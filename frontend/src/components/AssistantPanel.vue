<template>
  <div class="assistant-root">
    <button
      v-if="!open"
      class="assistant-fab"
      type="button"
      title="AI Assistant"
      aria-label="Open AI Assistant"
      @click="open = true"
    >
      <RobotOutlined />
    </button>

    <aside v-else class="assistant-panel" aria-label="AI Assistant">
      <header class="assistant-header">
        <div>
          <div class="assistant-title">AI Assistant</div>
          <div v-if="expiresAt" class="assistant-expiry">Context resets at {{ expiryLabel }}</div>
        </div>
        <div class="assistant-header-actions">
          <button class="assistant-icon-btn" type="button" title="Clear" aria-label="Clear chat" @click="clearChat">
            <DeleteOutlined />
          </button>
          <button class="assistant-icon-btn" type="button" title="Close" aria-label="Close AI Assistant" @click="open = false">
            <CloseOutlined />
          </button>
        </div>
      </header>

      <div ref="messagesEl" class="assistant-messages">
        <div v-if="!messages.length" class="assistant-empty">
          可以问 SN、WF/Config、FA、Raw History 或整体概览。
        </div>
        <div
          v-for="(msg, index) in messages"
          :key="`${msg.role}-${index}`"
          class="assistant-message"
          :class="`assistant-message--${msg.role}`"
        >
          <div class="assistant-bubble">
            <template v-if="msg.role === 'assistant'">
              <div class="assistant-answer">
                <template v-for="(block, blockIndex) in messageBlocks(msg)" :key="`${index}-${blockIndex}`">
                  <p v-if="block.type === 'paragraph'" class="assistant-answer-p">{{ block.text }}</p>
                  <ul v-else-if="block.type === 'list'" class="assistant-answer-list">
                    <li v-for="(item, itemIndex) in block.items" :key="`${index}-${blockIndex}-${itemIndex}`">{{ item }}</li>
                  </ul>
                  <div v-else-if="block.type === 'source'" class="assistant-answer-source">
                    数据来源：{{ block.text }}
                  </div>
                </template>
                <div
                  v-if="msg.toolCalls?.length && !hasSourceBlock(messageBlocks(msg))"
                  class="assistant-answer-source"
                >
                  数据来源：{{ msg.toolCalls.map((tool) => tool.name).join('、') }}
                </div>
              </div>
            </template>
            <template v-else>{{ msg.content }}</template>
          </div>
        </div>
        <div v-if="error" class="assistant-error">{{ error }}</div>
      </div>

      <form class="assistant-compose" @submit.prevent="sendMessage">
        <textarea
          v-model="draft"
          class="assistant-input"
          rows="2"
          placeholder="问一句，比如：帮我查 SN100 的 FA 情况"
          :disabled="loading"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <button class="assistant-send" type="submit" :disabled="loading || !draft.trim()" title="Send" aria-label="Send">
          <LoadingOutlined v-if="loading" />
          <SendOutlined v-else />
        </button>
      </form>
    </aside>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  CloseOutlined,
  DeleteOutlined,
  LoadingOutlined,
  RobotOutlined,
  SendOutlined,
} from '@ant-design/icons-vue'
import { formatAssistantContent, hasSourceBlock } from './assistantMessageFormat'
import { requestJson } from '@/composables/useApi'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const store = useAppStore()

const open = ref(false)
const draft = ref('')
const loading = ref(false)
const error = ref('')
const messages = ref([])
const sessionId = ref('')
const expiresAt = ref('')
const lastToolCalls = ref([])
const messagesEl = ref(null)

const expiryLabel = computed(() => {
  if (!expiresAt.value) return ''
  const date = new Date(expiresAt.value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
})

function pageContext() {
  return {
    route: route.name || '',
    path: route.path,
    fullPath: route.fullPath,
    query: { ...route.query },
    params: { ...route.params },
    report_date: store.reportDate || '',
    active_report: store.activeReport || null,
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

async function sendMessage() {
  const text = draft.value.trim()
  if (!text || loading.value) return

  draft.value = ''
  error.value = ''
  loading.value = true
  messages.value.push({ role: 'user', content: text })
  await scrollToBottom()

  try {
    const payload = await requestJson('/api/assistant/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        session_id: sessionId.value || null,
        page_context: pageContext(),
      }),
    })
    sessionId.value = payload.session_id || ''
    expiresAt.value = payload.expires_at || ''
    lastToolCalls.value = payload.tool_calls || []
    const answer = payload.answer || '没有生成可用回答。'
    messages.value.push({
      role: 'assistant',
      content: answer,
      blocks: formatAssistantContent(answer),
      toolCalls: payload.tool_calls || [],
    })
  } catch (e) {
    error.value = e.message || 'Assistant failed'
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function clearChat() {
  messages.value = []
  sessionId.value = ''
  expiresAt.value = ''
  lastToolCalls.value = []
  error.value = ''
}

function messageBlocks(msg) {
  if (msg.blocks) return msg.blocks
  return formatAssistantContent(msg.content)
}
</script>

<style scoped>
.assistant-root {
  position: fixed;
  right: 24px;
  top: 50%;
  z-index: 120;
  transform: translateY(-50%);
}

.assistant-fab {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--accent-steel);
  border: 1px solid color-mix(in srgb, var(--accent-steel) 70%, #fff);
  border-radius: 50%;
  box-shadow: var(--shadow-modal);
  cursor: pointer;
  transition: transform var(--duration-fast), box-shadow var(--duration-fast);
}

.assistant-fab:hover {
  transform: translateY(-2px);
}

.assistant-panel {
  width: min(520px, calc(100vw - 32px));
  height: min(680px, calc(100vh - 96px));
  display: grid;
  grid-template-rows: auto 1fr auto;
  overflow: hidden;
  background: var(--bg-card);
  color: var(--text-primary);
  border: 1px solid var(--border-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-modal);
}

.assistant-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px 14px;
  border-bottom: 1px solid var(--border-light);
}

.assistant-title {
  font-size: 15px;
  font-weight: 700;
}

.assistant-expiry {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
}

.assistant-header-actions {
  display: inline-flex;
  gap: 6px;
}

.assistant-icon-btn,
.assistant-send {
  display: grid;
  place-items: center;
  border: 1px solid var(--border-light);
  border-radius: 50%;
  background: var(--bg-tag);
  color: var(--text-secondary);
  cursor: pointer;
}

.assistant-icon-btn {
  width: 32px;
  height: 32px;
}

.assistant-icon-btn:hover,
.assistant-send:hover:not(:disabled) {
  color: #fff;
  background: var(--accent-steel);
  border-color: var(--accent-steel);
}

.assistant-messages {
  min-height: 0;
  overflow-y: auto;
  padding: 16px 18px;
  scrollbar-gutter: stable;
}

.assistant-empty {
  padding: 28px 18px;
  color: var(--text-muted);
  text-align: center;
  font-size: 13px;
}

.assistant-message {
  display: flex;
  margin-bottom: 12px;
}

.assistant-message--user {
  justify-content: flex-end;
}

.assistant-message--assistant {
  justify-content: flex-start;
}

.assistant-bubble {
  max-width: 90%;
  padding: 10px 12px;
  border-radius: 8px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.48;
  font-size: 13px;
}

.assistant-message--user .assistant-bubble {
  max-width: 78%;
}

.assistant-message--user .assistant-bubble {
  color: #fff;
  background: var(--accent-steel);
}

.assistant-message--assistant .assistant-bubble {
  width: min(100%, 430px);
  color: var(--text-primary);
  background: var(--bg-row-stripe);
  border: 1px solid var(--border-light);
}

.assistant-answer {
  display: grid;
  gap: 8px;
  white-space: normal;
}

.assistant-answer-p {
  margin: 0;
}

.assistant-answer-list {
  display: grid;
  gap: 5px;
  margin: 0;
  padding-left: 17px;
}

.assistant-answer-list li {
  padding-left: 2px;
}

.assistant-answer-source {
  margin-top: 2px;
  padding-top: 8px;
  color: var(--text-muted);
  border-top: 1px solid var(--border-light);
  font-size: 11px;
  line-height: 1.35;
}

.assistant-error {
  padding: 9px 11px;
  color: var(--color-danger);
  background: var(--color-danger-bg);
  border: 1px solid color-mix(in srgb, var(--color-danger) 25%, transparent);
  border-radius: var(--radius-md);
  font-size: 13px;
}

.assistant-compose {
  display: grid;
  grid-template-columns: 1fr 52px;
  gap: 8px;
  padding: 12px 18px 16px;
  border-top: 1px solid var(--border-light);
}

.assistant-input {
  min-width: 0;
  min-height: 64px;
  max-height: 96px;
  resize: none;
  padding: 10px 12px;
  color: var(--text-primary);
  background: var(--bg-input);
  border: 1px solid var(--border-input);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 13px;
  line-height: 1.45;
}

.assistant-input:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--border-focus) 14%, transparent);
}

.assistant-send {
  width: 52px;
  height: auto;
  min-height: 64px;
  align-self: stretch;
  border-radius: var(--radius-md);
  font-size: 17px;
}

.assistant-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .assistant-root {
    right: 12px;
  }

  .assistant-panel {
    width: calc(100vw - 24px);
    height: min(620px, calc(100vh - 80px));
  }

  .assistant-message--assistant .assistant-bubble,
  .assistant-message--user .assistant-bubble {
    max-width: 94%;
  }
}
</style>
