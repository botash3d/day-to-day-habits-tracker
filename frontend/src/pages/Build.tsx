import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  errorMessage,
  getBuildProjects,
  type BuildProjectSummary,
} from "../api/client";
import { percent } from "../utils/progress";
import "./Learn.css";
import "./Build.css";

export default function Build() {
  const [projects, setProjects] = useState<BuildProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getBuildProjects()
      .then((data) => {
        if (!cancelled) setProjects(data);
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
      <h1>Build</h1>
      <p className="learn-lead">
        Build a real project step by step, one small page at a time.
      </p>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!error && projects === null && <p className="muted">Loading projects…</p>}
      {projects && projects.length === 0 && (
        <p className="muted">Projects are coming soon.</p>
      )}

      {projects && projects.length > 0 && (
        <ul className="build-projects">
          {projects.map((project) => {
            const pct = percent(project.completed_count, project.page_count);
            return (
              <li key={project.slug}>
                <Link to={`/build/${project.slug}`} className="build-project-card">
                  <h2>{project.title}</h2>
                  {project.description && <p>{project.description}</p>}
                  <div className="learn-progress-row">
                    <div
                      className="learn-bar"
                      role="progressbar"
                      aria-label={`${project.title} progress`}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={pct}
                    >
                      <span style={{ width: `${pct}%` }} />
                    </div>
                    <span className="muted">
                      {project.completed_count}/{project.page_count} pages ·{" "}
                      {project.module_count} modules
                    </span>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}