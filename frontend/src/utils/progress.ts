export function percent(done: number, total: number): number {
  return total === 0 ? 0 : Math.round((done / total) * 100);
}