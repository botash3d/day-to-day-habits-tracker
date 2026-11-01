const KIND_LABELS: Record<string, string> = {
  explain: "Explain",
  exercise: "Exercise",
  run: "Run",
  check: "Check",
  stuck: "Stuck?",
  recap: "Recap",
};

export function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind;
}