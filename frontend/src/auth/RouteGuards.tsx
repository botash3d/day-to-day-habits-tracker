import { Navigate, Outlet, useLocation, type Location } from "react-router-dom";
import { useAuth } from "./authContext";

function Loading() {
  return <p className="center-text">Loading…</p>;
}

// Pages that need a logged-in user.
export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}

// Login/signup pages: logged-in users get sent onward instead.
export function GuestRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading />;
  if (user) {
    const from = (location.state as { from?: Location } | null)?.from;
    return <Navigate to={from?.pathname ?? "/"} replace />;
  }
  return <Outlet />;
}