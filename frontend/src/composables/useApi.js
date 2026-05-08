import { ref } from 'vue'

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
      const resp = await fetch(fullUrl)
      if (!resp.ok) {
        let msg = `HTTP ${resp.status}`
        try { const j = await resp.json(); if (j.error) msg = j.error } catch {}
        throw new Error(msg)
      }
      data.value = await resp.json()
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
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      if (!resp.ok) throw new Error(await resp.text())
      data.value = await resp.json()
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
