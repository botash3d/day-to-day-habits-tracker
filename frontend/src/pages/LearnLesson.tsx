import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  completeLesson,
  errorMessage,
  getLesson,
  uncompleteLesson,
  type LessonDetail,
} from "../api/client";
import ExerciseSteps from "../components/ExerciseSteps";
import LessonMarkdown from "../components/LessonMarkdown";
import "./Learn.css";

export default function LearnLesson() {
  const { subjectSlug = "", lessonSlug = "" } = useParams();
  // The key resets the page state (and the Try it ticks) for every new lesson.
  return (
    <LessonView
      key={`${subjectSlug}/${lessonSlug}`}
      subjectSlug={subjectSlug}
      lessonSlug={lessonSlug}
    />
  );
}

type Props = { subjectSlug: string; lessonSlug: string };

function LessonView({ subjectSlug, lessonSlug }: Props) {
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    window.scrollTo(0, 0);
    let cancelled = false;
    getLesson(subjectSlug, lessonSlug)
      .then((data) => {
        if (!cancelled) setLesson(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [subjectSlug, lessonSlug]);

  async function toggleComplete() {
    if (!lesson || saving) return;
    setSaving(true);
    setSaveError(null);
    try {
      if (lesson.completed) {
        await uncompleteLesson(subjectSlug, lessonSlug);
        setLesson({ ...lesson, completed: false, completed_at: null });
      } else {
        const progress = await completeLesson(subjectSlug, lessonSlug);
        setLesson({
          ...lesson,
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

  return (
    <main className="card wide">
      <Link to={`/learn/${subjectSlug}`} className="back-link">
        ← {lesson ? lesson.subject_title : "Back to course"}
      </Link>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!error && lesson === null && <p className="muted">Loading lesson…</p>}

      {lesson && (
        <>
          <header className="learn-head">
            <h1>{lesson.title}</h1>
            <div className="chips">
              <span className="chip">{lesson.module_title}</span>
              {lesson.completed && lesson.completed_at && (
                <span className="chip learn-done-chip">
                  ✓ Completed {new Date(lesson.completed_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </header>

          <LessonMarkdown>{lesson.body}</LessonMarkdown>

          {lesson.exercise && <ExerciseSteps steps={lesson.exercise.steps} />}

          {saveError && (
            <p className="error" role="alert">
              {saveError}
            </p>
          )}

          <nav className="learn-lesson-nav" aria-label="Lesson navigation">
            {lesson.previous_slug ? (
              <Link
                className="link-button secondary"
                to={`/learn/${subjectSlug}/${lesson.previous_slug}`}
              >
                ← Previous
              </Link>
            ) : (
              <span />
            )}

            <button
              type="button"
              className={lesson.completed ? "secondary" : undefined}
              onClick={toggleComplete}
              disabled={saving}
            >
              {lesson.completed ? "Mark as not complete" : "Mark complete"}
            </button>

            {lesson.next_slug ? (
              <Link
                className="link-button"
                to={`/learn/${subjectSlug}/${lesson.next_slug}`}
              >
                Next →
              </Link>
            ) : (
              <Link className="link-button secondary" to={`/learn/${subjectSlug}`}>
                Back to course
              </Link>
            )}
          </nav>
        </>
      )}
    </main>
  );
}