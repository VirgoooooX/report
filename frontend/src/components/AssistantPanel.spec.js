import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const componentSource = readFileSync(resolve(__dirname, 'AssistantPanel.vue'), 'utf8')
const appSource = readFileSync(resolve(__dirname, '../App.vue'), 'utf8')

assert.match(appSource, /import AssistantPanel from '@\/components\/AssistantPanel\.vue'/)
assert.match(appSource, /<AssistantPanel \/>/)

assert.match(componentSource, /requestJson\('\/api\/assistant\/chat'/)
assert.match(componentSource, /page_context: pageContext\(\)/)
assert.match(componentSource, /route\.query/)
assert.match(componentSource, /session_id: sessionId\.value \|\| null/)
assert.match(componentSource, /payload\.tool_calls/)
assert.match(componentSource, /clearChat/)
assert.match(componentSource, /RobotOutlined/)
assert.doesNotMatch(componentSource, /CustomerServiceOutlined/)
assert.match(componentSource, /\.assistant-root\s*\{[\s\S]*top:\s*50%/)
assert.match(componentSource, /\.assistant-root\s*\{[\s\S]*transform:\s*translateY\(-50%\)/)
assert.match(componentSource, /grid-template-columns:\s*1fr 52px/)
assert.match(componentSource, /\.assistant-send\s*\{[\s\S]*align-self:\s*stretch/)
assert.match(componentSource, /\.assistant-send\s*\{[\s\S]*height:\s*auto/)

console.log('AssistantPanel UI contract tests passed')
