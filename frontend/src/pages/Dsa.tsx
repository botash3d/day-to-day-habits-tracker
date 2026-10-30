import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  errorMessage,
  getDsaStats,
  getProblems,
  type Difficulty,
  type DsaStats,
  type ProblemWithStats,
} from "../api/client";
import StreakCard from "../components/StreakCard";
import { formatDuration, formatTotal } from "../utils/time";

type Status = "All" | "Solved" | "Unsolved";

type PartGroup = {
  name: string;
  total: number;
  solved: number;
  sections: Map<string, ProblemWithStats[]>;
};

export default function Dsa() {
  const [problems, setProblems] = useState<ProblemWithStats[]>([]);
  const [stats, setStats] = useState<DsaStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [difficulty, setDifficulty] = useState<Difficulty | "All">("All");
  const [status, setStatus] = useState<Status>("All");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    Promise.all([getProblems(), getDsaStats()])
      .then(([problemData, statsData]) => {
        if (cancelled) return;
        setProblems(problemData);
        setStats(statsData);
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
  }, []);

  const search = query.trim().toLowerCase();
  const filtersActive = difficulty !== "All" || status !== "All" || search !== "";

  // Parts (headings) containing sections (subheadings), in list order.
  // Totals count every question; the section lists only hold the ones matching the filters.
  const groups = useMemo(() => {
    const parts = new Map<string, PartGroup>();
    for (const p of problems) {
      const partName = p.part ?? "Other";
      let group = parts.get(partName);
      if (!group) {
        group = { name: partName, total: 0, solved: 0, sections: new Map() };
        parts.set(partName, group);
      }
      group.total += 1;
      if (p.solve_count > 0) group.solved += 1;

      const matches =
        (difficulty === "All" || p.difficulty === difficulty) &&
        (status === "All" ||
          (status === "Solved" ? p.solve_count > 0 : p.solve_count === 0)) &&
        (search === "" || p.title.toLowerCase().includes(search));
      if (!matches) continue;

      const list = group.sections.get(p.topic) ?? [];
      list.push(p);
      group.sections.set(p.topic, list);
    }
    return Array.from(parts.values()).filter((g) => g.sections.size > 0);
  }, [problems, difficulty, status, search]);

  const shown = groups.reduce(
    (sum, g) =>
      sum + Array.from(g.sections.values()).reduce((n, list) => n + list.length, 0),
    0,
  );

  return (
    <main className="card wide">
      <Link to="/dashboard" className="back-link">
        ← Dashboard
      </Link>
      <h1>DSA practice</h1>

      <StreakCard />

      {stats && (
        <div className="stats">
          <div>
            <strong>
              {stats.solved_problems}/{stats.total_problems}
            </strong>
            <span>Questions solved</span>
          </div>
          <div>
            <strong>{formatTotal(stats.total_seconds)}</strong>
            <span>Time spent</span>
          </div>
          <div>
            <strong>{stats.total_attempts}</strong>
            <span>Total solves</span>
          </div>
        </div>
      )}

      <div className="filters">
        <input
          type="search"
          placeholder="Search questions"
          aria-label="Search questions"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          aria-label="Status"
          value={status}
          onChange={(e) => setStatus(e.target.value as Status)}
        >
          <option value="All">All questions</option>
          <option value="Solved">Solved</option>
          <option value="Unsolved">Unsolved</option>
        </select>
        <select
          aria-label="Difficulty"
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value as Difficulty | "All")}
        >
          <option value="All">All difficulties</option>
          <option value="Easy">Easy</option>
          <option value="Medium">Medium</option>
          <option value="Hard">Hard</option>
        </select>
      </div>

      {loading && <p className="muted">Loading questions…</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {!loading && !error && (
        <>
          <p className="muted">
            Showing {shown} of {problems.length}
          </p>

          {groups.length === 0 ? (
            <p className="muted">No questions match these filters.</p>
          ) : (
            groups.map((group, index) => (
              <details
                key={group.name}
                className="part"
                open={filtersActive || index === 0}
              >
                <summary>
                  <span className="part-name">{group.name}</span>
                  <span className="part-progress">
                    <span className="muted">
                      {group.solved}/{group.total} solved
                    </span>
                    <span className="bar part-bar">
                      <span style={{ width: `${(group.solved / group.total) * 100}%` }} />
                    </span>
                  </span>
                </summary>

                <div className="part-body">
                  {Array.from(group.sections.entries()).map(([section, items]) => (
                    <section key={section}>
                      <h3 className="section-title">{section}</h3>
                      <ul className="problem-list">
                        {items.map((p) => (
                          <li key={p.id}>
                            <div>
                              <div className="problem-title">
                                {p.number !== null && (
                                  <span className="q-number">{p.number}.</span>
                                )}
                                {p.solve_count > 0 && (
                                  <span className="solved-mark" title="Solved">✓</span>
                                )}
                                {p.title}
                              </div>
                              <div className="chips">
                                <span className={`chip ${p.difficulty}`}>{p.difficulty}</span>
                                {p.best_seconds !== null && (
                                  <span className="muted">
                                    Best {formatDuration(p.best_seconds)} · solved {p.solve_count}×
                                  </span>
                                )}
                              </div>
                            </div>
                            <Link className="link-button small" to={`/dsa/${p.id}`}>
                              {p.solve_count > 0 ? "Practice again" : "Solve"}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </section>
                  ))}
                </div>
              </details>
            ))
          )}
        </>
      )}
    </main>
  );
}