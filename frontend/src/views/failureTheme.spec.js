import assert from 'node:assert/strict'
import { getFailureTheme } from './failureTheme.js'

const light = getFailureTheme('light')
const dark = getFailureTheme('dark')

assert.equal(light.isDark, false)
assert.equal(dark.isDark, true)

assert.notEqual(dark.heatmapEmptyBg, '#ffffff')
assert.notEqual(dark.tooltipBg, '#ffffff')
assert.notEqual(dark.labelBadgeBg, light.labelBadgeBg)
assert.notEqual(dark.gridColor, light.gridColor)

console.log('failureTheme dark-mode tests passed')
