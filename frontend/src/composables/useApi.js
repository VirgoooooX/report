import { ref } from 'vue'

export async function requestJson(url, options = {}) {
  const resp = await fetch(url, options)
  const contentType = resp.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await resp.json() : await resp.text()
  if (!resp.ok) {
    const message = (payload && payload.error) || payload || `HTTP ${resp.status}`
    throw new Error(message)
  }
  return payload
}

export function useApi(url) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchData(params = {}) {
    loading.value = true
    error.value = null
    try {
      const query = new URLSearchParams(params).toString()
      const fullUrl = query ? `${url}?${query}` : url
      data.value = await requestJson(fullUrl)
      return data.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function post(body) {
    loading.value = true
    error.value = null
    try {
      data.value = await requestJson(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      return data.value
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return { data, loading, error, fetch: fetchData, post }
}
