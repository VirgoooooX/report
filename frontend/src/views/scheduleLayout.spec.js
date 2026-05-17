import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const globalStyles = readFileSync(new URL('../assets/styles/global.css', import.meta.url), 'utf8')
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

function zIndexValue(rule) {
  const match = rule.match(/z-index\s*:\s*(\d+)\s*;/)
  return match ? Number(match[1]) : null
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
  /selectedDate/.test(scheduleTimeline) && /toggleDateHighlight/.test(scheduleTimeline),
  'date headers should allow toggling a highlighted date column'
)
assert.ok(
  /'selected-date': isSelectedDate\(column\.date\)/.test(scheduleTimeline),
  'selected date should add a column highlight class to date headers and cells'
)
assert.ok(
  /scrollTodayIntoView/.test(scheduleTimeline),
  'schedule timeline should center the current date on load'
)
assert.ok(
  /actual-progress/.test(scheduleTimeline),
  'schedule timeline should render actual completion progress cells'
)
assert.ok(
  /plan-progress-rail/.test(scheduleTimeline),
  'planned test ranges should render as rail elements with capsule endpoints'
)
assert.ok(
  /in planSegmentsOnDate/.test(scheduleTimeline),
  'planned rails should be rendered per test segment instead of one merged lane span'
)
assert.ok(
  /plan-progress-start/.test(scheduleTimeline) && /plan-progress-end/.test(scheduleTimeline),
  'planned rails should have per-test rounded start and end caps'
)
assert.ok(
  /isTestStartDate\(segment, column\.date\)/.test(scheduleTimeline) &&
    /isTestEndDate\(segment, column\.date\)/.test(scheduleTimeline),
  'planned rail caps should be based on each test segment boundary'
)
assert.ok(
  /date >= start && date <= end/.test(scheduleTimeline),
  'planned rails should render across each test calendar range so Sunday columns do not cut progress'
)
assert.ok(
  /actual-progress-rail/.test(scheduleTimeline),
  'actual completion should use a visible solid rail instead of only tinting the cell background'
)
assert.ok(
  /in actualSegmentsOnDate/.test(scheduleTimeline),
  'actual completion should render per test segment instead of one merged lane span'
)
assert.ok(
  /actual-progress-start/.test(scheduleTimeline) && /actual-progress-end/.test(scheduleTimeline),
  'actual completion segments should keep capsule endpoints per test'
)
assert.ok(
  hasDeclaration(ruleBody(scheduleTimelineStyles, '.actual-progress-start'), 'left', '-1px') &&
    hasDeclaration(ruleBody(scheduleTimelineStyles, '.actual-progress-end'), 'right', '-1px'),
  'actual completion rail should fully cover the underlying plan rail at segment caps'
)
assert.ok(
  /isActualSegmentStartDate\(segment, column\.date\)/.test(scheduleTimeline) &&
    /isActualSegmentEndDate\(segment, row, column\.date\)/.test(scheduleTimeline),
  'actual rail caps should be based on each completed test segment boundary'
)
assert.ok(
  /actual-progress-tip/.test(scheduleTimeline),
  'actual completion should mark the current completed CP endpoint'
)
assert.ok(
  /cp-current/.test(scheduleTimeline),
  'current CP marker should have a dedicated visual class'
)
assert.ok(
  !/box-shadow\s*:\s*inset 3px 0 0 var\(--schedule-color\)/.test(scheduleTimelineStyles),
  'test start cells should not render vertical boundary bars'
)
assert.ok(
  !/box-shadow\s*:\s*inset -3px 0 0 var\(--schedule-color\)/.test(scheduleTimelineStyles),
  'test end cells should not render vertical boundary bars'
)

const pageRule = ruleBody(scheduleViewStyles, '.schedule-page')
assert.ok(
  hasDeclaration(pageRule, 'width', '100%') &&
    hasDeclaration(pageRule, 'height', '100%') &&
    hasDeclaration(pageRule, 'padding', '4px 5px 8px'),
  'schedule-page should directly fill the app viewport container'
)
assert.ok(
  hasDeclaration(pageRule, 'overflow', 'hidden'),
  'schedule-page should prevent the outer page from creating a second vertical scrollbar'
)
assert.ok(
  !/:global\((?:html|body|\.main):has\(\.schedule-page\)\)/.test(scheduleViewStyles),
  'schedule view should not change the shared app shell through global :has() selectors'
)

const mainRule = ruleBody(globalStyles, '.main')
assert.ok(
  hasDeclaration(mainRule, 'width', '100%') &&
    hasDeclaration(mainRule, 'height', 'calc\\(100vh - 56px\\)') &&
    hasDeclaration(mainRule, 'max-width', 'none') &&
    hasDeclaration(mainRule, 'margin', '0') &&
    hasDeclaration(mainRule, 'padding', '0') &&
    hasDeclaration(mainRule, 'overflow', 'auto'),
  'main should be a stable full-viewport container for every route'
)

const pageContainerRule = ruleBody(globalStyles, '.main > .page-container')
assert.ok(
  /width\s*:\s*min\(100%, var\(--layout-max-width\)\)\s*;/.test(pageContainerRule) &&
    hasDeclaration(pageContainerRule, 'margin', '0 auto') &&
    /padding\s*:\s*var\(--page-padding-y\) var\(--page-padding-x\) var\(--page-padding-bottom\)\s*;/.test(pageContainerRule),
  'ordinary pages should keep the old centered shell inside the full-viewport main container'
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

const planRailRule = ruleBody(scheduleTimelineStyles, '.plan-progress-rail')
assert.ok(
  /box-shadow\s*:/.test(planRailRule) && /inset 1px 0 0/.test(planRailRule) && /inset -1px 0 0/.test(planRailRule),
  'planned rails should show per-date left/right borders inside each date cell'
)

const actualRailRule = ruleBody(scheduleTimelineStyles, '.actual-progress-rail')
assert.ok(
  !/box-shadow\s*:/.test(actualRailRule) && !/border\s*:/.test(actualRailRule),
  'actual completion rail should be a borderless opaque overlay'
)
assert.ok(
  /background\s*:\s*color-mix\(in srgb, var\(--completed-cp-color\) 14%, var\(--bg-card\)\)\s*;/.test(actualRailRule),
  'actual completion rail should use a slightly darker gray mix instead of transparent alpha stacking'
)

const pendingCpRule = ruleBody(scheduleTimelineStyles, '.cp-text.cp-pending')
assert.ok(
  /background\s*:\s*color-mix\(in srgb, var\(--pending-cp-color\) 88%, var\(--bg-card\)\)\s*;/.test(pendingCpRule),
  'pending CP markers should use the requested blue fill color'
)

const selectedDateRule = pseudoRuleBody(scheduleTimelineStyles, '.day-cell.selected-date::before')
const cpTextRule = ruleBody(scheduleTimelineStyles, '.cp-text')
const actualTipRule = pseudoRuleBody(scheduleTimelineStyles, '.actual-progress-tip::after')
assert.ok(
  zIndexValue(selectedDateRule) > zIndexValue(cpTextRule) &&
    zIndexValue(selectedDateRule) > zIndexValue(actualTipRule) &&
    zIndexValue(selectedDateRule) > zIndexValue(planRailRule) &&
    zIndexValue(selectedDateRule) > zIndexValue(actualRailRule),
  'selected date column overlay should render above rails, CP markers, and the current progress tip'
)

assert.ok(
  !/\.day-cell\.sunday\s*\{/.test(scheduleTimelineStyles),
  'Sunday date cells should not have a separate CSS rule on themselves (handled by the default gray base)'
)

assert.ok(
  !scheduleTimelineStyles.includes('.day-cell.sunday::after'),
  'Sunday date cells should not have a ::after pseudo-element overlay (requirement 2.1)'
)

const sundayPlanRailRule = ruleBody(scheduleTimelineStyles, '.day-cell.sunday .plan-progress-rail')
assert.ok(
  /opacity\s*:\s*0?\.[0-9]+\s*;/.test(sundayPlanRailRule) ||
    /color-mix\([^)]*var\(--plan-color\)[^)]*var\(--bg-card\)/.test(sundayPlanRailRule),
  'plan rail should be visually dimmed when crossing Sunday columns'
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
