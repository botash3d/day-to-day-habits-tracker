import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  clearBuildPageDone,
  errorMessage,
  getBuildPage,
  markBuildPageDone,
  type BuildPageDetail,
  type CheckpointFile,
} from "../api/client";
import LessonMarkdown from "../components/LessonMarkdown";
import { kindLabel } from "../utils/buildKinds";
import "./Learn.css";
import "./Build.css";

export default function BuildPage() {
  const { projectSlug = "", moduleSlug = "", pageSlug = "" } = useParams();
  // The key resets the page state (revealed hints, open checkpoint) for every new page.
  return (
    <PageView
      key={`${projectSlug}/${moduleSlug}/${pageSlug}`}
      projectSlug={projectSlug}
      moduleSlug={moduleSlug}
      pageSlug={pageSlug}
    />
  );
}

type Props = { projectSlug: string; moduleSlug: string; pageSlug: string };

const LANGUAGES: Record<string, string> = {
  py: "python",
  md: "markdown",
  yml: "yaml",
  yaml: "yaml",
  json: "json",
  toml: "toml",
  sh: "bash",
  ps1: "powershell",
  sql: "sql",
  ini: "ini",
  txt: "text",
};

// Wraps file content in a markdown code fence that is longer than any backtick run inside it.
function toFence(file: CheckpointFile): string {
  const ext = file.path.split(".").pop()?.toLowerCase() ?? "";
  const lang = LANGUAGES[ext] ?? "";
  const code = file.content.replace(/\n+$/, "");
  let ticks = "```";
  while (code.includes(ticks)) ticks += "`";
  return `${ticks}${lang}\n${code}\n${ticks}`;
}

function PageView({ projectSlug, moduleSlug, pageSlug }: Props) {
  const [page, setPage] = useState<BuildPageDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  // Browser-only state, like the Try it ticks on Learn.
  const [hintsShown, setHintsShown] = useState(0);
  const [checkpointOpen, setCheckpointOpen] = useState(false);
  const [fileIndex, setFileIndex] = useState(0);

  useEffect(() => {
    window.scrollTo(0, 0);
    let cancelled = false;
    getBuildPage(projectSlug, moduleSlug, pageSlug)
      .then((data) => {
        if (!cancelled) setPage(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [projectSlug, moduleSlug, pageSlug]);

  async function toggleDone() {
    if (!page || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      if (page.completed) {
        await clearBuildPageDone(projectSlug, moduleSlug, pageSlug);
        setPage({ ...page, completed: false, completed_at: null });
      } else {
        const progress = await markBuildPageDone(projectSlug, moduleSlug, pageSlug);
        setPage({
          ...page,
          completed: progress.completed,
          completed_at: progress.completed_at,
        });
      }
    } catch (err) {
      setSaveError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const doneLabel = page?.kind === "check" ? "I passed the check" : "Mark complete";
  const checkpoint = page?.checkpoint ?? [];
  const currentFile = checkpoint[Math.min(fileIndex, checkpoint.length - 1)];

  return (
    <main className="card wide">
      <Link to={`/build/${projectSlug}`} className="back-link">
        ← {page ? page.project_title : "Back to project"}
      </Link>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!error && page === null && <p className="muted">Loading page…</p>}

      {page && (
        <>
          <header className="learn-head">
            <h1>{page.title}</h1>
            <div className="chips">
              <span className="chip">{page.module_title}</span>
              <span className="chip">
                Page {page.page_number} of {page.module_page_count}
              </span>
              <span className="chip">{kindLabel(page.kind)}</span>
              {page.completed && page.completed_at && (
                <span className="chip learn-done-chip">
                  ✓ Completed {new Date(page.completed_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </header>

          <LessonMarkdown>{page.body}</LessonMarkdown>

          {page.hints.length > 0 && (
            <section className="build-hints" aria-label="Hints">
              {page.hints.slice(0, hintsShown).map((hint, i) => (
                <div className="build-hint" key={i}>
                  <strong>Hint {i + 1}</strong>
                  <LessonMarkdown>{hint}</LessonMarkdown>
                </div>
              ))}
              {hintsShown < page.hints.length && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setHintsShown((n) => n + 1)}
                >
                  Show hint {hintsShown + 1} of {page.hints.length}
                </button>
              )}
            </section>
          )}

          {page.kind === "stuck" && checkpoint.length > 0 && (
            <section className="build-checkpoint" aria-label="Checkpoint code">
              <p className="muted">
                Try the page again before opening this. It is the finished code
                for this module.
              </p>
              <button
                type="button"
                className="secondary"
                aria-expanded={checkpointOpen}
                onClick={() => setCheckpointOpen((v) => !v)}
              >
                {checkpointOpen ? "Hide checkpoint code" : "Show checkpoint code"}
              </button>

              {checkpointOpen && currentFile && (
                <>
                  <div
                    className="build-files"
                    role="tablist"
                    aria-label="Checkpoint files"
                  >
                    {checkpoint.map((file, i) => (
                      <button
                        key={file.path}
                        type="button"
                        role="tab"
                        aria-selected={file === currentFile}
                        className={`build-file${file === currentFile ? " is-active" : ""}`}
                        onClick={() => setFileIndex(i)}
                      >
                        {file.path}
                      </button>
                    ))}
                  </div>
                  <LessonMarkdown>{toFence(currentFile)}</LessonMarkdown>
                </>
              )}
            </section>
          )}

          {saveError && (
            <p className="error" role="alert">
              {saveError}
            </p>
          )}

          <nav className="learn-lesson-nav" aria-label="Page navigation">
            {page.previous ? (
              <Link
                className="link-button secondary"
                to={`/build/${projectSlug}/${page.previous.module_slug}/${page.previous.page_slug}`}
                title={page.previous.title}
              >
                ← Previous
              </Link>
            ) : (
              <span />
            )}

            <button
              type="button"
              className={page.completed ? "secondary" : undefined}
              onClick={toggleDone}
              disabled={saving}
            >
              {page.completed ? "Mark as not complete" : doneLabel}
            </button>

            {page.next ? (
              <Link
                className="link-button"
                to={`/build/${projectSlug}/${page.next.module_slug}/${page.next.page_slug}`}
                title={page.next.title}
              >
                {page.next.module_slug !== page.module_slug
                  ? "Next module →"
                  : "Next →"}
              </Link>
            ) : (
              <Link className="link-button secondary" to={`/build/${projectSlug}`}>
                Back to project
              </Link>
            )}
          </nav>
        </>
      )}
    </main>
  );
}