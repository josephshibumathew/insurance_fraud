import React, { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../contexts/AuthContext";
import LoadingSpinner from "../common/LoadingSpinner";

function ProtectedRoute({ children, roles }) {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const hasRedirectedRef = useRef(false);

  useEffect(() => {
    if (loading) {
      return;
    }

    if (isAuthenticated) {
      hasRedirectedRef.current = false;
      return;
    }

    if (!hasRedirectedRef.current && location.pathname !== "/login") {
      hasRedirectedRef.current = true;
      navigate("/login", { replace: true, state: { from: location } });
    }
  }, [isAuthenticated, loading, location, navigate]);

  useEffect(() => {
    if (!loading && isAuthenticated && roles?.length && user?.role && !roles.includes(user.role)) {
      const fallback = user.role === "admin" ? "/admin/dashboard" : "/dashboard";
      if (location.pathname !== fallback) {
        navigate(fallback, { replace: true });
      }
    }
  }, [isAuthenticated, loading, roles, user?.role, location.pathname, navigate]);

  if (loading) {
    return <LoadingSpinner text="Checking session..." fullPage />;
  }

  if (!isAuthenticated) {
    return null;
  }

  if (roles?.length && (!user?.role || !roles.includes(user.role))) {
    return null;
  }

  return children;
}

export default ProtectedRoute;
