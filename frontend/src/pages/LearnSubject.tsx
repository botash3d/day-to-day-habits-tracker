import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { errorMessage, getSubject, type SubjectDetail } from "../api/client";
import { percent } from "../utils/progress";
import "./Learn.css";

export default function LearnSubject() {
  const { subjectSlug = "" } = useParams();
  // The key resets the page state when the subject in the URL changes.
  return <SubjectView key={subjectSlug} subjectSlug={subjectSlug} />;
}

function SubjectView({ subjectSlug }: { subjectSlug: string }) {
  const [subject, setSubject] = useState<SubjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getSubject(subjectSlug)
      .then((data) => {
        if (!cancelled) setSubject(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [subjectSlug]);

  const pct = subject ? percent(subject.completed_count, subject.lesson_count) : 0;
  const nextLesson = subject?.modules
    .flatMap((m) => m.lessons)
    .find((l) => l.slug === subject.next_lesson_slug);

  return (
    <main className="card wide">
      <Link to="/learn" className="back-link">
        ← All courses
      </Link>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!error && subject === null && <p className="muted">Loading course…</p>}

      {subject && (
        <>
          <h1>{subject.title}</h1>
          {subject.description && <p className="learn-lead">{subject.description}</p>}

          <div className="learn-progress-row">
            <div
              className="learn-bar"
              role="progressbar"
              aria-label="Course progress"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={pct}
            >
              <span style={{ width: `${pct}%` }} />
            </div>
            <span className="muted">
              {subject.completed_count}/{subject.lesson_count} lessons
            </span>
          </div>

          <div className="learn-continue">
            {subject.next_lesson_slug ? (
              <Link
                className="link-button"
                to={`/learn/${subjectSlug}/${subject.next_lesson_slug}`}
              >
                {subject.completed_count === 0 ? "Start course" : "Continue"}
                {nextLesson ? `: ${nextLesson.title}` : ""}
              </Link>
            ) : subject.lesson_count > 0 ? (
              <p className="success">You have completed every lesson.</p>
            ) : (
              <p className="muted">Lessons are coming soon.</p>
            )}
          </div>

          {subject.modules.map((module) => {
            const done = module.lessons.filter((l) => l.completed).length;
            return (
              <section key={module.slug} className="learn-module">
                <div className="learn-module-head">
                  <h2>{module.title}</h2>
                  <span className="muted">
                    {done}/{module.lessons.length} done
                  </span>
                </div>
                <ul className="learn-lessons">
                  {module.lessons.map((lesson) => (
                    <li key={lesson.slug}>
                      <Link to={`/learn/${subjectSlug}/${lesson.slug}`}>
                        <span
                          className={`learn-lesson-mark${lesson.completed ? " is-done" : ""}`}
                          title={lesson.completed ? "Completed" : "Not completed"}
                        >
                          {lesson.completed ? "✓" : "○"}
                        </span>
                        {lesson.title}
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </>
      )}
    </main>
  );
}