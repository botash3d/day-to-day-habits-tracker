import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { GuestRoute, ProtectedRoute } from "./auth/RouteGuards";
import Dashboard from "./pages/Dashboard";
import Dsa from "./pages/Dsa";
import DsaProblem from "./pages/DsaProblem";
import Home from "./pages/Home";
import Learn from "./pages/Learn";
import LearnSubject from "./pages/LearnSubject";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Tasks from "./pages/Tasks";
import Build from "./pages/Build";
import BuildProject from "./pages/BuildProject";

// Pulls in the markdown and highlighting libraries, so it loads on demand.
const LearnLesson = lazy(() => import("./pages/LearnLesson"));
const BuildPage = lazy(() => import("./pages/BuildPage"));

export default function App() {
  return (
    <Suspense fallback={<p className="center-text">Loading…</p>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route element={<GuestRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
        </Route>
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/dsa" element={<Dsa />} />
          <Route path="/dsa/:problemId" element={<DsaProblem />} />
          <Route path="/learn" element={<Learn />} />
          <Route path="/learn/:subjectSlug" element={<LearnSubject />} />
          <Route
            path="/learn/:subjectSlug/:lessonSlug"
            element={<LearnLesson />}
          />
                    <Route path="/build" element={<Build />} />
          <Route path="/build/:projectSlug" element={<BuildProject />} />
          <Route
            path="/build/:projectSlug/:moduleSlug/:pageSlug"
            element={<BuildPage />}
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}