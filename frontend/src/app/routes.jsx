import { Navigate, Outlet, useLocation } from "react-router"
import { ErrorState } from "../components/ui"
import { useAuth } from "../context/AuthContext"

function AuthCheckScreen() {
  return (
    <div
      aria-label="Checking authentication"
      className="auth-check-screen"
      role="status"
    />
  )
}

export function ProtectedRoute() {
  const { user, loading, authError, refreshUser } = useAuth()
  const location = useLocation()

  if (loading) return <AuthCheckScreen />
  if (authError) {
    return (
      <ErrorState
        message={authError.message}
        onRetry={refreshUser}
        retrying={loading}
        title="Unable to verify your session"
      />
    )
  }
  if (!user) {
    return <Navigate replace state={{ from: location }} to="/login" />
  }

  return <Outlet />
}

export function AdminRoute() {
  const { user, loading } = useAuth()

  if (loading) return <AuthCheckScreen />
  if (!user) return <Navigate replace to="/login" />
  if (user.role !== "Admin") return <Navigate replace to="/inventory" />

  return <Outlet />
}
