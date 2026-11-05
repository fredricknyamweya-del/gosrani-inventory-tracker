import { Navigate, Outlet, useLocation } from "react-router";
import { Button, ErrorState, LoadingState } from "../components/ui";
import { useAuth } from "../context/AuthContext";

export function ProtectedRoute() {
  const { user, loading, authError, refreshUser } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingState label="Checking your session" />;
  if (authError) {
    return (
      <ErrorState
        message={authError.message}
        onRetry={refreshUser}
        retrying={loading}
        title="Unable to verify your session"
      />
    );
  }
  if (!user) {
    return (
      <Navigate
        replace
        state={{ from: location }}
        to="/login"
      />
    );
  }

  return <Outlet />;
}

export function AdminRoute() {
  const { user, loading } = useAuth();

  if (loading) return <LoadingState label="Checking your permissions" />;
  if (!user) return <Navigate replace to="/login" />;
  if (user.role !== "Admin") return <Navigate replace to="/inventory" />;

  return <Outlet />;
}

export function SignedInPlaceholder({ title = "Inventory workspace" }) {
  const { user, logout } = useAuth();

  return (
    <section className="auth-placeholder">
      <div className="auth-placeholder-card panel">
        <p className="eyebrow">Gosrani Wholesalers Limited</p>
        <h1>{title}</h1>
        <p>
          Signed in as <strong>{user?.name}</strong>. This screen is being
          prepared.
        </p>
        <Button onClick={logout} variant="secondary">
          Sign out
        </Button>
      </div>
    </section>
  );
}