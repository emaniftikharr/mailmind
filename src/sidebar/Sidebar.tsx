import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import {
  SUPPORTED_LANGUAGES,
  SUMMARY_WORD_THRESHOLD,
  type SupportedLanguage,
  type AnalyzeResponse,
  type GrammarResponse,
  type SummarizeResponse,
  type ToneVariant,
  type ToneRewriteResponse,
  analyzeEmail,
  countWords,
  summarizeEmail,
  translateText,
  checkGrammar,
  rewriteTone,
} from '../lib/api'
import { usePrivacyMode, type PrivacyMode } from '../lib/usePrivacyMode'
import type { EmailData } from '../content/gmail'

// ── Design tokens ─────────────────────────────────────────────────────────────
const C = {
  brand:         '#2563eb',
  brandBg:       '#eff6ff',
  brandBorder:   '#bfdbfe',
  textPrimary:   '#111827',
  textSecondary: '#374151',
  textMuted:     '#6b7280',
  textDisabled:  '#9ca3af',
  bg:            '#f8fafc',
  surface:       '#ffffff',
  border:        '#e5e7eb',
  borderFaint:   '#f3f4f6',
  success:       '#15803d',
  successBg:     '#f0fdf4',
  successBorder: '#bbf7d0',
  error:         '#dc2626',
  errorBg:       '#fef2f2',
  errorBorder:   '#fecaca',
  warn:          '#92400e',
  warnBg:        '#fffbeb',
  warnBorder:    '#fcd34d',
}

// Keyframe animations + utility classes injected once into the host page
const INJECTED_STYLES = `
@keyframes mm-shimmer {
  0%   { background-position: -200% 0 }
  100% { background-position:  200% 0 }
}
@keyframes mm-fade-in {
  from { opacity: 0; transform: translateY(4px) }
  to   { opacity: 1; transform: translateY(0)   }
}
.mm-skeleton {
  background: linear-gradient(90deg, #f0f0f0 0%, #e8e8e8 50%, #f0f0f0 100%);
  background-size: 200% 100%;
  animation: mm-shimmer 1.4s ease-in-out infinite;
  border-radius: 4px;
}
.mm-fade-in { animation: mm-fade-in .18s ease forwards; }
.mm-tab:hover { background: #1d4ed8 !important; }
.mm-close:hover { opacity: 1 !important; background: rgba(255,255,255,.15) !important; border-radius: 4px; }
`

// Sidebar width: 22% of viewport, clamped 300–400 px
const clampW = (vw: number) => Math.min(400, Math.max(300, Math.round(vw * 0.22)))

function useStyles() {
  useEffect(() => {
    const ID = 'mailmind-styles'
    if (!document.getElementById(ID)) {
      const el = document.createElement('style')
      el.id = ID
      el.textContent = INJECTED_STYLES
      document.head.appendChild(el)
    }
  }, [])
}

function useSidebarWidth() {
  const [w, setW] = useState(() => clampW(window.innerWidth))
  useEffect(() => {
    const h = () => setW(clampW(window.innerWidth))
    window.addEventListener('resize', h)
    return () => window.removeEventListener('resize', h)
  }, [])
  return w
}

// ── Types ─────────────────────────────────────────────────────────────────────
interface SidebarProps {
  emailOpen: boolean
  emailData?: EmailData | null
  onVisibilityChange?: (visible: boolean) => void
}

// ── Root component ────────────────────────────────────────────────────────────
export function Sidebar({ emailOpen, emailData, onVisibilityChange }: SidebarProps) {
  useStyles()
  const w = useSidebarWidth()
  const [privacyMode, setPrivacyMode] = usePrivacyMode()

  const [open, setOpen]                 = useState(true)
  const [analysis, setAnalysis]         = useState<AnalyzeResponse | null>(null)
  const [analyzing, setAnalyzing]       = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [summary, setSummary]           = useState<SummarizeResponse | null>(null)
  const [summarizing, setSummarizing]   = useState(false)

  // Cancel token shared by all analysis paths (auto + manual)
  const cancelRef = useRef<() => void>(() => {})

  // Shared runner – cancels any in-flight call before starting a new one
  function runAnalysis(data: EmailData) {
    cancelRef.current()
    let cancelled = false
    cancelRef.current = () => { cancelled = true }

    setAnalyzing(true); setAnalysis(null); setAnalyzeError(null)
    analyzeEmail({ email_id: data.emailId, subject: data.subject, body: data.body, sender: data.sender })
      .then(d  => { if (!cancelled) setAnalysis(d) })
      .catch(() => { if (!cancelled) setAnalyzeError('Could not analyze email. Is the backend running?') })
      .finally(() => { if (!cancelled) setAnalyzing(false) })

    // Bullet summary runs in parallel for long emails only
    setSummary(null)
    if (countWords(data.body) >= SUMMARY_WORD_THRESHOLD) {
      setSummarizing(true)
      summarizeEmail(data.body)
        .then(d  => { if (!cancelled) setSummary(d) })
        .catch(() => {})
        .finally(() => { if (!cancelled) setSummarizing(false) })
    }
  }

  // Cancel + reset when the open email changes
  useEffect(() => {
    cancelRef.current()
    setAnalysis(null); setAnalyzeError(null); setAnalyzing(false)
    setSummary(null); setSummarizing(false)
  }, [emailData?.emailId])

  // Auto-analyze in Smart mode; cleanup cancels on email change or mode leave
  useEffect(() => {
    if (!emailData || privacyMode !== 'smart') return
    runAnalysis(emailData)
    return () => { cancelRef.current() }
  }, [emailData?.emailId, privacyMode])

  // When mode switches to Off, cancel any in-flight call and clear state
  useEffect(() => {
    if (privacyMode !== 'off') return
    cancelRef.current()
    setAnalysis(null); setAnalyzeError(null); setAnalyzing(false)
    setSummary(null); setSummarizing(false)
  }, [privacyMode])

  // Manual trigger – uses the shared runner so it too can be cancelled
  function handleManualAnalyze() {
    if (!emailData || analyzing) return
    runAnalysis(emailData)
  }

  function show() { setOpen(true);  onVisibilityChange?.(true)  }
  function hide() { setOpen(false); onVisibilityChange?.(false) }

  // ── Collapsed tab ──
  if (!open) {
    return (
      <button
        className="mm-tab"
        onClick={show}
        aria-label="Open MailMind"
        style={{
          position: 'fixed', right: 0, top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 2147483647,
          width: 26, padding: '22px 0',
          background: C.brand, color: '#fff',
          border: 'none', borderRadius: '8px 0 0 8px',
          cursor: 'pointer', fontSize: 14,
          boxShadow: '-3px 0 12px rgba(37,99,235,.35)',
          transition: 'background .15s',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        ✉
      </button>
    )
  }

  // ── Sidebar ──
  return (
    <div
      style={{
        position: 'fixed', right: 0, top: 0,
        width: w, height: '100vh',
        zIndex: 2147483647,
        display: 'flex', flexDirection: 'column',
        fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
        fontSize: 13, lineHeight: 1.5,
        color: C.textPrimary,
        boxSizing: 'border-box',
        background: C.bg,
        borderLeft: `1px solid ${C.border}`,
        boxShadow: '-4px 0 24px rgba(0,0,0,.09)',
      }}
    >
      {/* ── Header ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 14px', height: 46, flexShrink: 0,
        background: C.brand,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: '#fff', fontSize: 15 }}>✉</span>
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 13, letterSpacing: '.02em' }}>
            MailMind
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <StatusPill active={emailOpen} />
          <button
            className="mm-close"
            onClick={hide}
            aria-label="Close MailMind"
            style={{
              background: 'none', border: 'none',
              color: 'rgba(255,255,255,.7)',
              fontSize: 20, cursor: 'pointer',
              lineHeight: 1, padding: '3px 5px',
              opacity: .8, transition: 'opacity .15s, background .15s',
            }}
          >
            ×
          </button>
        </div>
      </div>

      {/* ── Privacy bar ── */}
      <PrivacyBar mode={privacyMode} onChange={setPrivacyMode} />

      {/* ── Subject strip (email open only) ── */}
      {emailOpen && emailData?.subject && (
        <div style={{
          padding: '5px 14px',
          background: C.brandBg, borderBottom: `1px solid ${C.brandBorder}`,
          flexShrink: 0,
          fontSize: 11, fontWeight: 500, color: C.brand,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {emailData.subject}
        </div>
      )}

      {/* ── Scrollable body ── */}
      <div style={{
        flex: 1, overflowY: 'auto',
        padding: '12px 10px',
        display: 'flex', flexDirection: 'column', gap: 8,
        background: C.bg,
      }}>
        {privacyMode === 'off' ? (
          <PrivacyOffState />
        ) : emailOpen ? (
          <>
            {analyzeError ? (
              <ErrorBanner message={analyzeError} />
            ) : (
              <>
                <SectionLabel label="AI Analysis" />
                {privacyMode === 'manual' && !analysis && !analyzing ? (
                  <ManualAnalysisPrompt onAnalyze={handleManualAnalyze} loading={analyzing} />
                ) : (
                  <>
                    {(summarizing || summary !== null) && (
                      <SummaryPanel summary={summary} loading={summarizing} body={emailData?.body ?? ''} />
                    )}
                    <AnalysisPanels analysis={analysis} analyzing={analyzing} />
                  </>
                )}
              </>
            )}
            <SectionLabel label="Writing Tools" />
            <GrammarPanel     key={emailData?.emailId ?? ''} body={emailData?.body ?? ''} />
            <ToneRewritePanel key={emailData?.emailId ?? ''} body={emailData?.body ?? ''} />
            <TranslatePanel emailOpen body={emailData?.body ?? ''} />
          </>
        ) : (
          <>
            <EmptyState />
            <SectionLabel label="Translate" />
            <TranslatePanel emailOpen={false} body="" />
          </>
        )}
      </div>

      {/* ── Footer ── */}
      <div style={{
        padding: '5px 14px',
        borderTop: `1px solid ${C.border}`,
        background: C.surface, flexShrink: 0,
        fontSize: 10, color: C.textDisabled, textAlign: 'center',
        letterSpacing: '.04em',
      }}>
        MailMind · AI Email Assistant
      </div>
    </div>
  )
}

// ── Status pill (inside header) ───────────────────────────────────────────────
function StatusPill({ active }: { active: boolean }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      fontSize: 10, fontWeight: 500,
      padding: '2px 7px', borderRadius: 9999,
      background: active ? 'rgba(255,255,255,.18)' : 'rgba(0,0,0,.2)',
      color: active ? '#fff' : 'rgba(255,255,255,.55)',
    }}>
      <span style={{
        width: 5, height: 5, borderRadius: '50%', display: 'inline-block',
        background: active ? '#4ade80' : 'rgba(255,255,255,.3)',
      }} />
      {active ? 'Reading' : 'Idle'}
    </span>
  )
}

// ── Section divider ───────────────────────────────────────────────────────────
function SectionLabel({ label }: { label: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '2px 0' }}>
      <span style={{
        fontSize: 9, fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: '.1em',
        color: C.textMuted, whiteSpace: 'nowrap',
      }}>
        {label}
      </span>
      <div style={{ flex: 1, height: 1, background: C.border }} />
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState() {
  const features = [
    'AI Summary & Action Items',
    'Quick Reply Suggestions',
    'Grammar Correction',
    'Tone Rewrite — 6 styles',
    'Translate — 5 languages',
  ]
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      textAlign: 'center', padding: '28px 16px 16px',
    }}>
      <div style={{ fontSize: 28, marginBottom: 10, opacity: .35 }}>✉</div>
      <p style={{ fontWeight: 700, fontSize: 13, color: C.textSecondary, margin: '0 0 6px' }}>
        No email selected
      </p>
      <p style={{ fontSize: 12, color: C.textMuted, margin: '0 0 16px', lineHeight: 1.65 }}>
        Open an email in Gmail to unlock AI-powered tools.
      </p>
      <div style={{
        width: '100%', textAlign: 'left',
        background: C.surface, border: `1px solid ${C.border}`,
        borderRadius: 8, padding: '10px 12px',
        display: 'flex', flexDirection: 'column', gap: 7,
      }}>
        {features.map((f, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            fontSize: 12, color: C.textMuted,
          }}>
            <span style={{ color: C.brand, fontSize: 10 }}>✦</span>
            {f}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Error banner ──────────────────────────────────────────────────────────────
function ErrorBanner({ message }: { message: string }) {
  return (
    <div style={{
      fontSize: 12, color: C.error,
      background: C.errorBg, border: `1px solid ${C.errorBorder}`,
      borderRadius: 8, padding: '10px 12px',
    }}>
      {message}
    </div>
  )
}

// ── Bullet summary panel (long emails only) ───────────────────────────────────
function SummaryPanel({
  summary, loading, body,
}: {
  summary: SummarizeResponse | null
  loading: boolean
  body: string
}) {
  const [showFull, setShowFull] = useState(false)

  if (!loading && (!summary || !summary.was_summarized || summary.bullets.length === 0)) return null

  return (
    <Panel title="Quick Summary">
      {loading ? (
        <Skeleton lines={4} />
      ) : (
        <div className="mm-fade-in" style={{ display: 'flex', flexDirection: 'column' }}>
          {summary!.bullets.map((bullet, i) => (
            <div
              key={i}
              style={{
                display: 'flex', gap: 8, alignItems: 'flex-start',
                padding: '5px 0',
                borderBottom: i < summary!.bullets.length - 1
                  ? `1px solid ${C.borderFaint}` : 'none',
              }}
            >
              <span style={{
                color: C.brand, fontWeight: 700, fontSize: 11,
                marginTop: 2, flexShrink: 0,
              }}>•</span>
              <span style={{ fontSize: 12, color: C.textSecondary, lineHeight: 1.55 }}>
                {bullet}
              </span>
            </div>
          ))}

          <div style={{
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', marginTop: 7,
          }}>
            <span style={{ fontSize: 10, color: C.textMuted }}>
              {summary!.word_count.toLocaleString()} words
            </span>
            {body && (
              <button
                onClick={() => setShowFull(v => !v)}
                style={{
                  fontSize: 10, color: C.brand,
                  background: 'none', border: 'none',
                  padding: 0, cursor: 'pointer',
                  textDecoration: 'underline',
                }}
              >
                {showFull ? 'Hide email ↑' : 'Show full email ↓'}
              </button>
            )}
          </div>

          {showFull && body && (
            <div
              className="mm-fade-in"
              style={{
                marginTop: 8, maxHeight: 200, overflowY: 'auto',
                fontSize: 11, color: C.textMuted, lineHeight: 1.65,
                background: C.surface, border: `1px solid ${C.border}`,
                borderRadius: 6, padding: '8px 10px',
                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              }}
            >
              {body}
            </div>
          )}
        </div>
      )}
    </Panel>
  )
}

// ── Analysis panels ───────────────────────────────────────────────────────────
function AnalysisPanels({ analysis, analyzing }: { analysis: AnalyzeResponse | null; analyzing: boolean }) {
  const loading = analyzing || !analysis
  return (
    <>
      <Panel title="Summary">
        {loading
          ? <Skeleton lines={3} />
          : <p style={{ fontSize: 13, color: C.textSecondary, margin: 0, lineHeight: 1.65 }} className="mm-fade-in">
              {analysis!.summary}
            </p>}
      </Panel>

      <Panel title="Action Items">
        {loading
          ? <Skeleton lines={2} />
          : analysis!.action_items.length === 0
            ? <Placeholder>No action items found.</Placeholder>
            : (
              <ul style={{ margin: 0, paddingLeft: 16, fontSize: 13, color: C.textSecondary, lineHeight: 1.7 }} className="mm-fade-in">
                {analysis!.action_items.map((item, i) => <li key={i}>{item}</li>)}
              </ul>
            )}
      </Panel>

      <Panel title="Quick Replies">
        {loading
          ? <Skeleton lines={2} />
          : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }} className="mm-fade-in">
              {analysis!.quick_replies.map((reply, i) => (
                <QuickReplyButton key={i} text={reply} />
              ))}
            </div>
          )}
      </Panel>

      <Panel title="Signals">
        {loading
          ? <Skeleton lines={1} />
          : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }} className="mm-fade-in">
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <Chip label="Sentiment" value={analysis!.sentiment} />
                <Chip label="Tone"      value={analysis!.tone}      />
              </div>
              {analysis!.grammar_issues.length > 0 ? (
                <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: '#b45309', lineHeight: 1.65 }}>
                  {analysis!.grammar_issues.map((issue, i) => <li key={i}>{issue}</li>)}
                </ul>
              ) : (
                <span style={{ fontSize: 12, color: C.success }}>✓ No grammar issues detected.</span>
              )}
            </div>
          )}
      </Panel>
    </>
  )
}

function QuickReplyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  function handleClick() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true); setTimeout(() => setCopied(false), 1500)
    }).catch(() => undefined)
  }
  return (
    <button
      onClick={handleClick}
      title="Click to copy"
      style={{
        textAlign: 'left', fontSize: 12,
        padding: '6px 9px',
        background: copied ? C.successBg : C.brandBg,
        border: `1px solid ${copied ? C.successBorder : C.brandBorder}`,
        borderRadius: 6,
        color: copied ? C.success : '#1d4ed8',
        cursor: 'pointer',
        transition: 'all .15s',
      }}
    >
      {copied ? '✓ Copied' : text}
    </button>
  )
}

function Chip({ label, value }: { label: string; value: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 11, padding: '2px 8px', borderRadius: 9999,
      background: C.borderFaint, border: `1px solid ${C.border}`,
    }}>
      <span style={{ color: C.textMuted, fontWeight: 500 }}>{label}:</span>
      <span style={{ color: C.textSecondary, fontWeight: 600, textTransform: 'capitalize' }}>{value}</span>
    </span>
  )
}

// ── Panel card ────────────────────────────────────────────────────────────────
function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={{
      background: C.surface,
      border: `1px solid ${C.border}`,
      borderRadius: 10,
      padding: '10px 12px',
      boxShadow: '0 1px 2px rgba(0,0,0,.04)',
      boxSizing: 'border-box',
    }}>
      <p style={{
        fontSize: 10, fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: '.08em',
        color: C.textMuted, margin: '0 0 8px',
      }}>
        {title}
      </p>
      {children}
    </div>
  )
}

// ── Skeleton shimmer ──────────────────────────────────────────────────────────
function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="mm-skeleton"
          style={{ height: 11, width: i === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  )
}

// ── Placeholder text ──────────────────────────────────────────────────────────
function Placeholder({ children }: { children: ReactNode }) {
  return (
    <p style={{ fontSize: 12, color: C.textMuted, fontStyle: 'italic', margin: 0 }}>
      {children}
    </p>
  )
}

// ── Shared action button ──────────────────────────────────────────────────────
function ActionButton({
  onClick, loading, disabled, children,
}: {
  onClick: () => void
  loading: boolean
  disabled: boolean
  children: ReactNode
}) {
  const inactive = loading || disabled
  return (
    <button
      onClick={onClick}
      disabled={inactive}
      style={{
        width: '100%', fontSize: 12, fontWeight: 600,
        padding: '6px 0',
        background: inactive ? C.borderFaint : C.brand,
        color: inactive ? C.textDisabled : '#fff',
        border: 'none', borderRadius: 6,
        cursor: inactive ? 'not-allowed' : 'pointer',
        transition: 'background .15s',
        letterSpacing: '.01em',
      }}
    >
      {children}
    </button>
  )
}

// ── Suggestion comparison (Before / After + Accept / Dismiss) ─────────────────
interface SuggestionViewProps {
  original: string
  improved: string
  summary?: string
  truncated?: boolean
  accepted: boolean
  onAccept: () => void
  onDismiss: () => void
}

function SuggestionView({
  original, improved, summary, truncated, accepted, onAccept, onDismiss,
}: SuggestionViewProps) {
  const col = (bg: string, border: string): CSSProperties => ({
    fontSize: 11, lineHeight: 1.55,
    whiteSpace: 'pre-wrap', wordBreak: 'break-word',
    padding: '6px 8px', borderRadius: 6,
    border: `1px solid ${border}`, background: bg,
    maxHeight: 130, overflowY: 'auto',
    color: C.textPrimary,
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }} className="mm-fade-in">
      {truncated && (
        <div style={{
          fontSize: 11, color: C.warn,
          background: C.warnBg, border: `1px solid ${C.warnBorder}`,
          borderRadius: 6, padding: '5px 8px',
        }}>
          Email was long — only the first 2,000 characters were rewritten.
        </div>
      )}
      {summary && (
        <p style={{ fontSize: 11, color: C.textMuted, margin: 0, fontStyle: 'italic' }}>{summary}</p>
      )}

      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{
            fontSize: 9, fontWeight: 700,
            textTransform: 'uppercase', letterSpacing: '.07em',
            color: C.error, margin: '0 0 3px',
          }}>Before</p>
          <div style={col('#fff5f5', C.errorBorder)}>{original}</div>
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p style={{
            fontSize: 9, fontWeight: 700,
            textTransform: 'uppercase', letterSpacing: '.07em',
            color: C.success, margin: '0 0 3px',
          }}>After</p>
          <div style={col(C.successBg, C.successBorder)}>{improved}</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 6 }}>
        <button
          onClick={onAccept}
          style={{
            flex: 1, fontSize: 12, fontWeight: 500, padding: '5px 0',
            background: accepted ? C.successBg : '#16a34a',
            color: accepted ? C.success : '#fff',
            border: `1px solid ${accepted ? C.successBorder : '#16a34a'}`,
            borderRadius: 6, cursor: 'pointer',
            transition: 'all .15s',
          }}
        >
          {accepted ? '✓ Copied!' : '✓ Accept'}
        </button>
        <button
          onClick={onDismiss}
          style={{
            flex: 1, fontSize: 12, fontWeight: 500, padding: '5px 0',
            background: C.borderFaint, color: C.textSecondary,
            border: `1px solid ${C.border}`,
            borderRadius: 6, cursor: 'pointer',
          }}
        >
          ✕ Dismiss
        </button>
      </div>
    </div>
  )
}

// ── Grammar Fix panel ─────────────────────────────────────────────────────────
function GrammarPanel({ body }: { body: string }) {
  const [result,   setResult]   = useState<GrammarResponse | null>(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState<string | null>(null)
  const [accepted, setAccepted] = useState(false)

  async function handleCheck() {
    if (!body) return
    setLoading(true); setResult(null); setError(null)
    try   { setResult(await checkGrammar(body)) }
    catch { setError('Could not reach the server. Is the backend running?') }
    finally { setLoading(false) }
  }

  function handleAccept() {
    if (!result) return
    navigator.clipboard.writeText(result.corrected_text).then(() => {
      setAccepted(true); setTimeout(() => setAccepted(false), 2000)
    }).catch(() => undefined)
  }

  function handleDismiss() { setResult(null); setError(null); setAccepted(false) }

  return (
    <Panel title="Grammar Fix">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <ActionButton onClick={handleCheck} loading={loading} disabled={!body}>
          {loading ? 'Checking…' : 'Fix Grammar'}
        </ActionButton>

        {loading && <Skeleton lines={2} />}
        {error   && <ErrorBanner message={error} />}

        {result && result.corrections.length === 0 && (
          <p style={{ fontSize: 12, color: C.success, margin: 0 }} className="mm-fade-in">
            ✓ No issues found — the text looks good.
          </p>
        )}

        {result && result.corrections.length > 0 && (
          <div className="mm-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <SuggestionView
              original={body}
              improved={result.corrected_text}
              accepted={accepted}
              onAccept={handleAccept}
              onDismiss={handleDismiss}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {result.corrections.map((c, i) => (
                <div key={i} style={{
                  fontSize: 11,
                  background: '#fefce8', border: '1px solid #fde68a',
                  borderRadius: 6, padding: '5px 8px', lineHeight: 1.55,
                }}>
                  <span style={{ textDecoration: 'line-through', color: C.error }}>{c.original}</span>
                  {' → '}
                  <span style={{ color: C.success, fontWeight: 600 }}>{c.corrected}</span>
                  <div style={{ color: C.textMuted, marginTop: 2 }}>{c.explanation}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Panel>
  )
}

// ── Tone Rewrite panel ────────────────────────────────────────────────────────
const TONE_OPTIONS: { value: ToneVariant; label: string; description: string }[] = [
  { value: 'formal',       label: 'Formal',       description: 'Professional, no contractions, structured' },
  { value: 'friendly',     label: 'Friendly',     description: 'Warm, conversational, approachable' },
  { value: 'concise',      label: 'Concise',      description: '40–50% shorter, no filler words' },
  { value: 'persuasive',   label: 'Persuasive',   description: 'Benefit-led, compelling, clear call to action' },
  { value: 'executive',    label: 'Executive',    description: 'BLUF: key point first, bullets, one action item' },
  { value: 'professional', label: 'Professional', description: 'Full rewrite: formal, structured, grammar-clean' },
]

function ToneRewritePanel({ body }: { body: string }) {
  const [tone,     setTone]     = useState<ToneVariant>('formal')
  const [result,   setResult]   = useState<ToneRewriteResponse | null>(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState<string | null>(null)
  const [accepted, setAccepted] = useState(false)

  async function handleRewrite() {
    if (!body) return
    setLoading(true); setResult(null); setError(null)
    try   { setResult(await rewriteTone(body, tone)) }
    catch { setError('Could not reach the server. Is the backend running?') }
    finally { setLoading(false) }
  }

  function handleAccept() {
    if (!result) return
    navigator.clipboard.writeText(result.rewritten).then(() => {
      setAccepted(true); setTimeout(() => setAccepted(false), 2000)
    }).catch(() => undefined)
  }

  function handleDismiss() { setResult(null); setError(null); setAccepted(false) }

  const selectedDesc = TONE_OPTIONS.find(o => o.value === tone)!.description

  return (
    <Panel title="Tone Rewrite">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <select
          value={tone}
          onChange={e => { setTone(e.target.value as ToneVariant); setResult(null) }}
          style={{
            width: '100%', fontSize: 12, padding: '5px 8px',
            border: `1px solid ${C.border}`, borderRadius: 6,
            background: C.surface, color: C.textSecondary,
            cursor: 'pointer', outline: 'none',
          }}
        >
          {TONE_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        <p style={{ fontSize: 11, color: C.textMuted, margin: 0, lineHeight: 1.4 }}>
          {selectedDesc}
        </p>

        <ActionButton onClick={handleRewrite} loading={loading} disabled={!body}>
          {loading ? 'Rewriting…' : 'Rewrite'}
        </ActionButton>

        {loading && <Skeleton lines={3} />}
        {error   && <ErrorBanner message={error} />}

        {result && (
          <SuggestionView
            original={body}
            improved={result.rewritten}
            summary={result.changes_summary}
            truncated={result.truncated}
            accepted={accepted}
            onAccept={handleAccept}
            onDismiss={handleDismiss}
          />
        )}
      </div>
    </Panel>
  )
}

// ── Privacy bar ───────────────────────────────────────────────────────────────
const PRIVACY_MODES: { value: PrivacyMode; label: string; color: string; description: string }[] = [
  {
    value: 'off',
    label: 'Off',
    color: C.error,
    description: 'No email data is sent to AI services. All analysis and writing tools are disabled.',
  },
  {
    value: 'manual',
    label: 'Manual',
    color: '#d97706',
    description: 'Analysis only runs when you click "Analyze this email". Writing tools work on demand.',
  },
  {
    value: 'smart',
    label: 'Smart',
    color: C.success,
    description: 'Automatically analyzes each email you open. All features available.',
  },
]

function PrivacyBar({ mode, onChange }: { mode: PrivacyMode; onChange: (m: PrivacyMode) => void }) {
  const current = PRIVACY_MODES.find(m => m.value === mode)!
  return (
    <div style={{
      padding: '5px 10px 7px',
      background: '#f1f5f9', borderBottom: `1px solid ${C.border}`,
      flexShrink: 0,
      display: 'flex', flexDirection: 'column', gap: 5,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{
          fontSize: 9, fontWeight: 700,
          textTransform: 'uppercase', letterSpacing: '.1em',
          color: C.textMuted, whiteSpace: 'nowrap',
        }}>
          Privacy
        </span>
        <div style={{
          flex: 1, display: 'flex',
          background: C.border, borderRadius: 6,
          padding: 2, gap: 2,
        }}>
          {PRIVACY_MODES.map(m => {
            const active = mode === m.value
            return (
              <button
                key={m.value}
                onClick={() => onChange(m.value)}
                title={m.description}
                style={{
                  flex: 1, fontSize: 11,
                  fontWeight: active ? 600 : 400,
                  padding: '3px 0',
                  background: active ? C.surface : 'transparent',
                  color: active ? m.color : C.textDisabled,
                  border: 'none', borderRadius: 4,
                  cursor: 'pointer',
                  boxShadow: active ? '0 1px 2px rgba(0,0,0,.08)' : 'none',
                  transition: 'all .15s',
                }}
              >
                {m.label}
              </button>
            )
          })}
        </div>
      </div>
      <p style={{ margin: 0, fontSize: 10, color: C.textMuted, lineHeight: 1.4 }}>
        {current.description}
      </p>
    </div>
  )
}

// ── Privacy off state ─────────────────────────────────────────────────────────
function PrivacyOffState() {
  return (
    <div style={{
      background: '#1e293b', borderRadius: 10,
      padding: '28px 16px',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      textAlign: 'center', gap: 10,
    }}>
      <span style={{ fontSize: 28 }}>🔒</span>
      <p style={{ color: '#f8fafc', fontWeight: 700, fontSize: 13, margin: 0 }}>
        Privacy mode active
      </p>
      <p style={{ color: '#94a3b8', fontSize: 12, margin: 0, lineHeight: 1.65 }}>
        No email data is sent to AI services. Switch to Manual or Smart to enable analysis and writing tools.
      </p>
    </div>
  )
}

// ── Manual analysis prompt ────────────────────────────────────────────────────
function ManualAnalysisPrompt({ onAnalyze, loading }: { onAnalyze: () => void; loading: boolean }) {
  return (
    <Panel title="Analysis">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <Placeholder>Email not yet analyzed — analysis only runs when you choose.</Placeholder>
        <ActionButton onClick={onAnalyze} loading={loading} disabled={loading}>
          {loading ? 'Analyzing…' : 'Analyze this email'}
        </ActionButton>
        {loading && <Skeleton lines={3} />}
      </div>
    </Panel>
  )
}

// ── Translate panel ───────────────────────────────────────────────────────────
function TranslatePanel({ emailOpen, body }: { emailOpen: boolean; body: string }) {
  const [language, setLanguage] = useState<SupportedLanguage>('Spanish')
  const [result,   setResult]   = useState<string | null>(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState<string | null>(null)

  useEffect(() => { setResult(null); setError(null) }, [body])

  const canTranslate = emailOpen && Boolean(body)

  async function handleTranslate() {
    if (!canTranslate) return
    setLoading(true); setError(null); setResult(null)
    try   { setResult((await translateText(body, language)).translated_text) }
    catch { setError('Could not reach the server. Is the backend running?') }
    finally { setLoading(false) }
  }

  return (
    <Panel title="Translate">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <div style={{ display: 'flex', gap: 6 }}>
          <select
            value={language}
            onChange={e => { setLanguage(e.target.value as SupportedLanguage); setResult(null) }}
            style={{
              flex: 1, fontSize: 12, padding: '5px 8px',
              border: `1px solid ${C.border}`, borderRadius: 6,
              background: C.surface, color: C.textSecondary,
              cursor: 'pointer', outline: 'none',
            }}
          >
            {SUPPORTED_LANGUAGES.map(lang => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>

          <button
            onClick={handleTranslate}
            disabled={loading || !canTranslate}
            style={{
              fontSize: 12, fontWeight: 600,
              padding: '5px 12px',
              background: loading ? '#93c5fd' : !canTranslate ? C.borderFaint : C.brand,
              color: !canTranslate ? C.textDisabled : '#fff',
              border: 'none', borderRadius: 6,
              cursor: loading || !canTranslate ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap', transition: 'background .15s',
            }}
          >
            {loading ? '…' : 'Translate'}
          </button>
        </div>

        {!canTranslate && <Placeholder>Open an email to translate it.</Placeholder>}
        {loading && <Skeleton lines={3} />}
        {error   && <ErrorBanner message={error} />}

        {result && (
          <div
            className="mm-fade-in"
            style={{
              fontSize: 12, color: C.textSecondary, lineHeight: 1.65,
              background: C.brandBg, border: `1px solid ${C.brandBorder}`,
              borderRadius: 6, padding: '8px 10px',
            }}
          >
            {result}
          </div>
        )}
      </div>
    </Panel>
  )
}
