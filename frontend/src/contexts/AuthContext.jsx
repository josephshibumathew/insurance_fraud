import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import api, { authApi } from "../services/api";

const AuthContext = createContext(null);

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_KEY = "auth_user";

function decodeTokenExp(token) {
  if (!token) return null;
  try {
    const payloadBase64 = token.split(".")[1];
    const payload = JSON.parse(window.atob(payloadBase64.replace(/-/g, "+").replace(/_/g, "/")));
    return payload?.exp ? Number(payload.exp) : null;
  } catch (_e) {
    return null;
  }
}

export function AuthProvider({ children }) {
  const isLoggingOutRef = useRef(false);
  const hasRedirectedAfterLogoutRef = useRef(false);
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  });
  const [accessToken, setAccessToken] = useState(localStorage.getItem(ACCESS_TOKEN_KEY));
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem(REFRESH_TOKEN_KEY));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (accessToken) {
      api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    } else {
      delete api.defaults.headers.common.Authorization;
      localStorage.removeItem(ACCESS_TOKEN_KEY);
    }
  }, [accessToken]);

  useEffect(() => {
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    } else {
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  }, [refreshToken]);

  useEffect(() => {
    const exp = decodeTokenExp(accessToken);
    if (!exp || !refreshToken) return undefined;
    const msUntilRefresh = Math.max(5_000, exp * 1000 - Date.now() - 60_000);
    const timer = window.setTimeout(() => {
      refresh().catch(() => {
      });
    }, msUntilRefresh);
    return () => window.clearTimeout(timer);
  }, [accessToken, refreshToken]);

  useEffect(() => {
    if (accessToken && user) {
      hasRedirectedAfterLogoutRef.current = false;
    }
  }, [accessToken, user]);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const { data } = await authApi.login({ email, password });
      setAccessToken(data.access_token);
      setRefreshToken(data.refresh_token);
      setUser(data.user);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
    } finally {
      setLoading(false);
    }
  };

  const register = async (payload) => {
    setLoading(true);
    try {
      await authApi.register(payload);
      await login(payload.email, payload.password);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    if (isLoggingOutRef.current) return;
    isLoggingOutRef.current = true;

    try {
      if (refreshToken) {
        await authApi.logout(refreshToken);
      }
    } catch (_err) {
    } finally {
      setAccessToken(null);
      setRefreshToken(null);
      setUser(null);
      delete api.defaults.headers.common.Authorization;
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);

      if (!hasRedirectedAfterLogoutRef.current && location.pathname !== "/login") {
        hasRedirectedAfterLogoutRef.current = true;
        navigate("/login", { replace: true });
      }

      isLoggingOutRef.current = false;
    }
  };

  const refresh = async () => {
    if (isLoggingOutRef.current) {
      return null;
    }
    if (!refreshToken) {
      await logout();
      return null;
    }
    const { data } = await authApi.refresh({ refresh_token: refreshToken });
    setAccessToken(data.access_token);
    setRefreshToken(data.refresh_token);
      if (data.user) {
        setUser(data.user);
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      }
    return data.access_token;
  };

  const hasRole = (roleName) => user?.role === roleName;

  const hasPermission = (resource, action) => {
    if (user?.role === "admin") return true;
    const permissions = user?.permissions || {};
    const resourcePerms = permissions[resource] || [];
    return resourcePerms.includes(action);
  };

  const value = useMemo(
    () => ({
      user,
      loading,
      accessToken,
      refreshToken,
      isAuthenticated: Boolean(accessToken),
      login,
      register,
      logout,
      refresh,
      hasRole,
      hasPermission,
    }),
    [user, loading, accessToken, refreshToken]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
