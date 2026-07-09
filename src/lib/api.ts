const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export const SUPPORTED_LANGUAGES = ['Spanish', 'French', 'German', 'Portuguese', 'Japanese'] as const
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]

export interface AnalyzeRequest {
  email_id: string
  subject: string
  body: string
  sender?: string
}

export interface AnalyzeResponse {
  email_id: string
  summary: string
  action_items: string[]
  quick_replies: string[]
  sentiment: 'positive' | 'neutral' | 'negative'
  tone: 'formal' | 'informal' | 'urgent' | 'friendly'
  grammar_issues: string[]
}

export interface TranslateResponse {
  translated_text: string
  source_language: string
  target_language: string
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const analyzeEmail = (req: AnalyzeRequest) =>
  post<AnalyzeResponse>('/api/v1/analyze', req)

export const translateText = (text: string, targetLanguage: SupportedLanguage) =>
  post<TranslateResponse>('/api/v1/translate', { text, target_language: targetLanguage })

export interface Correction {
  original: string
  corrected: string
  explanation: string
}

export interface GrammarResponse {
  corrected_text: string
  corrections: Correction[]
}

export const checkGrammar = (text: string) =>
  post<GrammarResponse>('/api/v1/grammar', { text })

export type ToneVariant = 'formal' | 'friendly' | 'concise' | 'persuasive' | 'executive' | 'professional'

export interface ToneRewriteResponse {
  rewritten: string
  tone: string
  changes_summary: string
  truncated: boolean
}

export const rewriteTone = (text: string, tone: ToneVariant) =>
  post<ToneRewriteResponse>('/api/v1/rewrite-tone', { text, tone })
