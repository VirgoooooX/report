import { useAppStore } from '@/stores/app'
import { messages } from './messages'

export function useI18n() {
  const store = useAppStore()

  function t(path) {
    const lang = store.language || 'zh-CN'
    const keys = path.split('.')
    let value = messages[lang]
    for (const key of keys) {
      if (value == null) break
      value = value[key]
    }
    if (value != null) return value
    // fallback to en-US
    value = messages['en-US']
    for (const key of keys) {
      if (value == null) break
      value = value[key]
    }
    return value ?? path
  }

  return { t, language: store.language }
}
