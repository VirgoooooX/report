import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const scheduleView = readFileSync(new URL('./ScheduleView.vue', import.meta.url), 'utf8')
const scheduleTimeline = readFileSync(new URL('../components/ScheduleTimeline.vue', import.meta.url), 'utf8')

function styleBlock(source) {
  const match = source.match(/<style scoped>([\s\S]*?)<\/style>/)
  assert.ok(match, 'Expected a scoped style block')
  return match[1]
}

function ruleBody(styles, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = styles.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\}`, 'm'))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
}

function pseudoRuleBody(styles, selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = styles.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\}`, 'm'))
  assert.ok(match, `Expected CSS rule for ${selector}`)
  return match[1]
}

function hasDeclaration(rule, property, value) {
  return new RegExp(`${property}\\s*:\\s*${value}\\s*;`).test(rule)
}

const scheduleViewStyles = styleBlock(scheduleView)
const scheduleTimelineStyles = styleBlock(scheduleTimeline)

assert.ok(
  /ref="sheetScroll"/.test(scheduleTimeline),
  'schedule timeline should keep a scroll container ref for date centering'
)
assert.ok(
  /:data-date="column\.date"/.test(scheduleTimeline),
  'date cells should expose their date for centering today'
)
assert.ok(
  /scrollTodayIntoView/.test(scheduleTimeline),
  'schedule timeline should center the current date on load'
)
assert.ok(
  /actual-progress/.test(scheduleTimeline),
  'schedule timeline should render actual completion progress cells'
)

const pageRule = ruleBody(scheduleViewStyles, '.schedule-page')
assert.ok(
  hasDeclaration(pageRule, 'height', '100%'),
  'schedule-page should fill the available viewport below the nav'
)
assert.ok(
  hasDeclaration(pageRule, 'overflow', 'hidden'),
  'schedule-page should prevent the outer page from creating a second vertical scrollbar'
)

const scrollRule = ruleBody(scheduleTimelineStyles, '.sheet-scroll')
assert.ok(
  hasDeclaration(scrollRule, 'height', '100%'),
  'sheet-scroll should inherit the timeline panel height'
)
assert.ok(
  hasDeclaration(scrollRule, 'overflow-x', 'auto'),
  'sheet-scroll should keep horizontal scrolling for the timeline grid'
)
assert.ok(
  hasDeclaration(scrollRule, 'overflow-y', 'auto'),
  'sheet-scroll should own the vertical scrolling inside the frozen layout'
)

const stickyRule = ruleBody(scheduleTimelineStyles, '.sticky-col')
assert.ok(
  hasDeclaration(stickyRule, 'position', 'sticky'),
  'sticky-col should keep the left header column fixed while the grid scrolls'
)
assert.ok(
  hasDeclaration(stickyRule, 'left', '0'),
  'sticky-col should pin itself to the left edge of the timeline viewport'
)
assert.ok(
  /box-shadow\s*:/.test(stickyRule),
  'sticky-col should visually separate the frozen column from the horizontally scrolling dates'
)

const edgeMarkerRule = ruleBody(scheduleTimelineStyles, '.edge-marker')
assert.ok(
  hasDeclaration(edgeMarkerRule, 'z-index', '2'),
  'edge markers should stay below the sticky config column while horizontally scrolling'
)

const hiddenScrollbarRule = pseudoRuleBody(scheduleTimelineStyles, '.sheet-scroll::-webkit-scrollbar')
assert.ok(
  hasDeclaration(hiddenScrollbarRule, 'height', '0'),
  'horizontal scrollbar should stay hidden until the timeline is hovered'
)

const hoverScrollbarRule = pseudoRuleBody(scheduleTimelineStyles, '.sheet-scroll:hover::-webkit-scrollbar')
assert.ok(
  hasDeclaration(hoverScrollbarRule, 'height', '6px'),
  'horizontal scrollbar should reappear when the timeline region is hovered'
)

console.log('scheduleLayout tests passed')
