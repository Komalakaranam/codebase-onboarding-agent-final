/**
 * The backend stores `created_at` as UTC (see backend/app/database.py),
 * but SQLite drops timezone info on the way out, so the JSON string has
 * no "Z"/offset suffix. `new Date(...)` treats a bare string like that as
 * local time, which would silently mislabel every timestamp. Force UTC
 * interpretation before formatting.
 */
export function formatUtcTimestamp(isoString) {
  const hasTimezone = /Z|[+-]\d\d:\d\d$/.test(isoString);
  const date = new Date(hasTimezone ? isoString : `${isoString}Z`);
  return date.toLocaleString();
}
