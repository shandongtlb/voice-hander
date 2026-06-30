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

interface FunAsrSentence {
  text: string
  start?: number
  end?: number
  start_ms?: number
  end_ms?: number
  spk?: number
}

interface FunAsrMessage {
  event?: string
  error?: string
  sentences?: FunAsrSentence[]
  partial?: string
  partial_start_ms?: number
  duration_ms?: number
  is_final?: boolean
}

interface AsrLogItem {
  id: string
  text: string
  status: 'pending' | 'done' | 'error'
  at: string
}

declare global {
  interface Window {
    webkitAudioContext?: typeof AudioContext
  }
}

const apiBaseUrl = ref(localStorage.getItem('apiBaseUrl') || 'http://127.0.0.1:18080')
const funasrUrl = ref(localStorage.getItem('funasrUrl') || 'ws://127.0.0.1:10095')
const asrLanguage = ref(localStorage.getItem('asrLanguage') || '中文')
const hotwords = ref(localStorage.getItem('hotwords') || '')
const autoSend = ref(localStorage.getItem('autoSend') === 'true')
const autoSendSilenceSeconds = ref(Number(localStorage.getItem('autoSendSilenceSeconds') || '2'))

const api = computed(() => new ApiClient(apiBaseUrl.value.replace(/\/$/, '')))
const online = ref(false)
const checking = ref(false)
const statusText = ref('未连接')
const sessionId = ref('')
const draft = ref('')
const recording = ref(false)
const funasrConnected = ref(false)
const sending = ref(false)
const lastError = ref('')
const inputLevel = ref(0)
const audioBytesSent = ref(0)
const liveSentences = ref<FunAsrSentence[]>([])
const partialText = ref('')
const partialStartMs = ref(0)
const asrLog = ref<AsrLogItem[]>([])
const messages = ref<Message[]>([])
const chatLog = ref<HTMLElement | null>(null)

let stream: MediaStream | null = null
let socket: WebSocket | null = null
let audioContext: AudioContext | null = null
let sourceNode: MediaStreamAudioSourceNode | null = null
let processor: ScriptProcessorNode | null = null
let muteGain: GainNode | null = null
let silenceTimer = 0
let socketCloseTimer = 0
let stopping = false

const canSend = computed(() => draft.value.trim().length > 0 && !sending.value)
const silenceMs = computed(() => Math.max(1, autoSendSilenceSeconds.value) * 1000)
const inputLevelPercent = computed(() => Math.min(100, Math.round(inputLevel.value * 360)))
const transcriptText = computed(() => combineTranscript(liveSentences.value, partialText.value))
const recordHint = computed(() => {
  if (!recording.value) {
    return '官方 START / PCM16 / STOP 实时协议'
  }
  if (partialText.value || transcriptText.value) {
    return 'FunASR 正在返回文字'
  }
  if (audioBytesSent.value > 0) {
    return '正在发送麦克风音频'
  }
  return '等待麦克风输入'
})

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
    statusText.value = recording.value ? '正在实时转写' : '后端已连接'
  } catch (error) {
    online.value = false
    statusText.value = recording.value ? '正在实时转写' : '后端未连接'
    lastError.value = errorMessage(error)
  } finally {
    checking.value = false
  }
}

async function startRecording() {
  if (recording.value) {
    return
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    lastError.value = '当前浏览器不支持麦克风录音'
    return
  }

  lastError.value = ''
  stopping = false
  audioBytesSent.value = 0
  inputLevel.value = 0
  liveSentences.value = []
  partialText.value = ''
  partialStartMs.value = 0
  asrLog.value = []
  statusText.value = '连接 FunASR 实时服务...'

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    })
    await openFunAsrSocket()
    await setupPcmStreaming(stream)
    recording.value = true
    statusText.value = '正在实时转写'
    addAsrLog('已开始发送 16k PCM 音频', 'pending')
  } catch (error) {
    lastError.value = errorMessage(error)
    addAsrLog(lastError.value, 'error')
    cleanupAudio()
    closeSocket()
    recording.value = false
    funasrConnected.value = false
    statusText.value = online.value ? '后端已连接' : '后端未连接'
  }
}

function stopRecording() {
  window.clearTimeout(silenceTimer)
  if (!recording.value && !funasrConnected.value) {
    cleanupAudio()
    return
  }

  stopping = true
  recording.value = false
  cleanupAudio()

  if (socket?.readyState === WebSocket.OPEN) {
    try {
      socket.send('STOP')
      addAsrLog('已发送 STOP，等待最终结果', 'pending')
    } catch (error) {
      lastError.value = errorMessage(error)
    }
    window.clearTimeout(socketCloseTimer)
    socketCloseTimer = window.setTimeout(() => closeSocket(), 1800)
  } else {
    closeSocket()
  }
  statusText.value = online.value ? '后端已连接' : '后端未连接'
}

function openFunAsrSocket() {
  return new Promise<void>((resolve, reject) => {
    const url = funasrUrl.value.trim()
    if (!url) {
      reject(new Error('请填写 FunASR 实时地址'))
      return
    }

    let opened = false
    socket = new WebSocket(url)
    socket.binaryType = 'arraybuffer'

    socket.onopen = () => {
      opened = true
      funasrConnected.value = true
      socket?.send('START')
      const language = asrLanguage.value.trim()
      if (language) {
        socket?.send(`LANGUAGE:${language}`)
      }
      const words = normalizeHotwords(hotwords.value)
      if (words) {
        socket?.send(`HOTWORDS:${words}`)
      }
      addAsrLog('FunASR WebSocket 已连接', 'done')
      resolve()
    }

    socket.onmessage = (event) => {
      handleFunAsrMessage(event.data)
    }

    socket.onerror = () => {
      const message = `FunASR WebSocket 连接失败：${url}`
      lastError.value = message
      addAsrLog(message, 'error')
      if (!opened) {
        reject(new Error(message))
      }
    }

    socket.onclose = () => {
      funasrConnected.value = false
      if (recording.value && !stopping) {
        lastError.value = 'FunASR 实时连接已关闭'
        addAsrLog(lastError.value, 'error')
        stopRecording()
      }
    }
  })
}

async function setupPcmStreaming(mediaStream: MediaStream) {
  const AudioContextCtor = window.AudioContext || window.webkitAudioContext
  if (!AudioContextCtor) {
    throw new Error('当前浏览器不支持 Web Audio')
  }
  audioContext = new AudioContextCtor({ sampleRate: 16000 })
  sourceNode = audioContext.createMediaStreamSource(mediaStream)
  processor = audioContext.createScriptProcessor(4096, 1, 1)
  muteGain = audioContext.createGain()
  muteGain.gain.value = 0

  processor.onaudioprocess = (event) => {
    if (!recording.value || socket?.readyState !== WebSocket.OPEN || !audioContext) {
      return
    }
    const input = event.inputBuffer.getChannelData(0)
    inputLevel.value = rms(input)
    const samples = downsample(input, audioContext.sampleRate, 16000)
    const pcm = floatTo16BitPcm(samples)
    socket.send(pcm.buffer)
    audioBytesSent.value += pcm.byteLength
  }

  sourceNode.connect(processor)
  processor.connect(muteGain)
  muteGain.connect(audioContext.destination)
}

function cleanupAudio() {
  processor?.disconnect()
  sourceNode?.disconnect()
  muteGain?.disconnect()
  processor = null
  sourceNode = null
  muteGain = null
  if (audioContext && audioContext.state !== 'closed') {
    void audioContext.close()
  }
  audioContext = null
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
  inputLevel.value = 0
}

function closeSocket() {
  window.clearTimeout(socketCloseTimer)
  if (socket && socket.readyState !== WebSocket.CLOSED) {
    socket.close()
  }
  socket = null
  funasrConnected.value = false
}

function handleFunAsrMessage(raw: unknown) {
  if (typeof raw !== 'string') {
    return
  }

  let data: FunAsrMessage
  try {
    data = JSON.parse(raw) as FunAsrMessage
  } catch {
    addAsrLog(raw, 'done')
    return
  }

  if (data.error) {
    lastError.value = data.error
    addAsrLog(data.error, 'error')
    return
  }

  if (data.event) {
    if (data.event === 'started') {
      addAsrLog('FunASR 会话已启动', 'done')
    } else if (data.event === 'stopped') {
      addAsrLog('FunASR 会话已停止', 'done')
      scheduleAutoSend()
      closeSocket()
    } else {
      addAsrLog(`FunASR: ${data.event}`, 'done')
    }
  }

  if (Array.isArray(data.sentences) || typeof data.partial === 'string') {
    liveSentences.value = data.sentences || []
    partialText.value = data.is_final ? '' : data.partial || ''
    partialStartMs.value = data.partial_start_ms ?? partialStartMs.value
    const text = combineTranscript(liveSentences.value, partialText.value)
    if (text) {
      draft.value = text
      scheduleAutoSend()
    }
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
  if (!autoSend.value || recording.value || !draft.value.trim()) {
    return
  }
  silenceTimer = window.setTimeout(() => {
    void sendDraft()
  }, silenceMs.value)
}

function resetSession() {
  stopRecording()
  sessionId.value = ''
  messages.value = []
  liveSentences.value = []
  partialText.value = ''
  partialStartMs.value = 0
  asrLog.value = []
  draft.value = ''
  lastError.value = ''
  window.clearTimeout(silenceTimer)
}

function saveSettings() {
  localStorage.setItem('apiBaseUrl', apiBaseUrl.value)
  localStorage.setItem('funasrUrl', funasrUrl.value)
  localStorage.setItem('asrLanguage', asrLanguage.value)
  localStorage.setItem('hotwords', hotwords.value)
  localStorage.setItem('autoSend', String(autoSend.value))
  localStorage.setItem('autoSendSilenceSeconds', String(autoSendSilenceSeconds.value))
  void checkHealth()
}

function addAsrLog(text: string, status: AsrLogItem['status']) {
  asrLog.value.unshift({
    id: crypto.randomUUID(),
    text,
    status,
    at: nowTime(),
  })
  asrLog.value = asrLog.value.slice(0, 8)
}

function sentenceStart(sentence: FunAsrSentence) {
  return sentence.start ?? sentence.start_ms ?? 0
}

function sentenceEnd(sentence: FunAsrSentence) {
  return sentence.end ?? sentence.end_ms ?? 0
}

function formatSeconds(ms: number) {
  return `${(ms / 1000).toFixed(1)}s`
}

function combineTranscript(sentences: FunAsrSentence[], partial: string) {
  const parts = sentences.map((sentence) => sentence.text.trim()).filter(Boolean)
  const pending = partial.trim()
  if (pending) {
    parts.push(pending)
  }
  return parts.join('\n')
}

function normalizeHotwords(value: string) {
  return value
    .split(/[\n,，]/)
    .map((word) => word.trim())
    .filter(Boolean)
    .join(',')
}

function rms(input: Float32Array) {
  if (!input.length) {
    return 0
  }
  let sum = 0
  for (const sample of input) {
    sum += sample * sample
  }
  return Math.sqrt(sum / input.length)
}

function downsample(input: Float32Array, inputRate: number, outputRate: number) {
  if (inputRate === outputRate || inputRate < outputRate) {
    return input
  }
  const ratio = inputRate / outputRate
  const outputLength = Math.floor(input.length / ratio)
  const output = new Float32Array(outputLength)
  let inputOffset = 0

  for (let outputOffset = 0; outputOffset < outputLength; outputOffset += 1) {
    const nextInputOffset = Math.round((outputOffset + 1) * ratio)
    let sum = 0
    let count = 0
    for (let i = inputOffset; i < nextInputOffset && i < input.length; i += 1) {
      sum += input[i]
      count += 1
    }
    output[outputOffset] = count ? sum / count : 0
    inputOffset = nextInputOffset
  }
  return output
}

function floatTo16BitPcm(input: Float32Array) {
  const output = new Int16Array(input.length)
  for (let i = 0; i < input.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, input[i]))
    output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
  }
  return output
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
        <p>浏览器直连 FunASR 实时 WebSocket，转写后交给本地 chat 中枢处理。</p>
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
          <span>{{ recording ? '实时中' : '待机' }}</span>
        </div>

        <div class="record-zone" :class="{ active: recording }">
          <button v-if="!recording" class="record-button" type="button" @click="startRecording" title="开始实时转写">
            <Mic :size="28" />
          </button>
          <button v-else class="record-button stop" type="button" @click="stopRecording" title="停止实时转写">
            <CircleStop :size="28" />
          </button>
          <div class="record-meta">
            <strong>{{ recording ? '正在实时转写' : '点击开始说话' }}</strong>
            <span>{{ recordHint }}</span>
            <div class="level-meter" aria-hidden="true">
              <span :style="{ width: `${inputLevelPercent}%` }"></span>
            </div>
          </div>
        </div>

        <label class="field">
          <span>后端地址</span>
          <input v-model="apiBaseUrl" type="text" @change="saveSettings" />
        </label>

        <label class="field">
          <span>FunASR 实时地址</span>
          <input v-model="funasrUrl" type="text" @change="saveSettings" />
        </label>

        <div class="field-grid">
          <label class="field">
            <span>识别语言</span>
            <input v-model="asrLanguage" type="text" placeholder="中文" @change="saveSettings" />
          </label>
          <label class="field">
            <span>停止后提交</span>
            <input
              v-model.number="autoSendSilenceSeconds"
              type="number"
              min="1"
              max="20"
              @change="saveSettings"
            />
          </label>
        </div>

        <label class="field">
          <span>热词</span>
          <textarea v-model="hotwords" class="hotword-box" placeholder="人名、地名或术语，可换行" @change="saveSettings" />
        </label>

        <label class="switch-row">
          <input v-model="autoSend" type="checkbox" @change="saveSettings" />
          <span>停止转写后自动提交给 chat</span>
        </label>

        <div class="panel-heading compact">
          <h2>实时结果</h2>
          <Loader2 v-if="recording || funasrConnected" :size="16" class="spin" />
        </div>
        <div class="live-list">
          <div
            v-for="(sentence, index) in liveSentences"
            :key="`${sentenceStart(sentence)}-${index}`"
            class="live-line"
          >
            <span>{{ formatSeconds(sentenceStart(sentence)) }} - {{ formatSeconds(sentenceEnd(sentence)) }}</span>
            <p>{{ sentence.text }}</p>
          </div>
          <div v-if="partialText" class="live-line live-partial">
            <span>{{ formatSeconds(partialStartMs) }} ...</span>
            <p>{{ partialText }}</p>
          </div>
          <div v-if="!liveSentences.length && !partialText" class="empty">
            {{ recording ? '正在等待 FunASR 返回文字' : '还没有实时转写结果' }}
          </div>
        </div>

        <div class="asr-log">
          <div v-for="item in asrLog" :key="item.id" class="log-item" :class="item.status">
            <span>{{ item.at }}</span>
            <p>{{ item.text }}</p>
          </div>
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
            开始实时转写后，文字会进入下方草稿区；确认无误后发送给 chat。
          </div>
        </div>

        <div class="composer">
          <textarea v-model="draft" placeholder="实时转写文字会累积在这里，也可以手动输入..." />
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
