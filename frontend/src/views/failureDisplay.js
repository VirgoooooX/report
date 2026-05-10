function toNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : 0
}

export function failureMetricDisplay(item = {}) {
  const spec = toNumber(item.specSnCount ?? item.specSNCount ?? item.specCount ?? item.spec)
  const strife = toNumber(item.strifeSnCount ?? item.strifeSNCount ?? item.strifeCount ?? item.strife)
  const total = toNumber(item.totalSamples ?? item.totalSampleSize ?? item.totalTests ?? item.total)

  if (spec > 0) return `${spec}F/${total}T`
  if (strife > 0) return `${strife}SF/${total}T`
  return `0F/${total}T`
}

export function strifeMetricDisplay(item = {}) {
  const strife = toNumber(item.strifeSnCount ?? item.strifeSNCount ?? item.strifeCount ?? item.strife)
  const total = toNumber(item.totalSamples ?? item.totalSampleSize ?? item.totalTests ?? item.total)
  return `${strife}SF/${total}T`
}

export function overviewFailureDisplay(summary = {}) {
  return failureMetricDisplay({
    specSnCount: summary.specSNCount,
    strifeSnCount: summary.strifeSNCount,
    totalSamples: summary.totalSampleSize,
  })
}

export function heatmapCellDisplay(cell, mode = 'spec') {
  if (!cell) return '-'
  if (mode === 'strife') return strifeMetricDisplay(cell)
  return failureMetricDisplay(cell)
}

export function chartMetricValue(item = {}) {
  const explicitPpm = item.specFailureRate ?? item.specRatePpm
  if (explicitPpm != null) return toNumber(explicitPpm)

  const specRatePercent = item.specRate
  if (specRatePercent != null) return Math.round(toNumber(specRatePercent) * 10000)

  const spec = toNumber(item.specSnCount ?? item.specSNCount ?? item.specCount ?? item.spec)
  const total = toNumber(item.totalSamples ?? item.totalSampleSize ?? item.totalTests ?? item.total)
  return total > 0 ? Math.round((spec / total) * 1000000) : 0
}

export function oneLineLabel(value = '') {
  return String(value).replace(/\s+/g, ' ').trim()
}

export function formatPpmTick(value) {
  return toNumber(value).toLocaleString()
}

export function getClampedTooltipPosition(pointer, viewport, tooltip = { width: 240, height: 160 }, offset = 14) {
  const preferredLeft = pointer.x + offset
  const preferredTop = pointer.y + offset
  const maxLeft = Math.max(offset, viewport.width - tooltip.width - offset)
  const maxTop = Math.max(offset, viewport.height - tooltip.height - offset)

  return {
    left: Math.min(Math.max(offset, preferredLeft), maxLeft),
    top: Math.min(Math.max(offset, preferredTop), maxTop)
  }
}
