import { useEffect, useState } from "react";
import { errorMessage, getStreaks, type StreakStats } from "../api/client";

function levelFor(count: number): number {
  return Math.min(count, 3);
}

// Monday = 0 ... Sunday = 6. Dates are plain calendar dates, so read them as UTC.
function weekdayIndex(isoDate: string): number {
  return (new Date(`${isoDate}T00:00:00Z`).getUTCDay() + 6) % 7;
}

export default function StreakCard() {
  const [data, setData] = useState<StreakStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getStreaks()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="error" role="alert">{error}</p>;
  }
  if (!data) {
    return <p className="muted">Loading streak…</p>;
  }

  const message = data.solved_today
    ? "You've solved something today. Your streak is safe."
    : data.current_streak > 0
      ? "Solve a question today to keep your streak going."
      : "Solve a question today to start a streak.";

  const padding = data.days.length > 0 ? weekdayIndex(data.days[0].date) : 0;

  return (
    <section className="streak-card">
      <div className="streak-top">
        <div className="streak-main">
          <span className="flame" aria-hidden="true">🔥</span>
          <strong>{data.current_streak}</strong>
          <span>day streak</span>
        </div>
        <div className="streak-side">
          <div>
            <strong>{data.longest_streak}</strong>
            <span>Longest streak</span>
          </div>
          <div>
            <strong>{data.total_active_days}</strong>
            <span>Active days</span>
          </div>
        </div>
      </div>

      <p className="muted">{message}</p>

      <div
        className="heatmap"
        role="img"
        aria-label="Questions solved per day over the last 12 weeks"
      >
        {Array.from({ length: padding }, (_, i) => (
          <span key={`pad-${i}`} className="cell empty" />
        ))}
        {data.days.map((d) => (
          <span
            key={d.date}
            className={`cell level-${levelFor(d.count)}${d.date === data.today ? " today" : ""}`}
            title={`${d.date}: ${d.count} solve${d.count === 1 ? "" : "s"}`}
          />
        ))}
      </div>

      <div className="heatmap-legend" aria-hidden="true">
        Less
        <span className="cell level-0" />
        <span className="cell level-1" />
        <span className="cell level-2" />
        <span className="cell level-3" />
        More
      </div>
    </section>
  );
}