import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  errorMessage,
  getBuildProject,
  type BuildProjectDetail,
} from "../api/client";
import { kindLabel } from "../utils/buildKinds";
import { percent } from "../utils/progress";
import "./Learn.css";
import "./Build.css";

export default function BuildProject() {
  const { projectSlug = "" } = useParams();
  // The key resets the page state when the project in the URL changes.
  return <ProjectView key={projectSlug} projectSlug={projectSlug} />;
}

function ProjectView({ projectSlug }: { projectSlug: string }) {
  const [project, setProject] = useState<BuildProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    getBuildProject(projectSlug)
      .then((data) => {
        if (cancelled) return;
        setProject(data);
        // Start with the chapter the student is working in (or the first one).
        const current = data.next_page?.module_slug ?? data.modules[0]?.slug;
        setOpen(new Set(current ? [current] : []));
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [projectSlug]);

  function toggle(moduleSlug: string) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(moduleSlug)) next.delete(moduleSlug);
      else next.add(moduleSlug);
      return next;
    });
  }

  const pct = project ? percent(project.completed_count, project.page_count) : 0;

  return (
    <main className="card wide">
      <Link to="/build" className="back-link">
        ← All projects
      </Link>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!error && project === null && <p className="muted">Loading project…</p>}

      {project && (
        <>
          <h1>{project.title}</h1>
          {project.description && (
            <p className="learn-lead">{project.description}</p>
          )}

          <div className="learn-progress-row">
            <div
              className="learn-bar"
              role="progressbar"
              aria-label="Project progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={pct}
            >
              <span style={{ width: `${pct}%` }} />
            </div>
            <span className="muted">
              {project.completed_count}/{project.page_count} pages
            </span>
          </div>

          <div className="learn-continue">
            {project.next_page ? (
              <Link
                className="link-button"
                to={`/build/${projectSlug}/${project.next_page.module_slug}/${project.next_page.page_slug}`}
              >
                {project.completed_count === 0 ? "Start project" : "Continue"}
                {`: ${project.next_page.title}`}
              </Link>
            ) : project.page_count > 0 ? (
              <p className="success">You have completed every page.</p>
            ) : (
              <p className="muted">Pages are coming soon.</p>
            )}
          </div>

          {project.modules.map((module, index) => {
            const isOpen = open.has(module.slug);
            const modulePct = percent(module.completed_count, module.page_count);
            return (
              <section key={module.slug} className="learn-module">
                <button
                  type="button"
                  className="build-module-toggle"
                  aria-expanded={isOpen}
                  onClick={() => toggle(module.slug)}
                >
                  <span className="build-module-arrow" aria-hidden="true">
                    {isOpen ? "▾" : "▸"}
                  </span>
                  <span className="build-module-title">
                    {index + 1}. {module.title}
                  </span>
                  <span className="muted">
                    {module.completed_count}/{module.page_count} done
                  </span>
                </button>
                <div
                  className="learn-bar build-module-bar"
                  role="progressbar"
                  aria-label={`${module.title} progress`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={modulePct}
                >
                  <span style={{ width: `${modulePct}%` }} />
                </div>

                {isOpen && (
                  <>
                    {module.summary && (
                      <p className="muted build-module-summary">
                        {module.summary}
                      </p>
                    )}
                    <ul className="learn-lessons">
                      {module.pages.map((page) => (
                        <li key={page.slug}>
                          <Link
                            to={`/build/${projectSlug}/${module.slug}/${page.slug}`}
                          >
                            <span
                              className={`learn-lesson-mark${page.completed ? " is-done" : ""}`}
                              title={page.completed ? "Completed" : "Not completed"}
                            >
                              {page.completed ? "✓" : "○"}
                            </span>
                            {page.title}
                            <span className="build-kind">
                              {kindLabel(page.kind)}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </section>
            );
          })}
        </>
      )}
    </main>
  );
}