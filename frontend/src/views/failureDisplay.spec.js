import assert from 'node:assert/strict'
import {
  chartMetricValue,
  failureMetricDisplay,
  getClampedTooltipPosition,
  heatmapCellDisplay,
  oneLineLabel,
  overviewFailureDisplay,
} from './failureDisplay.js'

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

console.log('failureDisplay formatting tests passed')
