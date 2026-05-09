function pad(value: number) {
  return String(value).padStart(2, '0');
}

export function formatLocalDateInputOffset(days: number) {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
}
