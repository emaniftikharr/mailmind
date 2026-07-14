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

export const SUMMARY_WORD_THRESHOLD = 300

export function countWords(text: string): number {
  return text.trim() === '' ? 0 : text.trim().split(/\s+/).length
}

export interface SummarizeResponse {
  bullets: string[]
  word_count: number
  was_summarized: boolean
}

export const summarizeEmail = (text: string) =>
  post<SummarizeResponse>('/api/v1/summarize', { text })

export type PriorityLevel = 'urgent' | 'high' | 'normal' | 'low'

export interface ClassifyResponse {
  category: string
  priority: PriorityLevel
  confidence: number
  reason: string
  all_categories: string[]
  all_priorities: string[]
}

export const classifyEmail = (subject: string, body: string) =>
  post<ClassifyResponse>('/api/v1/classify', { subject, body })

export interface TrustHit {
  category: string
  matched_text: string
}

export type RiskLevel = 'low' | 'moderate' | 'high' | 'critical'

export interface TrustResponse {
  trust_score: number
  risk_level: RiskLevel
  urgency_hits: TrustHit[]
  urgency_categories: string[]
  credential_hits: TrustHit[]
  credential_categories: string[]
  link_flags: string[]
  score_breakdown: Record<string, number>
  summary: string
}

export const checkTrust = (subject: string, body: string) =>
  post<TrustResponse>('/api/v1/trust', { subject, body })

export interface DeadlineModel {
  phrase: string
  resolved_date: string | null
  confidence: 'high' | 'medium' | 'low'
  is_relative: boolean
  urgency: 'today' | 'tomorrow' | 'this_week' | 'next_week' | 'this_month' | 'future' | 'asap' | 'overdue'
}

export interface MeetingModel {
  meeting_detected: boolean
  title: string
  date_str: string
  time_str: string
  duration_minutes: number | null
  location: string
  organizer: string
  attendees: string[]
  agenda: string
  is_tentative: boolean
  extraction_error: string | null
}

export interface TaskModel {
  title: string
  description: string
  assignee: 'me' | 'them' | 'other'
  due_date_str: string
  priority: 'urgent' | 'high' | 'normal' | 'low'
}

export interface ActionResponse {
  meeting: MeetingModel
  deadlines: DeadlineModel[]
  tasks: TaskModel[]
  has_meeting: boolean
  has_deadlines: boolean
  has_tasks: boolean
}

export const extractActions = (subject: string, body: string, sender = '') =>
  post<ActionResponse>('/api/v1/actions', { subject, body, sender })

export interface ReplyVariant {
  label: string
  tone: 'formal' | 'friendly' | 'direct'
  text: string
}

export interface ReplyResponse {
  variants: ReplyVariant[]
  count: number
  reply_needed: boolean
}

export const generateReplies = (
  subject: string,
  body: string,
  sender = '',
  category = '',
  priority = 'normal',
) =>
  post<ReplyResponse>('/api/v1/replies', { subject, body, sender, category, priority })

export type PhishingVerdict = 'phishing' | 'suspicious' | 'legitimate'

export interface PhishingResponse {
  verdict: PhishingVerdict
  risk_score: number
  indicators: string[]
  explanation: string
  safe_to_open: boolean
}

export const detectPhishing = (subject: string, body: string, sender = '') =>
  post<PhishingResponse>('/api/v1/phishing', { subject, body, sender })

export interface LinkInfo {
  url: string
  display_text: string
  domain: string
  display_domain: string
  is_shortened: boolean
  risk_flags: string[]
}

export interface LinkAnalysisResponse {
  links: LinkInfo[]
  total: number
  flagged: number
  risk_flags: string[]
}

export const analyzeLinks = (body: string, subject = '', is_html = false) =>
  post<LinkAnalysisResponse>('/api/v1/links', { body, subject, is_html })

// ── Pipeline ────────────────────────────────────────────────────────────────

export interface PipelineRequest {
  subject?: string
  body: string
  sender?: string
  is_html?: boolean
}

export interface PipelineResponse {
  classification: ClassifyResponse
  phishing: PhishingResponse
  trust: TrustResponse
  links: LinkAnalysisResponse
  actions: ActionResponse
  replies: ReplyResponse
  elapsed_ms: number
}

export const runPipeline = (req: PipelineRequest) =>
  post<PipelineResponse>('/api/v1/pipeline', req)

// ── Flowchart ────────────────────────────────────────────────────────────────

export type FlowchartNodeType = 'start' | 'end' | 'step' | 'decision'
export type FlowchartType = 'sequential' | 'branching' | 'parallel'

export interface FlowchartNode {
  id: string
  label: string
  type: FlowchartNodeType
  description: string
}

/** source/target instead of from/to — maps directly to React Flow Edge */
export interface FlowchartEdge {
  source: string
  target: string
  label: string
}

export interface FlowchartResponse {
  has_flowchart: boolean
  title: string
  flowchart_type: FlowchartType | null
  nodes: FlowchartNode[]
  edges: FlowchartEdge[]
  /** Ready-to-render Mermaid flowchart definition */
  mermaid: string
}

export const detectFlowchart = (subject: string, body: string) =>
  post<FlowchartResponse>('/api/v1/flowchart', { subject, body })
