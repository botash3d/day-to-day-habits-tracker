import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { errorMessage, getSubjects, type SubjectSummary } from "../api/client";
import { percent } from "../utils/progress";
import "./Learn.css";

export default function Learn() {
  const [subjects, setSubjects] = useState<SubjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getSubjects()
      .then((data) => {
        if (!cancelled) setSubjects(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="card wide">
      <Link to="/" className="back-link">
        ← Home
      </Link>
      <h1>Learn</h1>
      <p className="muted">Pick a course and work through it lesson by lesson.</p>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!error && subjects === null && <p className="muted">Loading courses…</p>}
      {subjects !== null && subjects.length === 0 && (
        <p className="muted">No courses are published yet. Check back soon.</p>
      )}

      {subjects !== null && subjects.length > 0 && (
        <ul className="learn-subjects">
          {subjects.map((s) => {
            const pct = percent(s.completed_count, s.lesson_count);
            const label =
              s.completed_count === 0
                ? "Start"
                : s.completed_count >= s.lesson_count
                  ? "Review"
                  : "Continue";
            return (
              <li key={s.slug} className="learn-subject">
                <div className="learn-subject-main">
                  <h2>{s.title}</h2>
                  {s.description && <p>{s.description}</p>}
                  <div className="learn-progress-row">
                    <div
                      className="learn-bar"
                      role="progressbar"
                      aria-label={`${s.title} progress`}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={pct}
                    >
                      <span style={{ width: `${pct}%` }} />
                    </div>
                    <span className="muted">
                      {s.completed_count}/{s.lesson_count} lessons
                    </span>
                  </div>
                </div>
                <Link className="link-button small" to={`/learn/${s.slug}`}>
                  {label}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}