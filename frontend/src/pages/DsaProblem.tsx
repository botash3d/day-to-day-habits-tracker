import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  discardAttempt,
  errorMessage,
  finishAttempt,
  getProblem,
  startAttempt,
  type Attempt,
  type ProblemDetail,
} from "../api/client";
import { formatDuration } from "../utils/time";

// An attempt plus the moment we received it, so the timer can keep counting
// from the server's elapsed time without depending on the browser clock being right.
type Tracked = { attempt: Attempt; syncedAt: number };

export default function DsaProblem() {
  const { problemId } = useParams();
  const id = Number(problemId);
  const invalid = !Number.isInteger(id);

  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [tracked, setTracked] = useState<Tracked | null>(null);
  const [loading, setLoading] = useState(!invalid);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [solutionUrl, setSolutionUrl] = useState("");
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (invalid) return;
    let cancelled = false;
    getProblem(id)
      .then((data) => {
        if (cancelled) return;
        setProblem(data);
        if (data.active_attempt) {
          setTracked({ attempt: data.active_attempt, syncedAt: Date.now() });
        }
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id, invalid]);

  const active = tracked !== null && tracked.attempt.finished_at === null;
  const finished = tracked !== null && tracked.attempt.finished_at !== null;

  useEffect(() => {
    if (!active) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);

  let elapsed = 0;
  if (tracked) {
    elapsed = tracked.attempt.duration_seconds;
    if (active) {
      elapsed += Math.max(0, Math.floor((now - tracked.syncedAt) / 1000));
    }
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleStart() {
    await run(async () => {
      const attempt = await startAttempt(id);
      setTracked({ attempt, syncedAt: Date.now() });
      setSolutionUrl("");
    });
  }

  async function handleFinish(e: FormEvent) {
    e.preventDefault();
    if (!tracked) return;
    await run(async () => {
      const attempt = await finishAttempt(
        tracked.attempt.id,
        solutionUrl.trim() || null,
      );
      setTracked({ attempt, syncedAt: Date.now() });
      setProblem((p) => (p ? { ...p, history: [attempt, ...p.history] } : p));
    });
  }

  async function handleDiscard() {
    if (!tracked) return;
    if (!window.confirm("Discard this attempt? Your time will not be saved.")) {
      return;
    }
    await run(async () => {
      await discardAttempt(tracked.attempt.id);
      setTracked(null);
    });
  }

  if (invalid) {
    return (
      <main className="card wide">
        <Link to="/dsa" className="back-link">← All questions</Link>
        <p className="error" role="alert">Question not found.</p>
      </main>
    );
  }

  const bestSeconds =
    problem && problem.history.length > 0
      ? Math.min(...problem.history.map((a) => a.duration_seconds))
      : null;

  return (
    <main className="card wide">
      <Link to="/dsa" className="back-link">← All questions</Link>

      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {problem && (
        <>
          <h1>{problem.title}</h1>
          <div className="chips">
            <span className={`chip ${problem.difficulty}`}>{problem.difficulty}</span>
            <span className="chip">{problem.topic}</span>
          </div>
          <p>
            <a href={problem.url} target="_blank" rel="noopener noreferrer">
              Open the question ↗
            </a>
          </p>

          {!tracked && (
            <div className="button-row">
              <button type="button" onClick={handleStart} disabled={busy}>
                {busy ? "Starting…" : "Start timer"}
              </button>
            </div>
          )}

          {active && (
            <form onSubmit={handleFinish}>
              <div className="timer" aria-live="off">{formatDuration(elapsed)}</div>
              <label>
                Link to your solution (optional)
                <input
                  type="url"
                  placeholder="https://github.com/you/repo/blob/main/solution.py"
                  maxLength={500}
                  value={solutionUrl}
                  onChange={(e) => setSolutionUrl(e.target.value)}
                />
              </label>
              <div className="button-row">
                <button type="submit" disabled={busy}>
                  {busy ? "Saving…" : "Finish: I solved it"}
                </button>
                <button
                  type="button"
                  className="secondary"
                  onClick={handleDiscard}
                  disabled={busy}
                >
                  Discard
                </button>
              </div>
            </form>
          )}

          {finished && tracked && (
            <>
              <p className="success">
                Solved in <strong>{formatDuration(tracked.attempt.duration_seconds)}</strong>
              </p>
              <div className="button-row">
                <button type="button" onClick={handleStart} disabled={busy}>
                  Start another attempt
                </button>
                <Link className="link-button secondary" to="/dsa">
                  Back to questions
                </Link>
              </div>
            </>
          )}

          {problem.history.length > 0 && (
            <section className="history">
              <h2>Your solves</h2>
              <ul>
                {problem.history.map((a) => (
                  <li key={a.id}>
                    <span>
                      {a.finished_at ? new Date(a.finished_at).toLocaleString() : ""}
                    </span>
                    <span>
                      <strong>{formatDuration(a.duration_seconds)}</strong>
                      {a.duration_seconds === bestSeconds && (
                        <span className="chip Easy">Best</span>
                      )}
                    </span>
                    {a.solution_url ? (
                      <a href={a.solution_url} target="_blank" rel="noopener noreferrer">
                        Solution ↗
                      </a>
                    ) : (
                      <span className="muted">No link</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}