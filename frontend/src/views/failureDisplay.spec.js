import assert from 'node:assert/strict'
import {
  chartMetricValue,
  failureMetricDisplay,
  getClampedTooltipPosition,
  heatmapBackgroundColor,
  heatmapCellDisplay,
  oneLineLabel,
  overviewFailureDisplay,
} from './failureDisplay.js'
import { getFailureTheme } from './failureTheme.js'

assert.equal(
  failureMetricDisplay({ specSnCount: 3, strifeSnCount: 8, totalSamples: 40 }),
  '3F/40T',
)

assert.equal(
  failureMetricDisplay({ specSnCount: 0, strifeSnCount: 8, totalSamples: 40 }),
  '8SF/40T',
)

assert.equal(
  failureMetricDisplay({ specSnCount: 0, strifeSnCount: 0, totalSamples: 40 }),
  '0F/40T',
)

assert.equal(
  heatmapCellDisplay(
    { specSnCount: 0, strifeSnCount: 2, totalSamples: 16, display: '2SF/16T' },
    'spec',
  ),
  '2SF/16T',
)

assert.equal(
  overviewFailureDisplay({ specSNCount: 0, strifeSNCount: 5, totalSampleSize: 100 }),
  '5SF/100T',
)

assert.equal(
  chartMetricValue({ specSnCount: 82, totalSamples: 1016 }),
  Math.round((82 / 1016) * 1000000),
)

assert.equal(oneLineLabel('WF 25 - Non Op Storage\nTaber Abrasion'), 'WF 25 - Non Op Storage Taber Abrasion')

assert.deepEqual(
  getClampedTooltipPosition(
    { x: 100, y: 120 },
    { width: 1000, height: 800 },
    { width: 240, height: 160 },
    14
  ),
  { left: 114, top: 134 },
)

assert.deepEqual(
  getClampedTooltipPosition(
    { x: 980, y: 760 },
    { width: 1000, height: 800 },
    { width: 240, height: 160 },
    14
  ),
  { left: 746, top: 626 },
)

const lightTheme = getFailureTheme('light')

assert.equal(
  heatmapBackgroundColor(null, 'spec', 30, lightTheme),
  lightTheme.heatmapEmptyBg,
)

assert.equal(
  heatmapBackgroundColor(
    { totalCount: 9, specSnCount: 1, strifeSnCount: 0 },
    'spec',
    30,
    lightTheme,
  ),
  lightTheme.heatmapColors.spec[0],
)

assert.equal(
  heatmapBackgroundColor(
    { totalCount: 15, specSnCount: 0, strifeSnCount: 2 },
    'spec',
    30,
    lightTheme,
  ),
  lightTheme.heatmapColors.strife[1],
)

assert.equal(
  heatmapBackgroundColor(
    { totalCount: 21, specSnCount: 2, strifeSnCount: 0 },
    'total',
    30,
    lightTheme,
  ),
  lightTheme.heatmapColors.total[2],
)

console.log('failureDisplay formatting tests passed')
