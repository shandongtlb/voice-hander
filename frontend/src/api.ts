export interface ChatResponse {
  session_id: string
  reply: string
  tool_results: Array<Record<string, unknown>>
}

export interface TranscribeResponse {
  transcript: string
}

export class ApiClient {
  constructor(private readonly baseUrl: string) {}

  async health(): Promise<Record<string, unknown>> {
    const response = await fetch(`${this.baseUrl}/health`)
    if (!response.ok) {
      throw new Error(await errorText(response))
    }
    return response.json()
  }

  async transcribe(blob: Blob, filename: string): Promise<TranscribeResponse> {
    const form = new FormData()
    form.append('file', blob, filename)
    const response = await fetch(`${this.baseUrl}/v1/transcribe`, {
      method: 'POST',
      body: form,
    })
    if (!response.ok) {
      throw new Error(await errorText(response))
    }
    return response.json()
  }

  async chat(message: string, sessionId?: string): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        session_id: sessionId || undefined,
      }),
    })
    if (!response.ok) {
      throw new Error(await errorText(response))
    }
    return response.json()
  }
}

async function errorText(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    const payload = await response.json()
    if (typeof payload.detail === 'string') {
      return payload.detail
    }
    return JSON.stringify(payload)
  }
  return response.text()
}
