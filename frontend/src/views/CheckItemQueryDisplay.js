/**
 * Pure display/formatting logic for the SN Test History (Raw Data) mode
 * in QueryCenter. Extracted for testability (no Vue/DOM dependencies).
 */

/**
 * Parse test_params JSON for display in the parameter table.
 * Handles null, object, valid JSON string, and invalid JSON string.
 * @param {*} paramsJson - null, object, or JSON string
 * @returns {object|null} Parsed params object or null
 */
export function parseTestParams(paramsJson) {
  if (!paramsJson) return null
  if (typeof paramsJson === 'object') return paramsJson
  try { return JSON.parse(paramsJson) } catch { return null }
}

/**
 * Format end_time for display. Returns a locale-formatted date/time string.
 * @param {string|null|undefined} endTime - Timestamp string (e.g. "2026-05-14 21:34:13")
 * @returns {string} Formatted string or empty string for invalid/missing input
 */
export function formatEndTime(endTime) {
  if (!endTime) return ''
  const d = new Date(endTime)
  if (isNaN(d.getTime())) return endTime
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * Check if a record is a FAIL record.
 * @param {object} record - A raw test record with a `status` field
 * @returns {boolean} True if the record status is 'FAIL'
 */
export function isFailRecord(record) {
  if (!record || typeof record !== 'object') return false
  return record.status === 'FAIL'
}

/**
 * Return the CSS class for a status badge based on the status value.
 * @param {string} status - 'PASS' or 'FAIL'
 * @returns {string} CSS class name
 */
export function getRecordStatusClass(status) {
  if (status === 'PASS') return 'badge-pass'
  if (status === 'FAIL') return 'badge-fail'
  return ''
}
