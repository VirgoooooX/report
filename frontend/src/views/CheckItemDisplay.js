/**
 * Pure display/formatting logic for CheckItemView.
 * Extracted for testability (no Vue/DOM dependencies).
 */

export const CHECK_ITEM_TYPES = ['BT-OTA', 'Charging', 'FACT', 'ISB', 'Touch-CAL-Post', 'Cosmetic']

export const REQUIRED_BASE_FILE_TYPES = ['sn_mapping', 'checkpoint_schedule', 'test_plan']

export const OPTIONAL_BASE_FILE_TYPES = ['test_schedule']

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

/**
 * Build a file_type keyed status map from /api/base-files output.
 * @param {Array<object>} files
 * @returns {Record<string, object>}
 */
export function getBaseStatusMap(files) {
  const result = {}
  for (const file of Array.isArray(files) ? files : []) {
    if (file?.file_type) result[file.file_type] = file
  }
  return result
}

/**
 * Return required Base file types missing for Daily Report generation.
 * @param {Array<object>} files
 * @returns {string[]}
 */
export function getMissingRequiredBaseFiles(files) {
  const statusMap = getBaseStatusMap(files)
  return REQUIRED_BASE_FILE_TYPES.filter((fileType) => !statusMap[fileType])
}

/**
 * True when the Base definition set is sufficient to generate/import reports.
 * @param {Array<object>} files
 * @returns {boolean}
 */
export function isBaseReadyForGeneration(files) {
  return getMissingRequiredBaseFiles(files).length === 0
}
