import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const navSource = readFileSync(resolve(__dirname, 'NavBar.vue'), 'utf8')
const checkItemSource = readFileSync(resolve(__dirname, '../views/CheckItemView.vue'), 'utf8')
const settingsSource = readFileSync(resolve(__dirname, '../views/SettingsView.vue'), 'utf8')
const storeSource = readFileSync(resolve(__dirname, '../stores/app.js'), 'utf8')
const messagesSource = readFileSync(resolve(__dirname, '../i18n/messages.js'), 'utf8')

assert.match(navSource, /class="nav-data-ops-btn"/)
assert.match(navSource, /to="\/checkitem"/)
assert.match(navSource, /t\('nav\.dataOperations'\)/)
assert.match(navSource, /class="mobile-data-ops-link"/)
assert.doesNotMatch(navSource, /upload\.idle/)
assert.doesNotMatch(messagesSource, /上传 Rawdata|Upload Rawdata/)

assert.match(checkItemSource, /t\('checkitem\.uploadDailyReportTitle'\)/)
assert.doesNotMatch(checkItemSource, /UploadDialog/)
assert.doesNotMatch(checkItemSource, /showUploadDialog/)

assert.match(storeSource, /aiEnabled = ref\(localStorage\.getItem\('dashboard-ai-enabled'\) !== 'false'\)/)
assert.match(storeSource, /function setAiEnabled\(enabled\)/)
assert.match(settingsSource, /store\.setAiEnabled\(\$event\.target\.checked\)/)
assert.match(settingsSource, /<button :class="\{ active: tab === 'assistant' \}" @click="tab = 'assistant'">\{\{ t\('settings\.tabAssistant'\) \}\}<\/button>/)
assert.match(settingsSource, /<section v-else-if="tab === 'assistant'" class="rules-grid">/)
assert.match(settingsSource, /<div v-if="store\.aiEnabled" class="panel">/)
assert.doesNotMatch(settingsSource, /<section class="panel ai-feature-panel">[\s\S]*<div class="settings-tabs"/)
assert.match(messagesSource, /aiFeature:/)
assert.match(messagesSource, /aiFeatureDesc:/)

console.log('NavBar data operations UI contract tests passed')
