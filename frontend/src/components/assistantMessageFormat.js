const SOURCE_RE = /(?:数据来源|来源)[:：]\s*`?([^`。.\n]+)`?[。.]*\s*$/i

function cleanText(value) {
  return String(value || '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()
}

function stripBullet(value) {
  return cleanText(value).replace(/^[-*•]\s*/, '')
}

function splitLooseList(value) {
  return cleanText(value)
    .split(/[，、,]\s*/)
    .map((item) => item.replace(/^(其余|其中|另外)\s*/, '').trim())
    .filter(Boolean)
}

function splitFirstSentence(value) {
  const text = cleanText(value)
  const match = text.match(/^(.+?[。!！?？])\s*(.*)$/)
  if (!match) return [text, '']
  return [match[1], match[2]]
}

function cleanSource(value) {
  return cleanText(value).replace(/[（(].*$/, '').trim()
}

export function formatAssistantContent(content) {
  let text = String(content || '').trim()
  if (!text) return []

  const blocks = []
  const sourceMatch = text.match(SOURCE_RE)
  if (sourceMatch) {
    text = text.slice(0, sourceMatch.index).trim()
  }

  const rawLines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  let pendingList = []

  function flushList() {
    if (!pendingList.length) return
    blocks.push({ type: 'list', items: pendingList })
    pendingList = []
  }

  for (const line of rawLines) {
    if (/^[-*•]\s+/.test(line)) {
      pendingList.push(stripBullet(line))
      continue
    }
    flushList()

    const distribution = line.match(/^(.+?[：:])\s*(.+)$/)
    if (distribution && /分布|排序|如下|包括/.test(distribution[1])) {
      const [firstSentence, remainder] = splitFirstSentence(distribution[2])
      const items = splitLooseList(firstSentence)
      if (items.length > 1) {
        blocks.push({ type: 'paragraph', text: `${distribution[1]} ${items[0]}` })
        blocks.push({ type: 'list', items: items.slice(1) })
        if (remainder) {
          blocks.push({ type: 'paragraph', text: remainder })
        }
        continue
      }
    }

    blocks.push({ type: 'paragraph', text: cleanText(line) })
  }
  flushList()

  if (sourceMatch) {
    blocks.push({ type: 'source', text: cleanSource(sourceMatch[1]) })
  }

  return blocks
}

export function hasSourceBlock(blocks) {
  return Array.isArray(blocks) && blocks.some((block) => block.type === 'source')
}
