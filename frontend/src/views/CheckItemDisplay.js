/**
 * Pure display/formatting logic for CheckItemView.
 * Extracted for testability (no Vue/DOM dependencies).
 */

/**
 * Identify the CSV test item type from a filename by matching keywords.
 * @param {string} filename
 * @returns {string|null} Item type or null if unrecognized
 */
export function identifyCsvType(filename) {
  if (!filename || typeof filename !== 'string') return null
  const lower = filename.toLowerCase()
  if (lower.includes('bt-ota')) return 'BT-OTA'
  if (lower.includes('charging')) return 'Charging'
  if (lower.includes('fact')) return 'FACT'
  if (lower.includes('isb')) return 'ISB'
  if (lower.includes('touch-cal-post')) return 'Touch-CAL-Post'
  if (lower.includes('cosmetic')) return 'Cosmetic'
  return null
}

/**
 * Format parsed summary statistics for display based on file type.
 * @param {string} fileType - One of: sn_mapping, checkpoint_schedule, test_plan, test_schedule
 * @param {object|null} summary - Parsed summary object from API
 * @returns {string} Formatted display string
 */
export function formatStats(fileType, summary) {
  if (!summary) return ''
  switch (fileType) {
    case 'sn_mapping': {
      const parts = []
      if (summary.sn_count) parts.push(`${summary.sn_count} SNs`)
      if (summary.config_count) parts.push(`${summary.config_count} configs`)
      if (summary.wf_count) parts.push(`${summary.wf_count} WFs`)
      return parts.join(', ') || ''
    }
    case 'checkpoint_schedule': {
      const parts = []
      if (summary.wf_count) parts.push(`${summary.wf_count} WFs`)
      if (summary.cp_count) parts.push(`${summary.cp_count} CPs`)
      return parts.join(', ') || ''
    }
    case 'test_plan': {
      const parts = []
      if (summary.wf_count) parts.push(`${summary.wf_count} WFs`)
      if (summary.test_count) parts.push(`${summary.test_count} tests`)
      return parts.join(', ') || ''
    }
    case 'test_schedule': {
      const parts = []
      if (summary.segment_count) parts.push(`${summary.segment_count} schedule segments`)
      return parts.join(', ') || ''
    }
    default:
      return JSON.stringify(summary)
  }
}

/**
 * Format a date string for display using locale date formatting.
 * @param {string} dateStr - ISO date string or similar
 * @returns {string} Formatted date or original string if invalid
 */
export function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return d.toLocaleDateString()
}
