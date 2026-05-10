import { useAppStore } from '@/stores/app'
import { messages } from './messages'

export function useI18n() {
  const store = useAppStore()

  function t(path, params) {
    const lang = store.language || 'zh-CN'
    const keys = path.split('.')
    let value = messages[lang]
    for (const key of keys) {
      if (value == null) break
      value = value[key]
    }
    if (value != null) {
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          value = String(value).replace(new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'g'), String(v))
        }
      }
      return value
    }
    // fallback to en-US
    value = messages['en-US']
    for (const key of keys) {
      if (value == null) break
      value = value[key]
    }
    if (value != null) {
      if (params) {
        for (const [k, v] of Object.entries(params)) {
          value = String(value).replace(new RegExp(`\\{\\{\\s*${k}\\s*\\}\\}`, 'g'), String(v))
        }
      }
      return value
    }
    return path
  }

  return { t, language: store.language }
}
