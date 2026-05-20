import assert from 'node:assert/strict'
import { formatAssistantContent } from './assistantMessageFormat.js'

const compact = formatAssistantContent(
  '根据分析结果，不良Config分布为：R2CNM故障率最高（8.9%），其次是R1FNF（6.7%），其余R3（0.5%）、R4（0.3%）及Unknown（0.2%）故障率较低。 数据来源：调用 analyze_check_item_failure_rate。'
)

assert.equal(compact[0].type, 'paragraph')
assert.match(compact[0].text, /R2CNM/)
assert.equal(compact[1].type, 'list')
assert.deepEqual(compact[1].items.slice(0, 2), [
  '其次是R1FNF（6.7%）',
  'R3（0.5%）',
])
assert.equal(compact.at(-1).type, 'source')
assert.equal(compact.at(-1).text, '调用 analyze_check_item_failure_rate')

const bullets = formatAssistantContent('结论：R2CNM最高。\n- R2CNM: 3F/3T，100.0%\n- R1FNF: 1F/2T，50.0%')
assert.equal(bullets[1].type, 'list')
assert.deepEqual(bullets[1].items, ['R2CNM: 3F/3T，100.0%', 'R1FNF: 1F/2T，50.0%'])

const markdown = formatAssistantContent('- **R2CNM**：故障率8.9%\n- `R1FNF`：故障率6.7%')
assert.deepEqual(markdown[0].items, ['R2CNM：故障率8.9%', 'R1FNF：故障率6.7%'])

const verboseSource = formatAssistantContent('结论。数据来源：调用 analyze_check_item_failure_rate（维度为 config，限制20条）。')
assert.equal(verboseSource.at(-1).text, '调用 analyze_check_item_failure_rate')

console.log('Assistant message formatting tests passed')
