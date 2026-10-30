import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  errorMessage,
  getProblems,
  type ProblemWithStats,
} from "../api/client";
import { useAuth } from "../auth/authContext";
import { formatDuration } from "../utils/time";

const PREVIEW_COUNT = 8;

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [problems, setProblems] = useState<ProblemWithStats[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getProblems()
      .then((data) => {
        if (!cancelled) setProblems(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!user) return null;

  // Most recently solved first.
  const solved = (problems ?? [])
    .filter((p) => p.solve_count > 0)
    .sort((a, b) => (b.last_solved_at ?? "").localeCompare(a.last_solved_at ?? ""));
  const visible = showAll ? solved : solved.slice(0, PREVIEW_COUNT);

  return (
    <main className="card wide">
      <h1>Welcome, {user.full_name}</h1>
      <dl>
        <dt>Email</dt>
        <dd>{user.email}</dd>
        <dt>Member since</dt>
        <dd>{new Date(user.created_at).toLocaleDateString()}</dd>
      </dl>
            <div className="actions">
        <Link className="link-button" to="/">
          Home
        </Link>
        <Link className="link-button" to="/tasks">
          Tasks
        </Link>
        <button type="button" className="secondary" onClick={logout}>
          Log out
        </button>
      </div>

      <section className="dash-section">
        <h2>Completed DSA questions</h2>

        {error && <p className="error" role="alert">{error}</p>}
        {!error && problems === null && <p className="muted">Loading…</p>}

        {problems !== null && (
          <>
            <p className="muted">
              {solved.length} of {problems.length} solved
            </p>

            {solved.length === 0 ? (
              <p className="muted">
                You haven't solved any questions yet.{" "}
                <Link to="/dsa">Pick one from the DSA page.</Link>
              </p>
            ) : (
              <ul className="problem-list">
                {visible.map((p) => (
                  <li key={p.id}>
                    <div>
                      <div className="problem-title">
                        <span className="solved-mark" title="Solved">✓</span>
                        {p.title}
                      </div>
                      <div className="chips">
                        <span className={`chip ${p.difficulty}`}>{p.difficulty}</span>
                        <span className="chip">{p.topic}</span>
                        {p.best_seconds !== null && (
                          <span className="muted">
                            Best {formatDuration(p.best_seconds)} · solved {p.solve_count}×
                          </span>
                        )}
                      </div>
                    </div>
                    <Link className="link-button small" to={`/dsa/${p.id}`}>
                      Practice again
                    </Link>
                  </li>
                ))}
              </ul>
            )}

            {solved.length > PREVIEW_COUNT && (
              <div className="button-row" style={{ marginTop: "1rem" }}>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setShowAll((s) => !s)}
                >
                  {showAll ? "Show fewer" : `Show all ${solved.length}`}
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}