import React, { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

import ProtectedRoute from "./components/auth/ProtectedRoute";
import Layout from "./components/layout/Layout";
import LoadingSpinner from "./components/common/LoadingSpinner";
import LoginForm from "./components/auth/LoginForm";
import RegisterForm from "./components/auth/RegisterForm";
import { useAuth } from "./contexts/AuthContext";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Claims = lazy(() => import("./pages/Claims"));
const ClaimDetail = lazy(() => import("./pages/ClaimDetail"));
const NewClaim = lazy(() => import("./pages/NewClaim"));
const Reports = lazy(() => import("./pages/Reports"));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const AdminLogs = lazy(() => import("./pages/admin/SystemLogs"));
const AdminModels = lazy(() => import("./pages/AdminModels"));
const AdminSurveyors = lazy(() => import("./pages/AdminSurveyors"));
const AdminClaims = lazy(() => import("./pages/AdminClaims"));
const AdminReports = lazy(() => import("./pages/AdminReports"));

function AppRoutes() {
	const location = useLocation();
	const { user } = useAuth();
	const defaultHome = user?.role === "admin" ? "/admin/dashboard" : user?.role === "surveyor" ? "/dashboard" : "/login";

	return (
		<Suspense fallback={<LoadingSpinner text="Loading page..." fullPage />}>
			<AnimatePresence mode="wait">
				<motion.div
					key={location.pathname}
					initial={{ opacity: 0, y: 8 }}
					animate={{ opacity: 1, y: 0 }}
					exit={{ opacity: 0, y: -8 }}
					transition={{ duration: 0.2 }}
				>
					<Routes location={location}>
						<Route path="/login" element={<LoginForm />} />
						<Route path="/register" element={<RegisterForm />} />

						<Route
							path="/"
							element={
								<ProtectedRoute>
									<Layout />
								</ProtectedRoute>
							}
						>
							<Route index element={<Navigate to={defaultHome} replace />} />
							<Route path="dashboard" element={<ProtectedRoute roles={["surveyor"]}><Dashboard /></ProtectedRoute>} />
							<Route path="claims" element={<ProtectedRoute roles={["surveyor"]}><Claims /></ProtectedRoute>} />
							<Route path="claims/new" element={<ProtectedRoute roles={["surveyor"]}><NewClaim /></ProtectedRoute>} />
							<Route path="claims/:claimId" element={<ProtectedRoute roles={["surveyor"]}><ClaimDetail /></ProtectedRoute>} />
							<Route path="reports" element={<ProtectedRoute roles={["surveyor"]}><Reports /></ProtectedRoute>} />
							<Route path="admin/dashboard" element={<ProtectedRoute roles={["admin"]}><AdminDashboard /></ProtectedRoute>} />
							<Route path="admin/logs" element={<ProtectedRoute roles={["admin"]}><AdminLogs /></ProtectedRoute>} />
							<Route path="admin/ml-models" element={<ProtectedRoute roles={["admin"]}><AdminModels /></ProtectedRoute>} />
							<Route path="admin/surveyors" element={<ProtectedRoute roles={["admin"]}><AdminSurveyors /></ProtectedRoute>} />
							<Route path="admin/claims" element={<ProtectedRoute roles={["admin"]}><AdminClaims /></ProtectedRoute>} />
							<Route path="admin/reports" element={<ProtectedRoute roles={["admin"]}><AdminReports /></ProtectedRoute>} />
						</Route>

						<Route path="*" element={<Navigate to={defaultHome} replace />} />
					</Routes>
				</motion.div>
			</AnimatePresence>
		</Suspense>
	);
}

export default AppRoutes;

