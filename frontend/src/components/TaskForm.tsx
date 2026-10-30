import { useId, useState, type FormEvent } from "react";
import {
  errorMessage,
  type Priority,
  type Repeat,
  type TaskInput,
} from "../api/client";

type Props = {
  initial?: TaskInput;
  submitLabel: string;
  categories: string[];
  resetOnSuccess?: boolean;
  onSubmit: (input: TaskInput) => Promise<void>;
  onCancel?: () => void;
};

const EMPTY: TaskInput = {
  title: "",
  due_date: null,
  priority: "medium",
  category: null,
  repeat: "none",
};

export default function TaskForm({
  initial = EMPTY,
  submitLabel,
  categories,
  resetOnSuccess = false,
  onSubmit,
  onCancel,
}: Props) {
  const listId = useId();
  const [title, setTitle] = useState(initial.title);
  const [dueDate, setDueDate] = useState(initial.due_date ?? "");
  const [priority, setPriority] = useState<Priority>(initial.priority);
  const [category, setCategory] = useState(initial.category ?? "");
  const [repeat, setRepeat] = useState<Repeat>(initial.repeat);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleDueChange(value: string) {
    setDueDate(value);
    if (!value) setRepeat("none"); // repeating needs a due date
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        title: title.trim(),
        due_date: dueDate || null,
        priority,
        category: category.trim() || null,
        repeat,
      });
      if (resetOnSuccess) {
        setTitle("");
        setDueDate("");
        setPriority("medium");
        setCategory("");
        setRepeat("none");
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="What needs doing?"
        aria-label="Task title"
        required
        maxLength={200}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />

      <div className="task-form-grid">
        <label>
          Due date
          <input
            type="date"
            value={dueDate}
            onChange={(e) => handleDueChange(e.target.value)}
          />
        </label>
        <label>
          Priority
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as Priority)}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label>
          Category
          <input
            type="text"
            list={listId}
            maxLength={50}
            placeholder="e.g. Home"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
          <datalist id={listId}>
            {categories.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </label>
        <label>
          Repeat
          <select
            value={repeat}
            disabled={!dueDate}
            title={dueDate ? undefined : "Choose a due date to enable repeating"}
            onChange={(e) => setRepeat(e.target.value as Repeat)}
          >
            <option value="none">Never</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="button-row">
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}