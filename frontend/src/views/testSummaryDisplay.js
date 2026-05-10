export function testSummaryCellClass(result) {
  if (!result) return 'ts-not-started'
  if (result.status === 'not_started') return 'ts-not-started'
  if (result.status === 'in_progress') return 'ts-in-progress'
  if (result.spec > 0) return 'ts-fail'
  if (result.strife > 0) return 'ts-strife'
  return 'ts-pass'
}
