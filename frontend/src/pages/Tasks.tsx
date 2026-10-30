import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  completeTask,
  createTask,
  deleteTask,
  errorMessage,
  getTasks,
  reopenTask,
  updateTask,
  type Task,
  type TaskInput,
} from "../api/client";
import TaskForm from "../components/TaskForm";
import { formatDueLabel, todayLocal } from "../utils/date";

type View = "open" | "completed";

type RowProps = {
  task: Task;
  today: string;
  categories: string[];
  editing: boolean;
  onToggle: (task: Task) => void;
  onEdit: (id: string | null) => void;
  onSave: (id: string, input: TaskInput) => Promise<void>;
  onDelete: (task: Task) => void;
};

function TaskRow({
  task,
  today,
  categories,
  editing,
  onToggle,
  onEdit,
  onSave,
  onDelete,
}: RowProps) {
  if (editing) {
    return (
      <li className="task editing">
        <TaskForm
          initial={{
            title: task.title,
            due_date: task.due_date,
            priority: task.priority,
            category: task.category,
            repeat: task.repeat,
          }}
          submitLabel="Save"
          categories={categories}
          onSubmit={(input) => onSave(task.id, input)}
          onCancel={() => onEdit(null)}
        />
      </li>
    );
  }

  const done = task.completed_at !== null;
  const overdue = !done && task.due_date !== null && task.due_date < today;

  return (
    <li className={`task${done ? " done" : ""}`}>
      <input
        type="checkbox"
        checked={done}
        aria-label={done ? `Reopen ${task.title}` : `Complete ${task.title}`}
        onChange={() => onToggle(task)}
      />
      <div className="task-body">
        <div className="task-title">{task.title}</div>
        <div className="chips">
          <span className={`chip prio-${task.priority}`}>{task.priority}</span>
          {task.category && <span className="chip">{task.category}</span>}
          {task.repeat !== "none" && <span className="chip">🔁 {task.repeat}</span>}
          {task.due_date && !done && (
            <span className={`due${overdue ? " overdue" : ""}`}>
              {formatDueLabel(task.due_date, today)}
            </span>
          )}
          {done && task.completed_at && (
            <span className="due">
              Done {new Date(task.completed_at).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
      <div className="task-actions">
        {!done && (
          <button type="button" className="icon-btn" onClick={() => onEdit(task.id)}>
            Edit
          </button>
        )}
        <button type="button" className="icon-btn" onClick={() => onDelete(task)}>
          Delete
        </button>
      </div>
    </li>
  );
}

export default function Tasks() {
  const [view, setView] = useState<View>("open");
  const [data, setData] = useState<{ view: View; tasks: Task[] } | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getTasks(view)
      .then((tasks) => {
        if (cancelled) return;
        setData({ view, tasks });
        setError(null);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [view, reloadKey]);

  const reload = () => setReloadKey((k) => k + 1);
  const tasks = data?.view === view ? data.tasks : null;
  const today = todayLocal();

  const categories = Array.from(
    new Set((tasks ?? []).map((t) => t.category).filter((c): c is string => !!c)),
  ).sort();

  async function run(action: () => Promise<unknown>) {
    setError(null);
    try {
      await action();
      reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleCreate(input: TaskInput) {
    await createTask(input); // errors are shown by the form
    reload();
  }

  async function handleSave(id: string, input: TaskInput) {
    await updateTask(id, input);
    setEditingId(null);
    reload();
  }

  function handleToggle(task: Task) {
    void run(() => (task.completed_at ? reopenTask(task.id) : completeTask(task.id)));
  }

  function handleDelete(task: Task) {
    if (!window.confirm(`Delete "${task.title}"?`)) return;
    void run(() => deleteTask(task.id));
  }

  function renderRows(list: Task[]) {
    return list.map((task) => (
      <TaskRow
        key={task.id}
        task={task}
        today={today}
        categories={categories}
        editing={editingId === task.id}
        onToggle={handleToggle}
        onEdit={setEditingId}
        onSave={handleSave}
        onDelete={handleDelete}
      />
    ));
  }

  function renderGroup(title: string, list: Task[], className = "") {
    if (list.length === 0) return null;
    return (
      <section className="task-section">
        <h2 className={className}>
          {title} ({list.length})
        </h2>
        <ul className="task-list">{renderRows(list)}</ul>
      </section>
    );
  }

  const overdue = (tasks ?? []).filter((t) => t.due_date !== null && t.due_date < today);
  const dueToday = (tasks ?? []).filter((t) => t.due_date === today);
  const upcoming = (tasks ?? []).filter((t) => t.due_date !== null && t.due_date > today);
  const noDate = (tasks ?? []).filter((t) => t.due_date === null);

  return (
    <main className="card wide">
      <Link to="/dashboard" className="back-link">
        ← Dashboard
      </Link>
      <h1>Tasks</h1>

      <TaskForm
        submitLabel="Add task"
        categories={categories}
        resetOnSuccess
        onSubmit={handleCreate}
      />

      <div className="button-row" style={{ margin: "1.25rem 0 0" }}>
        <button
          type="button"
          className={view === "open" ? "" : "secondary"}
          onClick={() => setView("open")}
        >
          Open
        </button>
        <button
          type="button"
          className={view === "completed" ? "" : "secondary"}
          onClick={() => setView("completed")}
        >
          Completed
        </button>
      </div>

      {error && <p className="error" role="alert" style={{ marginTop: "1rem" }}>{error}</p>}
      {tasks === null && !error && <p className="muted">Loading…</p>}

      {tasks !== null && view === "open" && (
        <>
          {tasks.length === 0 && (
            <p className="muted">Nothing to do. Add your first task above.</p>
          )}
          {renderGroup("Overdue", overdue, "overdue")}
          {renderGroup("Today", dueToday)}
          {renderGroup("Upcoming", upcoming)}
          {renderGroup("No date", noDate)}
        </>
      )}

      {tasks !== null && view === "completed" && (
        <>
          {tasks.length === 0 ? (
            <p className="muted">No completed tasks yet.</p>
          ) : (
            <section className="task-section">
              <ul className="task-list">{renderRows(tasks)}</ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}