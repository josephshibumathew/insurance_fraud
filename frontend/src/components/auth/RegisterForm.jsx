import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { toast } from "react-toastify";
import { FiLock, FiMail, FiShield } from "react-icons/fi";
import { z } from "zod";

import { useAuth } from "../../contexts/AuthContext";

const schema = z
  .object({
    email: z.string().email("Enter a valid email"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string().min(8, "Confirm your password"),
  })
  .refine((value) => value.password === value.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

function RegisterForm() {
  const { register: registerUser, loading } = useAuth();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({ resolver: zodResolver(schema) });

  const onSubmit = async (values) => {
    try {
      await registerUser({ email: values.email, password: values.password });
      toast.success("Account created successfully");
      navigate("/dashboard", { replace: true });
    } catch (error) {
      toast.error(error.response?.data?.detail || "Registration failed");
    }
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4 py-8"
      style={{ backgroundColor: "var(--bg)" }}
    >
      <div className="mx-auto grid w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-200/70 bg-white shadow-card-hover lg:grid-cols-2">
        {/* Left hero */}
        <div
          className="relative hidden flex-col justify-between overflow-hidden p-10 text-white lg:flex"
          style={{
            background: "linear-gradient(145deg, #393E46 0%, #222831 55%, #948979 100%)",
          }}
        >
          <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/5" />
          <div className="absolute -bottom-12 -left-12 h-48 w-48 rounded-full bg-white/5" />

          <div className="relative z-10 flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15">
              <FiShield size={20} />
            </span>
            <span className="text-lg font-bold tracking-tight">AutoFraud Intelligence</span>
          </div>

          <div className="relative z-10">
            <h1 className="text-3xl font-bold leading-snug tracking-tight">
              Create Your<br />Surveyor Workspace
            </h1>
            <p className="mt-4 text-base leading-relaxed text-white/75">
              Join the AI-assisted insurance workflow to submit claims, review risk scoring,
              and generate comprehensive reports.
            </p>
            <div className="mt-8 rounded-2xl border border-white/20 bg-white/10 p-4 text-sm text-white/80 backdrop-blur-sm">
              Accounts are activated with surveyor privileges by default.
            </div>
          </div>

          <div className="relative z-10 text-xs text-white/40">
            &copy; {new Date().getFullYear()} AutoFraud Intelligence
          </div>
        </div>

        {/* Right form */}
        <motion.div
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.28 }}
          className="flex flex-col justify-center p-8 sm:p-12"
        >
          <h2 className="text-2xl font-bold tracking-tight text-slate-900">Create account</h2>
          <p className="mt-1 text-sm text-slate-500">Set up your surveyor credentials.</p>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-4">
            <div>
              <label htmlFor="register-email" className="form-label-tw">Email address</label>
              <div className="relative">
                <FiMail className="pointer-events-none absolute left-3.5 top-3 text-slate-400" size={15} />
                <input
                  id="register-email"
                  type="email"
                  className="app-input pl-10"
                  placeholder="you@example.com"
                  {...register("email")}
                />
              </div>
              {errors.email ? <p className="form-error-tw">{errors.email.message}</p> : null}
            </div>

            <div>
              <label htmlFor="register-password" className="form-label-tw">Password</label>
              <div className="relative">
                <FiLock className="pointer-events-none absolute left-3.5 top-3 text-slate-400" size={15} />
                <input
                  id="register-password"
                  type="password"
                  className="app-input pl-10"
                  placeholder="&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;"
                  {...register("password")}
                />
              </div>
              {errors.password ? <p className="form-error-tw">{errors.password.message}</p> : null}
            </div>

            <div>
              <label htmlFor="register-confirm-password" className="form-label-tw">Confirm password</label>
              <div className="relative">
                <FiLock className="pointer-events-none absolute left-3.5 top-3 text-slate-400" size={15} />
                <input
                  id="register-confirm-password"
                  type="password"
                  className="app-input pl-10"
                  placeholder="&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;&#9679;"
                  {...register("confirmPassword")}
                />
              </div>
              {errors.confirmPassword ? (
                <p className="form-error-tw">{errors.confirmPassword.message}</p>
              ) : null}
            </div>

            <button type="submit" className="app-button mt-2 w-full py-2.5" disabled={loading}>
              {loading ? "Creating account..." : "Create account"}
            </button>
          </form>

          <p className="mt-6 text-sm text-slate-500">
            Already have an account?{" "}
            <Link className="font-semibold text-navy-600 hover:text-navy-900 hover:underline" to="/login">
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}

export default RegisterForm;
