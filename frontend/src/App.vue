<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  CircleStop,
  Loader2,
  Mic,
  RotateCcw,
  Send,
  Settings,
  Wifi,
  WifiOff,
} from 'lucide-vue-next'
import { ApiClient } from './api'

type Role = 'user' | 'assistant' | 'system'

interface Message {
  id: string
  role: Role
  content: string
  at: string
}

interface TranscriptSegment {
  id: string
  text: string
  status: 'pending' | 'done' | 'error'
  at: string
}

const apiBaseUrl = ref(localStorage.getItem('apiBaseUrl') || 'http://127.0.0.1:18080')
const chunkSeconds = ref(Number(localStorage.getItem('chunkSeconds') || '4'))
const autoSend = ref(localStorage.getItem('autoSend') === 'true')
const autoSendSilenceSeconds = ref(Number(localStorage.getItem('autoSendSilenceSeconds') || '2'))

const api = computed(() => new ApiClient(apiBaseUrl.value.replace(/\/$/, '')))
const online = ref(false)
const checking = ref(false)
const statusText = ref('未连接')
const sessionId = ref('')
const draft = ref('')
const recording = ref(false)
const transcribing = ref(false)
const sending = ref(false)
const lastError = ref('')
const messages = ref<Message[]>([])
const segments = ref<TranscriptSegment[]>([])
const chatLog = ref<HTMLElement | null>(null)

let stream: MediaStream | null = null
let recorder: MediaRecorder | null = null
let silenceTimer = 0

const canSend = computed(() => draft.value.trim().length > 0 && !sending.value)
const chunkMs = computed(() => Math.max(1, chunkSeconds.value) * 1000)
const silenceMs = computed(() => Math.max(1, autoSendSilenceSeconds.value) * 1000)

onMounted(() => {
  void checkHealth()
})

onBeforeUnmount(() => {
  stopRecording()
})

async function checkHealth() {
  checking.value = true
  lastError.value = ''
  try {
    await api.value.health()
    online.value = true
    statusText.value = '后端已连接'
  } catch (error) {
    online.value = false
    statusText.value = '后端未连接'
    lastError.value = errorMessage(error)
  } finally {
    checking.value = false
  }
}

async function startRecording() {
  lastError.value = ''
  if (!navigator.mediaDevices?.getUserMedia) {
    lastError.value = '当前浏览器不支持麦克风录音'
    return
  }

  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mimeType = preferredMimeType()
    recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        void transcribeChunk(event.data)
      }
    }
    recorder.onerror = (event) => {
      lastError.value = `录音失败：${event.error?.message || '未知错误'}`
    }
    recorder.onstop = () => {
      stream?.getTracks().forEach((track) => track.stop())
      stream = null
      recorder = null
      recording.value = false
    }

    recorder.start(chunkMs.value)
    recording.value = true
    statusText.value = '正在监听麦克风'
  } catch (error) {
    lastError.value = errorMessage(error)
  }
}

function stopRecording() {
  window.clearTimeout(silenceTimer)
  if (recorder && recorder.state !== 'inactive') {
    recorder.stop()
  }
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
  recorder = null
  recording.value = false
  statusText.value = online.value ? '后端已连接' : '未连接'
}

async function transcribeChunk(blob: Blob) {
  const segment: TranscriptSegment = {
    id: crypto.randomUUID(),
    text: '转写中...',
    status: 'pending',
    at: nowTime(),
  }
  segments.value.unshift(segment)
  transcribing.value = true

  try {
    const result = await api.value.transcribe(blob, `speech-${Date.now()}.${audioExtension(blob.type)}`)
    const text = result.transcript.trim()
    segment.text = text || '空片段'
    segment.status = 'done'
    if (text) {
      draft.value = joinDraft(draft.value, text)
      scheduleAutoSend()
    }
  } catch (error) {
    segment.text = errorMessage(error)
    segment.status = 'error'
    lastError.value = segment.text
  } finally {
    transcribing.value = false
  }
}

async function sendDraft() {
  const text = draft.value.trim()
  if (!text || sending.value) {
    return
  }

  sending.value = true
  lastError.value = ''
  messages.value.push({
    id: crypto.randomUUID(),
    role: 'user',
    content: text,
    at: nowTime(),
  })
  draft.value = ''
  window.clearTimeout(silenceTimer)
  await scrollChat()

  try {
    const result = await api.value.chat(text, sessionId.value || undefined)
    sessionId.value = result.session_id
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'assistant',
      content: result.reply,
      at: nowTime(),
    })
    await scrollChat()
  } catch (error) {
    lastError.value = errorMessage(error)
    messages.value.push({
      id: crypto.randomUUID(),
      role: 'system',
      content: lastError.value,
      at: nowTime(),
    })
  } finally {
    sending.value = false
  }
}

function scheduleAutoSend() {
  window.clearTimeout(silenceTimer)
  if (!autoSend.value) {
    return
  }
  silenceTimer = window.setTimeout(() => {
    void sendDraft()
  }, silenceMs.value)
}

function resetSession() {
  sessionId.value = ''
  messages.value = []
  segments.value = []
  draft.value = ''
  lastError.value = ''
  window.clearTimeout(silenceTimer)
}

function saveSettings() {
  localStorage.setItem('apiBaseUrl', apiBaseUrl.value)
  localStorage.setItem('chunkSeconds', String(chunkSeconds.value))
  localStorage.setItem('autoSend', String(autoSend.value))
  localStorage.setItem('autoSendSilenceSeconds', String(autoSendSilenceSeconds.value))
  void checkHealth()
}

function preferredMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/wav']
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || ''
}

function audioExtension(mimeType: string) {
  if (mimeType.includes('mp4')) return 'm4a'
  if (mimeType.includes('wav')) return 'wav'
  return 'webm'
}

function joinDraft(current: string, next: string) {
  const trimmed = current.trim()
  return trimmed ? `${trimmed}\n${next}` : next
}

function nowTime() {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date())
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

async function scrollChat() {
  await nextTick()
  if (chatLog.value) {
    chatLog.value.scrollTop = chatLog.value.scrollHeight
  }
}
</script>

<template>
  <main class="app-shell">
    <section class="topbar">
      <div>
        <h1>内网语音助手</h1>
        <p>实时转写到文本，再交给本地 chat 中枢处理。</p>
      </div>
      <div class="connection" :class="{ online }">
        <Wifi v-if="online" :size="18" />
        <WifiOff v-else :size="18" />
        <span>{{ statusText }}</span>
        <button class="icon-button" type="button" @click="checkHealth" title="检查后端">
          <Loader2 v-if="checking" :size="18" class="spin" />
          <RotateCcw v-else :size="18" />
        </button>
      </div>
    </section>

    <section class="workspace">
      <aside class="panel control-panel">
        <div class="panel-heading">
          <h2>语音输入</h2>
          <span>{{ recording ? '监听中' : '待机' }}</span>
        </div>

        <div class="record-zone" :class="{ active: recording }">
          <button v-if="!recording" class="record-button" type="button" @click="startRecording" title="开始录音">
            <Mic :size="28" />
          </button>
          <button v-else class="record-button stop" type="button" @click="stopRecording" title="停止录音">
            <CircleStop :size="28" />
          </button>
          <div class="record-meta">
            <strong>{{ recording ? '正在分片转写' : '点击开始说话' }}</strong>
            <span>{{ transcribing ? 'ASR 正在处理片段' : `${chunkSeconds} 秒一个片段` }}</span>
          </div>
        </div>

        <label class="field">
          <span>后端地址</span>
          <input v-model="apiBaseUrl" type="text" @change="saveSettings" />
        </label>

        <div class="field-grid">
          <label class="field">
            <span>分片秒数</span>
            <input v-model.number="chunkSeconds" type="number" min="1" max="20" @change="saveSettings" />
          </label>
          <label class="field">
            <span>静音提交</span>
            <input
              v-model.number="autoSendSilenceSeconds"
              type="number"
              min="1"
              max="20"
              @change="saveSettings"
            />
          </label>
        </div>

        <label class="switch-row">
          <input v-model="autoSend" type="checkbox" @change="saveSettings" />
          <span>转写后自动提交给 chat</span>
        </label>

        <div class="panel-heading compact">
          <h2>片段日志</h2>
          <Loader2 v-if="transcribing" :size="16" class="spin" />
        </div>
        <div class="segment-list">
          <div v-for="segment in segments" :key="segment.id" class="segment" :class="segment.status">
            <span>{{ segment.at }}</span>
            <p>{{ segment.text }}</p>
          </div>
          <div v-if="segments.length === 0" class="empty">还没有语音片段</div>
        </div>
      </aside>

      <section class="panel chat-panel">
        <div class="panel-heading">
          <div>
            <h2>会话</h2>
            <span>{{ sessionId || '新会话' }}</span>
          </div>
          <button class="secondary-button" type="button" @click="resetSession">
            <RotateCcw :size="16" />
            重置
          </button>
        </div>

        <div ref="chatLog" class="chat-log">
          <article v-for="message in messages" :key="message.id" class="message" :class="message.role">
            <div class="message-meta">
              <span>{{ message.role === 'assistant' ? '助手' : message.role === 'user' ? '你' : '系统' }}</span>
              <time>{{ message.at }}</time>
            </div>
            <p>{{ message.content }}</p>
          </article>
          <div v-if="messages.length === 0" class="empty chat-empty">
            开始录音后，转写文字会出现在下方草稿区。确认无误后发送给 chat。
          </div>
        </div>

        <div class="composer">
          <textarea v-model="draft" placeholder="转写文字会累积在这里，也可以手动输入..." />
          <div class="composer-actions">
            <span class="error-text">{{ lastError }}</span>
            <button class="secondary-button" type="button" @click="draft = ''">
              <Settings :size="16" />
              清空
            </button>
            <button class="primary-button" type="button" :disabled="!canSend" @click="sendDraft">
              <Loader2 v-if="sending" :size="18" class="spin" />
              <Send v-else :size="18" />
              发送
            </button>
          </div>
        </div>
      </section>
    </section>
  </main>
</template>
