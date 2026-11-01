const API_URL: string =
  import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "access_token";

// ---------- Types ----------

export type User = {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
};

type Token = { access_token: string; token_type: string };

export type Difficulty = "Easy" | "Medium" | "Hard";

export type Problem = {
  id: number;
  number: number | null;
  slug: string;
  title: string;
  difficulty: Difficulty;
  topic: string;
  part: string | null;
  url: string;
};

export type ProblemWithStats = Problem & {
  solve_count: number;
  best_seconds: number | null;
  last_solved_at: string | null;
};

export type Attempt = {
  id: string;
  problem_id: number;
  started_at: string;
  finished_at: string | null;
  solution_url: string | null;
  duration_seconds: number;
};

export type ProblemDetail = Problem & {
  active_attempt: Attempt | null;
  history: Attempt[];
};

export type DsaStats = {
  solved_problems: number;
  total_problems: number;
  total_attempts: number;
  total_seconds: number;
};

export type DayActivity = { date: string; count: number };

export type StreakStats = {
  current_streak: number;
  longest_streak: number;
  total_active_days: number;
  solved_today: boolean;
  today: string;
  days: DayActivity[];
};

export type Priority = "low" | "medium" | "high";
export type Repeat = "none" | "daily" | "weekly" | "monthly";

export type Task = {
  id: string;
  title: string;
  due_date: string | null;
  priority: Priority;
  category: string | null;
  repeat: Repeat;
  completed_at: string | null;
  created_at: string;
};

export type TaskInput = {
  title: string;
  due_date: string | null;
  priority: Priority;
  category: string | null;
  repeat: Repeat;
};

// ---------- Token storage ----------

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// ---------- Errors ----------

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function errorMessage(err: unknown): string {
  return err instanceof ApiError
    ? err.message
    : "Something went wrong. Please try again.";
}

// FastAPI returns `detail` as a string (our own errors) or as a list (validation errors).
function extractMessage(body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: string; loc?: unknown[] };
    const field = first.loc?.[first.loc.length - 1];
    const msg = first.msg ?? "Invalid input.";
    return field ? `${String(field)}: ${msg}` : msg;
  }
  return "Something went wrong. Please try again.";
}

// ---------- Core request helper ----------

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection.");
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Non-JSON error body; fall back to the generic message.
    }
    throw new ApiError(response.status, extractMessage(body));
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// Days are counted in the browser's timezone, e.g. "Asia/Kolkata".
function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

// ---------- Auth ----------

export function signup(fullName: string, email: string, password: string) {
  return request<User>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ full_name: fullName, email, password }),
  });
}

export function login(email: string, password: string) {
  return request<Token>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe() {
  return request<User>("/users/me");
}

// ---------- DSA ----------

export function getProblems() {
  return request<ProblemWithStats[]>("/dsa/problems");
}

export function getDsaStats() {
  return request<DsaStats>("/dsa/stats");
}

export function getStreaks() {
  return request<StreakStats>(
    `/dsa/streaks?tz=${encodeURIComponent(browserTimeZone())}`,
  );
}

export function getProblem(id: number) {
  return request<ProblemDetail>(`/dsa/problems/${id}`);
}

export function startAttempt(problemId: number) {
  return request<Attempt>(`/dsa/problems/${problemId}/attempts`, {
    method: "POST",
  });
}

export function finishAttempt(attemptId: string, solutionUrl: string | null) {
  return request<Attempt>(`/dsa/attempts/${attemptId}/finish`, {
    method: "POST",
    body: JSON.stringify({ solution_url: solutionUrl }),
  });
}

export function discardAttempt(attemptId: string) {
  return request<void>(`/dsa/attempts/${attemptId}`, { method: "DELETE" });
}

// ---------- Tasks ----------

export function getTasks(status: "open" | "completed") {
  return request<Task[]>(`/tasks?status=${status}`);
}

export function createTask(input: TaskInput) {
  return request<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateTask(id: string, input: TaskInput) {
  return request<Task>(`/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function completeTask(id: string) {
  return request<Task>(
    `/tasks/${id}/complete?tz=${encodeURIComponent(browserTimeZone())}`,
    { method: "POST" },
  );
}

export function reopenTask(id: string) {
  return request<Task>(`/tasks/${id}/reopen`, { method: "POST" });
}

export function deleteTask(id: string) {
  return request<void>(`/tasks/${id}`, { method: "DELETE" });
}

// ---------- Learn ----------

export type SubjectSummary = {
  slug: string;
  title: string;
  description: string;
  lesson_count: number;
  completed_count: number;
};

export type LessonSummary = {
  slug: string;
  title: string;
  completed: boolean;
};

export type ModuleOutline = {
  slug: string;
  title: string;
  lessons: LessonSummary[];
};

export type SubjectDetail = SubjectSummary & {
  modules: ModuleOutline[];
  next_lesson_slug: string | null;
};

export type ExerciseStep = {
  instruction: string;
  command: string;
  expected_output: string;
  check: string;
};

export type Exercise = {
  kind: string;
  steps: ExerciseStep[];
};

export type LessonDetail = {
  slug: string;
  title: string;
  body: string;
  subject_slug: string;
  subject_title: string;
  module_slug: string;
  module_title: string;
  completed: boolean;
  completed_at: string | null;
  previous_slug: string | null;
  next_slug: string | null;
  exercise: Exercise | null;
};

export type LessonProgress = {
  slug: string;
  completed: boolean;
  completed_at: string | null;
};

function lessonPath(subjectSlug: string, lessonSlug: string): string {
  return `/learn/subjects/${encodeURIComponent(subjectSlug)}/lessons/${encodeURIComponent(lessonSlug)}`;
}

export function getSubjects() {
  return request<SubjectSummary[]>("/learn/subjects");
}

export function getSubject(subjectSlug: string) {
  return request<SubjectDetail>(
    `/learn/subjects/${encodeURIComponent(subjectSlug)}`,
  );
}

export function getLesson(subjectSlug: string, lessonSlug: string) {
  return request<LessonDetail>(lessonPath(subjectSlug, lessonSlug));
}

export function completeLesson(subjectSlug: string, lessonSlug: string) {
  return request<LessonProgress>(`${lessonPath(subjectSlug, lessonSlug)}/progress`, {
    method: "PUT",
  });
}

export function uncompleteLesson(subjectSlug: string, lessonSlug: string) {
  return request<void>(`${lessonPath(subjectSlug, lessonSlug)}/progress`, {
    method: "DELETE",
  });
}


// ---------- Build ----------

export type BuildPageRef = {
  module_slug: string;
  page_slug: string;
  title: string;
};

export type BuildProjectSummary = {
  slug: string;
  title: string;
  description: string;
  module_count: number;
  page_count: number;
  completed_count: number;
};

export type BuildPageSummary = {
  slug: string;
  title: string;
  kind: string;
  completed: boolean;
};

export type BuildModuleOutline = {
  slug: string;
  title: string;
  summary: string;
  page_count: number;
  completed_count: number;
  pages: BuildPageSummary[];
};

export type BuildProjectDetail = BuildProjectSummary & {
  modules: BuildModuleOutline[];
  next_page: BuildPageRef | null;
};

export type CheckpointFile = {
  path: string;
  content: string;
};

export type BuildPageDetail = {
  slug: string;
  title: string;
  kind: string;
  body: string;
  hints: string[];
  project_slug: string;
  project_title: string;
  module_slug: string;
  module_title: string;
  page_number: number;
  module_page_count: number;
  completed: boolean;
  completed_at: string | null;
  previous: BuildPageRef | null;
  next: BuildPageRef | null;
  checkpoint: CheckpointFile[];
};

export type BuildPageProgress = {
  slug: string;
  completed: boolean;
  completed_at: string | null;
};

function buildPagePath(
  projectSlug: string,
  moduleSlug: string,
  pageSlug: string,
): string {
  return `/build/projects/${encodeURIComponent(projectSlug)}/modules/${encodeURIComponent(moduleSlug)}/pages/${encodeURIComponent(pageSlug)}`;
}

export function getBuildProjects() {
  return request<BuildProjectSummary[]>("/build/projects");
}

export function getBuildProject(projectSlug: string) {
  return request<BuildProjectDetail>(
    `/build/projects/${encodeURIComponent(projectSlug)}`,
  );
}

export function getBuildPage(
  projectSlug: string,
  moduleSlug: string,
  pageSlug: string,
) {
  return request<BuildPageDetail>(
    buildPagePath(projectSlug, moduleSlug, pageSlug),
  );
}

export function markBuildPageDone(
  projectSlug: string,
  moduleSlug: string,
  pageSlug: string,
) {
  return request<BuildPageProgress>(
    `${buildPagePath(projectSlug, moduleSlug, pageSlug)}/progress`,
    { method: "PUT" },
  );
}

export function clearBuildPageDone(
  projectSlug: string,
  moduleSlug: string,
  pageSlug: string,
) {
  return request<void>(
    `${buildPagePath(projectSlug, moduleSlug, pageSlug)}/progress`,
    { method: "DELETE" },
  );
}