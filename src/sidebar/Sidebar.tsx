import mermaid from 'mermaid'
import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import {
  SUPPORTED_LANGUAGES,
  SUMMARY_WORD_THRESHOLD,
  type SupportedLanguage,
  type AnalyzeResponse,
  type ClassifyResponse,
  type GrammarResponse,
  type SummarizeResponse,
  type ToneVariant,
  type ToneRewriteResponse,
  type TrustResponse,
  type RiskLevel,
  type ActionResponse,
  type TaskModel,
  type ReplyResponse,
  type FlowchartResponse,
  analyzeEmail,
  classifyEmail,
  checkTrust,
  extractActions,
  generateReplies,
  countWords,
  summarizeEmail,
  translateText,
  checkGrammar,
  rewriteTone,
  detectFlowchart,
} from '../lib/api'

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
  flowchart: { curve: 'basis', padding: 12 },
})
import { usePrivacyMode, type PrivacyMode } from '../lib/usePrivacyMode'
import type { EmailData } from '../content/gmail'
import { insertIntoCompose, type InsertResult } from '../content/compose'

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
@keyframes mm-pulse {
  0%, 100% { opacity: 1 }
  50%       { opacity: .3 }
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
.mm-urgent-pulse { animation: mm-pulse 1s ease-in-out infinite; }
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

// ── Trust banner ─────────────────────────────────────────────────────────────

const URGENCY_LABELS: Record<string, string> = {
  account_threat:   'Account-closure threat',
  security_alarm:   'Fake security alert',
  time_pressure:    'Artificial deadline',
  loss_aversion:    'Loss-aversion tactic',
  authority_threat: 'Legal/authority threat',
}

const CRED_LABELS: Record<string, string> = {
  password:     'Password request',
  pin:          'PIN/code request',
  ssn:          'SSN / national ID',
  bank_account: 'Bank account details',
  card_details: 'Card details (CVV, expiry)',
  identity:     'Identity documents',
}

const LINK_LABELS: Record<string, string> = {
  shortened_url:      'Shortened URL',
  domain_mismatch:    'Domain mismatch',
  brand_mismatch:     'Brand spoofing',
  raw_ip_address:     'Raw IP address',
  redirect_parameter: 'Open redirect',
}

const RISK_PALETTE: Record<RiskLevel, { color: string; bg: string; border: string; headerBg: string; barFill: string }> = {
  critical: { color: '#991b1b', bg: '#fef2f2', border: '#fca5a5', headerBg: '#fee2e2', barFill: '#dc2626' },
  high:     { color: '#92400e', bg: '#fffbeb', border: '#fcd34d', headerBg: '#fef3c7', barFill: '#d97706' },
  moderate: { color: '#713f12', bg: '#fefce8', border: '#fde68a', headerBg: '#fef9c3', barFill: '#ca8a04' },
  low:      { color: '#166534', bg: '#f0fdf4', border: '#bbf7d0', headerBg: '#dcfce7', barFill: '#16a34a' },
}

function TrustBanner({ trust }: { trust: TrustResponse | null }) {
  const [expanded, setExpanded] = useState(false)
  const [reported, setReported] = useState(false)

  if (!trust || trust.risk_level === 'low') return null

  const pal   = RISK_PALETTE[trust.risk_level]
  const score = trust.trust_score
  const isCriticalOrHigh = trust.risk_level === 'critical' || trust.risk_level === 'high'

  const riskLabel: Record<RiskLevel, string> = {
    critical: 'Critical Risk',
    high:     'High Risk',
    moderate: 'Moderate Risk',
    low:      'Low Risk',
  }

  const hasDetails =
    trust.urgency_categories.length > 0 ||
    trust.credential_categories.length > 0 ||
    trust.link_flags.length > 0

  function handleReport() {
    if (reported) return
    console.log('[MailMind] Phishing report submitted (placeholder)', trust)
    setReported(true)
    setTimeout(() => setReported(false), 3000)
  }

  return (
    <div
      className="mm-fade-in"
      style={{
        background: pal.bg,
        border: `1px solid ${pal.border}`,
        borderRadius: 10,
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0,0,0,.07)',
      }}
    >
      {/* ── Header ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 12px',
        background: pal.headerBg,
        borderBottom: `1px solid ${pal.border}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 13 }}>⚠</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: pal.color, letterSpacing: '.02em' }}>
            {riskLabel[trust.risk_level]}
          </span>
        </div>
        {/* Score badge */}
        <span style={{
          fontSize: 11, fontWeight: 700,
          padding: '1px 7px', borderRadius: 9999,
          background: pal.barFill, color: '#fff',
        }}>
          {score}/100
        </span>
      </div>

      {/* ── Body ── */}
      <div style={{ padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 9 }}>

        {/* Trust score bar */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: 9, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.08em', color: pal.color }}>
              Trust score
            </span>
            <span style={{ fontSize: 9, color: pal.color, fontWeight: 600 }}>
              {score < 40 ? 'Very low — exercise caution' : score < 60 ? 'Low — verify before acting' : 'Moderate — double-check sender'}
            </span>
          </div>
          <div style={{
            height: 5, borderRadius: 9999,
            background: `${pal.barFill}22`,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%', borderRadius: 9999,
              width: `${score}%`,
              background: pal.barFill,
              transition: 'width .5s ease',
            }} />
          </div>
        </div>

        {/* Summary reason */}
        <p style={{
          fontSize: 11, color: pal.color, margin: 0,
          lineHeight: 1.5,
        }}>
          {trust.summary.replace(/^Trust score \d+\/100 \([^)]+\)\.\s*/, '')}
        </p>

        {/* Expandable indicators */}
        {hasDetails && (
          <div>
            <button
              onClick={() => setExpanded(v => !v)}
              style={{
                background: 'none', border: 'none', padding: 0,
                fontSize: 11, fontWeight: 600, color: pal.color,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              <span style={{
                display: 'inline-block',
                transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform .15s',
                fontSize: 9,
              }}>▶</span>
              {expanded ? 'Hide details' : 'Why flagged'}
            </button>

            {expanded && (
              <div className="mm-fade-in" style={{
                marginTop: 7,
                display: 'flex', flexDirection: 'column', gap: 6,
                paddingLeft: 2,
              }}>
                {trust.urgency_categories.length > 0 && (
                  <IndicatorGroup
                    label="Urgency tactics"
                    items={trust.urgency_categories.map(c => URGENCY_LABELS[c] ?? c)}
                    color={pal.color}
                    border={pal.border}
                  />
                )}
                {trust.credential_categories.length > 0 && (
                  <IndicatorGroup
                    label="Sensitive data requested"
                    items={trust.credential_categories.map(c => CRED_LABELS[c] ?? c)}
                    color={pal.color}
                    border={pal.border}
                  />
                )}
                {trust.link_flags.length > 0 && (
                  <IndicatorGroup
                    label="Suspicious links"
                    items={trust.link_flags.map(f => LINK_LABELS[f] ?? f)}
                    color={pal.color}
                    border={pal.border}
                  />
                )}
              </div>
            )}
          </div>
        )}

        {/* Report phishing button — only for high/critical */}
        {isCriticalOrHigh && (
          <button
            onClick={handleReport}
            disabled={reported}
            style={{
              width: '100%', fontSize: 11, fontWeight: 600,
              padding: '6px 0', borderRadius: 6,
              background: reported ? pal.headerBg : 'transparent',
              color: reported ? pal.color : pal.color,
              border: `1px solid ${pal.border}`,
              cursor: reported ? 'default' : 'pointer',
              transition: 'all .15s',
              letterSpacing: '.02em',
            }}
          >
            {reported ? '✓ Phishing reported' : '🚨 Report phishing'}
          </button>
        )}

      </div>
    </div>
  )
}

function IndicatorGroup({ label, items, color, border }: {
  label: string; items: string[]; color: string; border: string
}) {
  return (
    <div>
      <p style={{
        fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '.08em', color, margin: '0 0 4px',
      }}>
        {label}
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {items.map(item => (
          <span key={item} style={{
            fontSize: 10, padding: '2px 7px', borderRadius: 9999,
            background: `${color}14`,
            border: `1px solid ${border}`,
            color,
          }}>
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Suggested action buttons ──────────────────────────────────────────────────

const URGENCY_ORDER = ['today', 'tomorrow', 'this_week', 'asap', 'next_week', 'this_month', 'future', 'overdue']

const ACTION_META = {
  calendar: { icon: '📅', label: 'Add to calendar', color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  reminder: { icon: '⏰', label: 'Add reminder',    color: '#d97706', bg: '#fffbeb', border: '#fcd34d' },
  task:     { icon: '✓',  label: 'Create task',     color: '#15803d', bg: '#f0fdf4', border: '#bbf7d0' },
} as const

function SuggestedActionRow({
  kind, subtitle, phase3Payload,
}: {
  kind: keyof typeof ACTION_META
  subtitle: string
  phase3Payload: unknown
}) {
  const [done, setDone] = useState(false)
  const meta = ACTION_META[kind]

  function handleClick() {
    if (done) return
    // Phase 3: replace this log with the real API call
    console.log('[MailMind][Phase3]', { type: kind, payload: phase3Payload })
    setDone(true)
    setTimeout(() => setDone(false), 2500)
  }

  return (
    <button
      onClick={handleClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        width: '100%', textAlign: 'left',
        padding: '8px 10px', borderRadius: 8,
        background: done ? meta.bg : C.surface,
        border: `1px solid ${done ? meta.border : C.border}`,
        cursor: 'pointer',
        transition: 'all .18s',
        boxShadow: '0 1px 2px rgba(0,0,0,.04)',
      }}
    >
      {/* Icon circle */}
      <span style={{
        flexShrink: 0,
        width: 28, height: 28, borderRadius: '50%',
        background: done ? meta.bg : `${meta.color}14`,
        border: `1px solid ${meta.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13,
        transition: 'background .18s',
      }}>
        {done ? '✓' : meta.icon}
      </span>

      {/* Text */}
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{
          display: 'block', fontSize: 12, fontWeight: 600,
          color: done ? meta.color : C.textSecondary,
        }}>
          {done ? 'Added — Phase 3 coming' : meta.label}
        </span>
        {!done && subtitle && (
          <span style={{
            display: 'block', fontSize: 10, color: C.textMuted,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            marginTop: 1,
          }}>
            {subtitle}
          </span>
        )}
      </span>

      {/* Chevron */}
      {!done && (
        <span style={{ fontSize: 10, color: C.textMuted, flexShrink: 0 }}>›</span>
      )}
    </button>
  )
}

function SuggestedActions({ actions }: { actions: ActionResponse | null }) {
  if (!actions) return null
  const myTasks = actions.tasks.filter((t: TaskModel) => t.assignee === 'me')
  const hasAnything = actions.has_meeting || actions.has_deadlines || myTasks.length > 0
  if (!hasAnything) return null

  // Sort deadlines by urgency and pick the most pressing
  const sortedDeadlines = [...actions.deadlines].sort(
    (a, b) => URGENCY_ORDER.indexOf(a.urgency) - URGENCY_ORDER.indexOf(b.urgency)
  )
  const topDeadline = sortedDeadlines[0]
  const extraDeadlines = sortedDeadlines.length - 1

  return (
    <div className="mm-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
      <p style={{
        fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '.1em', color: C.textMuted, margin: 0,
      }}>
        Suggested Actions
      </p>

      {/* Calendar event */}
      {actions.has_meeting && (
        <SuggestedActionRow
          kind="calendar"
          subtitle={[
            actions.meeting.title,
            [actions.meeting.date_str, actions.meeting.time_str].filter(Boolean).join(' · '),
          ].filter(Boolean).join(' — ')}
          phase3Payload={{
            title:     actions.meeting.title,
            date_str:  actions.meeting.date_str,
            time_str:  actions.meeting.time_str,
            location:  actions.meeting.location,
            attendees: actions.meeting.attendees,
            agenda:    actions.meeting.agenda,
            duration:  actions.meeting.duration_minutes,
          }}
        />
      )}

      {/* Reminder for most urgent deadline */}
      {actions.has_deadlines && topDeadline && (
        <SuggestedActionRow
          kind="reminder"
          subtitle={[
            topDeadline.phrase,
            topDeadline.resolved_date ?? topDeadline.urgency,
            extraDeadlines > 0 ? `+${extraDeadlines} more` : '',
          ].filter(Boolean).join(' · ')}
          phase3Payload={sortedDeadlines.map(d => ({
            phrase:   d.phrase,
            date:     d.resolved_date,
            urgency:  d.urgency,
          }))}
        />
      )}

      {/* Tasks (my tasks only) */}
      {myTasks.length > 0 && (
        <SuggestedActionRow
          kind="task"
          subtitle={[
            myTasks[0].title,
            myTasks[0].due_date_str,
            myTasks.length > 1 ? `+${myTasks.length - 1} more` : '',
          ].filter(Boolean).join(' · ')}
          phase3Payload={myTasks.map(t => ({
            title:       t.title,
            description: t.description,
            due_date:    t.due_date_str,
            priority:    t.priority,
          }))}
        />
      )}
    </div>
  )
}

// ── Smart replies ─────────────────────────────────────────────────────────────

const TONE_PALETTE = {
  formal:   { label: 'Formal',   color: '#1e40af', bg: '#eff6ff', border: '#bfdbfe' },
  friendly: { label: 'Friendly', color: '#15803d', bg: '#f0fdf4', border: '#bbf7d0' },
  direct:   { label: 'Direct',   color: '#92400e', bg: '#fffbeb', border: '#fde68a' },
} as const

type ActionStatus = 'idle' | InsertResult | 'copied'

const STATUS_MESSAGE: Record<ActionStatus, string | null> = {
  idle:       null,
  success:    '✓ Inserted into compose',
  copied:     '✓ Copied to clipboard',
  no_compose: 'Open a reply compose window first',
  error:      'Insert failed — try Copy instead',
}
const STATUS_COLOR: Record<ActionStatus, string> = {
  idle:       'transparent',
  success:    '#15803d',
  copied:     '#15803d',
  no_compose: '#92400e',
  error:      '#dc2626',
}

function SmartReplies({ replies }: { replies: ReplyResponse | null }) {
  const [activeIdx,   setActiveIdx]   = useState(0)
  const [insertedIdx, setInsertedIdx] = useState<number | null>(null)
  const [editing,     setEditing]     = useState(false)
  const [editText,    setEditText]    = useState('')
  const [status,      setStatus]      = useState<ActionStatus>('idle')

  useEffect(() => {
    setActiveIdx(0); setInsertedIdx(null)
    setEditing(false); setEditText(''); setStatus('idle')
  }, [replies])

  if (!replies) return null

  // Automated / no-reply emails: show a dismissal card instead of variants
  if (!replies.reply_needed) {
    return (
      <div className="mm-fade-in" style={{
        display: 'flex', alignItems: 'flex-start', gap: 9,
        padding: '10px 12px',
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        borderRadius: 10, boxShadow: '0 1px 2px rgba(0,0,0,.04)',
      }}>
        <span style={{
          flexShrink: 0, width: 20, height: 20, borderRadius: '50%',
          background: '#15803d', color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, fontWeight: 700,
        }}>✓</span>
        <div>
          <p style={{ fontSize: 11, fontWeight: 600, color: '#15803d', margin: '0 0 2px' }}>
            No reply needed
          </p>
          <p style={{ fontSize: 10, color: '#15803d', margin: 0, lineHeight: 1.4, opacity: .8 }}>
            This appears to be an automated notification.
          </p>
        </div>
      </div>
    )
  }

  if (replies.count === 0) return null

  const variant = replies.variants[activeIdx]
  const tone    = TONE_PALETTE[variant.tone as keyof typeof TONE_PALETTE]
    ?? { label: variant.tone, color: C.textMuted, bg: C.bg, border: C.border }
  const displayText = editing ? editText : variant.text

  function switchTab(i: number) {
    setActiveIdx(i); setEditing(false); setEditText(''); setStatus('idle')
  }

  function startEditing() {
    setEditText(variant.text); setEditing(true); setStatus('idle')
  }

  function handleInsert() {
    const result = insertIntoCompose(displayText)
    if (result === 'success') { setInsertedIdx(activeIdx); setEditing(false) }
    setStatus(result)
    setTimeout(() => setStatus('idle'), result === 'success' ? 2500 : 3500)
  }

  function handleCopy() {
    navigator.clipboard.writeText(displayText).then(() => {
      setStatus('copied')
      setTimeout(() => setStatus('idle'), 2000)
    }).catch(() => {})
  }

  const statusMsg   = STATUS_MESSAGE[status]
  const statusColor = STATUS_COLOR[status]

  return (
    <div className="mm-fade-in" style={{
      background: C.surface, border: `1px solid ${C.border}`,
      borderRadius: 10, overflow: 'hidden',
      boxShadow: '0 1px 2px rgba(0,0,0,.04)',
    }}>

      {/* Section label */}
      <p style={{
        fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
        letterSpacing: '.1em', color: C.textMuted,
        margin: 0, padding: '8px 12px 0',
      }}>
        Smart Replies
      </p>

      {/* Variant tab pills */}
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', padding: '6px 12px 0' }}>
        {replies.variants.map((v, i) => {
          const isIns = insertedIdx === i
          const isAct = activeIdx === i
          return (
            <button key={i} onClick={() => switchTab(i)} style={{
              fontSize: 10, fontWeight: 600, cursor: 'pointer',
              padding: '3px 9px', borderRadius: 9999, transition: 'all .15s',
              border: `1px solid ${isIns ? '#bbf7d0' : isAct ? C.brand : C.border}`,
              background: isIns ? '#f0fdf4' : isAct ? C.brandBg : 'transparent',
              color: isIns ? '#15803d' : isAct ? C.brand : C.textMuted,
            }}>
              {isIns ? `✓ ${v.label}` : v.label}
            </button>
          )
        })}
      </div>

      {/* Tone badge */}
      <div style={{ padding: '6px 12px 0' }}>
        <span style={{
          display: 'inline-block',
          fontSize: 9, fontWeight: 700, letterSpacing: '.07em', textTransform: 'uppercase',
          padding: '2px 8px', borderRadius: 9999,
          background: tone.bg, border: `1px solid ${tone.border}`, color: tone.color,
        }}>
          {tone.label}
        </span>
      </div>

      {/* Reply body — textarea when editing, pre-wrap div otherwise */}
      <div style={{ padding: '6px 12px 0' }}>
        {editing ? (
          <textarea
            value={editText}
            onChange={e => setEditText(e.target.value)}
            autoFocus
            style={{
              width: '100%', boxSizing: 'border-box',
              fontSize: 11, color: C.textSecondary, lineHeight: 1.55,
              background: C.bg, borderRadius: 6,
              padding: '8px 10px',
              border: `1px solid ${tone.border}`,
              fontFamily: 'inherit',
              resize: 'vertical', minHeight: 100, maxHeight: 220,
              outline: 'none',
            }}
          />
        ) : (
          <div style={{
            fontSize: 11, color: C.textSecondary, lineHeight: 1.55,
            background: C.bg, borderRadius: 6,
            padding: '8px 10px',
            border: `1px solid ${insertedIdx === activeIdx ? tone.border : C.borderFaint}`,
            whiteSpace: 'pre-wrap', maxHeight: 130, overflowY: 'auto',
            fontFamily: 'inherit', transition: 'border-color .18s',
          }}>
            {variant.text}
          </div>
        )}
      </div>

      {/* Status message */}
      {statusMsg && (
        <p style={{
          fontSize: 10, fontWeight: 500, textAlign: 'center',
          color: statusColor, margin: '5px 12px 0', lineHeight: 1.4,
        }}>
          {statusMsg}
        </p>
      )}

      {/* Action row: Insert | Edit/Done | Copy */}
      <div style={{ display: 'flex', gap: 5, padding: '7px 12px 10px' }}>

        <button onClick={handleInsert} style={{
          flex: 1, fontSize: 11, fontWeight: 600, cursor: 'pointer',
          padding: '6px 0', borderRadius: 7, transition: 'all .18s',
          border: `1px solid ${tone.color}`,
          background: tone.color, color: '#fff',
        }}>
          {editing ? 'Insert edited reply' : 'Insert into compose'}
        </button>

        <button
          onClick={editing ? () => setEditing(false) : startEditing}
          style={{
            fontSize: 10, fontWeight: 600, flexShrink: 0, cursor: 'pointer',
            padding: '6px 10px', borderRadius: 7, transition: 'all .18s',
            border: `1px solid ${editing ? tone.border : C.border}`,
            background: editing ? tone.bg : 'transparent',
            color: editing ? tone.color : C.textMuted,
          }}
        >
          {editing ? 'Done' : 'Edit'}
        </button>

        <button onClick={handleCopy} style={{
          fontSize: 10, fontWeight: 600, flexShrink: 0, cursor: 'pointer',
          padding: '6px 10px', borderRadius: 7, transition: 'all .18s',
          border: `1px solid ${status === 'copied' ? '#bbf7d0' : C.border}`,
          background: status === 'copied' ? '#f0fdf4' : 'transparent',
          color: status === 'copied' ? '#15803d' : C.textMuted,
        }}>
          {status === 'copied' ? '✓' : 'Copy'}
        </button>

      </div>
    </div>
  )
}

// ── Classification badge metadata ─────────────────────────────────────────────

const CATEGORY_META: Record<string, { label: string; icon: string; color: string; bg: string; border: string }> = {
  meeting:   { label: 'Meeting',   icon: '📅', color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  complaint: { label: 'Complaint', icon: '⚠',  color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  job:       { label: 'Job',       icon: '💼', color: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe' },
  update:    { label: 'Update',    icon: '📋', color: '#475569', bg: '#f1f5f9', border: '#e2e8f0' },
  invoice:   { label: 'Invoice',   icon: '💳', color: '#d97706', bg: '#fffbeb', border: '#fcd34d' },
  support:   { label: 'Support',   icon: '🔧', color: '#b45309', bg: '#fef9c3', border: '#fde68a' },
  social:    { label: 'Social',    icon: '💬', color: '#15803d', bg: '#f0fdf4', border: '#bbf7d0' },
  spam:      { label: 'Spam',      icon: '🚫', color: '#6b7280', bg: '#f3f4f6', border: '#e5e7eb' },
}

const PRIORITY_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  urgent: { label: 'Urgent', color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  high:   { label: 'High',   color: '#d97706', bg: '#fffbeb', border: '#fcd34d' },
  normal: { label: 'Normal', color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  low:    { label: 'Low',    color: '#6b7280', bg: '#f3f4f6', border: '#e5e7eb' },
}

function ClassificationBadge({
  classification, loading,
}: {
  classification: ClassifyResponse | null
  loading: boolean
}) {
  if (!loading && !classification) return null

  const cat = classification ? (CATEGORY_META[classification.category] ?? CATEGORY_META.update) : null
  const pri = classification ? (PRIORITY_META[classification.priority] ?? PRIORITY_META.normal) : null

  return (
    <div style={{
      background: C.surface, border: `1px solid ${C.border}`,
      borderRadius: 10, padding: '10px 12px',
      boxShadow: '0 1px 2px rgba(0,0,0,.04)',
    }}>
      <p style={{
        fontSize: 10, fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: '.08em',
        color: C.textMuted, margin: '0 0 8px',
      }}>
        Classification
      </p>

      {loading ? <Skeleton lines={1} /> : (
        <div className="mm-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>

          {/* "Detected: [Category] + [Priority] Priority" */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11, color: C.textMuted, fontWeight: 500 }}>Detected:</span>

            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              fontSize: 11, fontWeight: 600,
              padding: '2px 8px', borderRadius: 9999,
              background: cat!.bg, border: `1px solid ${cat!.border}`, color: cat!.color,
            }}>
              <span>{cat!.icon}</span>
              {cat!.label}
            </span>

            <span style={{ fontSize: 11, color: C.textMuted }}>+</span>

            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              fontSize: 11, fontWeight: 600,
              padding: '2px 8px', borderRadius: 9999,
              background: pri!.bg, border: `1px solid ${pri!.border}`, color: pri!.color,
            }}>
              <span
                className={classification!.priority === 'urgent' ? 'mm-urgent-pulse' : undefined}
                style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: pri!.color, display: 'inline-block', flexShrink: 0,
                }}
              />
              {pri!.label} Priority
            </span>
          </div>

          {/* Reason */}
          <p style={{ fontSize: 11, color: C.textMuted, margin: 0, lineHeight: 1.45, fontStyle: 'italic' }}>
            {classification!.reason}
          </p>

          {/* Confidence bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              flex: 1, height: 3, borderRadius: 9999,
              background: C.borderFaint, overflow: 'hidden',
            }}>
              <div style={{
                height: '100%', borderRadius: 9999,
                width: `${Math.round(classification!.confidence * 100)}%`,
                background: cat!.color, transition: 'width .4s ease',
              }} />
            </div>
            <span style={{ fontSize: 10, color: C.textMuted, whiteSpace: 'nowrap' }}>
              {Math.round(classification!.confidence * 100)}% confident
            </span>
          </div>

        </div>
      )}
    </div>
  )
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

  const [open, setOpen]                       = useState(true)
  const [analysis, setAnalysis]               = useState<AnalyzeResponse | null>(null)
  const [analyzing, setAnalyzing]             = useState(false)
  const [analyzeError, setAnalyzeError]       = useState<string | null>(null)
  const [summary, setSummary]                 = useState<SummarizeResponse | null>(null)
  const [summarizing, setSummarizing]         = useState(false)
  const [classification, setClassification]   = useState<ClassifyResponse | null>(null)
  const [classifying, setClassifying]         = useState(false)
  const [trust, setTrust]                     = useState<TrustResponse | null>(null)
  const [actions, setActions]                 = useState<ActionResponse | null>(null)
  const [replies, setReplies]                 = useState<ReplyResponse | null>(null)
  const [flowchart, setFlowchart]             = useState<FlowchartResponse | null>(null)
  const [flowcharting, setFlowcharting]       = useState(false)

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

    // Classification runs in parallel
    setClassification(null); setClassifying(true)
    classifyEmail(data.subject, data.body)
      .then(d  => { if (!cancelled) setClassification(d) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setClassifying(false) })

    // Trust check runs in parallel (rule-based, fast)
    setTrust(null)
    checkTrust(data.subject, data.body)
      .then(d  => { if (!cancelled) setTrust(d) })
      .catch(() => {})

    // Action extraction runs in parallel (meeting + tasks via LLM, deadlines rule-based)
    setActions(null)
    extractActions(data.subject, data.body, data.sender ?? '')
      .then(d  => { if (!cancelled) setActions(d) })
      .catch(() => {})

    // Bullet summary runs in parallel for long emails only
    setSummary(null)
    if (countWords(data.body) >= SUMMARY_WORD_THRESHOLD) {
      setSummarizing(true)
      summarizeEmail(data.body)
        .then(d  => { if (!cancelled) setSummary(d) })
        .catch(() => {})
        .finally(() => { if (!cancelled) setSummarizing(false) })
    }

    // Flowchart extraction runs in parallel
    setFlowchart(null); setFlowcharting(true)
    detectFlowchart(data.subject, data.body)
      .then(d  => { if (!cancelled) setFlowchart(d) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setFlowcharting(false) })
  }

  // Cancel + reset when the open email changes
  useEffect(() => {
    cancelRef.current()
    setAnalysis(null); setAnalyzeError(null); setAnalyzing(false)
    setSummary(null); setSummarizing(false)
    setClassification(null); setClassifying(false)
    setTrust(null); setActions(null); setReplies(null)
    setFlowchart(null); setFlowcharting(false)
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
    setClassification(null); setClassifying(false)
    setTrust(null); setActions(null); setReplies(null)
    setFlowchart(null); setFlowcharting(false)
  }, [privacyMode])

  // Generate smart replies once classification is ready (provides category context)
  useEffect(() => {
    if (!classification || !emailData) return
    let cancelled = false
    generateReplies(emailData.subject, emailData.body, emailData.sender ?? '', classification.category, classification.priority)
      .then(d => { if (!cancelled) setReplies(d) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [classification])

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
                    <TrustBanner trust={trust} />
                    <ClassificationBadge classification={classification} loading={classifying} />
                    <SmartReplies replies={replies} />
                    <SuggestedActions actions={actions} />
                    {(summarizing || summary !== null) && (
                      <SummaryPanel summary={summary} loading={summarizing} body={emailData?.body ?? ''} />
                    )}
                    <FlowchartPanel flowchart={flowchart} loading={flowcharting} />
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

// ── Flowchart panel ───────────────────────────────────────────────────────────
const FLOWCHART_TYPE_LABEL: Record<string, { label: string; color: string; bg: string; border: string }> = {
  sequential: { label: 'Sequential', color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  branching:  { label: 'Branching',  color: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe' },
  parallel:   { label: 'Parallel',   color: '#15803d', bg: '#f0fdf4', border: '#bbf7d0' },
}

function FlowchartPanel({
  flowchart, loading,
}: {
  flowchart: FlowchartResponse | null
  loading: boolean
}) {
  const svgContainerRef = useRef<HTMLDivElement>(null)
  const [svgHtml, setSvgHtml]       = useState('')
  const [renderErr, setRenderErr]   = useState(false)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    if (!flowchart?.mermaid) { setSvgHtml(''); setRenderErr(false); return }
    let cancelled = false
    setRenderErr(false)
    const uid = `mm-fc-${Date.now()}`
    mermaid.render(uid, flowchart.mermaid)
      .then(({ svg }) => { if (!cancelled) setSvgHtml(svg) })
      .catch(() => { if (!cancelled) setRenderErr(true) })
    return () => { cancelled = true }
  }, [flowchart?.mermaid])

  // Style the rendered SVG to fill the container width
  useEffect(() => {
    const svg = svgContainerRef.current?.querySelector('svg')
    if (!svg) return
    svg.style.width = '100%'
    svg.style.maxWidth = '100%'
    svg.removeAttribute('height')
  }, [svgHtml])

  function handleDownload() {
    const svg = svgContainerRef.current?.querySelector('svg')
    if (!svg || downloading) return
    setDownloading(true)

    const serializer = new XMLSerializer()
    const svgStr = serializer.serializeToString(svg)
    const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)

    const img = new Image()
    img.onload = () => {
      const scale = 2
      const canvas = document.createElement('canvas')
      canvas.width  = (svg.clientWidth  || 400) * scale
      canvas.height = (svg.clientHeight || 300) * scale
      const ctx = canvas.getContext('2d')!
      ctx.scale(scale, scale)
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0)
      URL.revokeObjectURL(url)
      canvas.toBlob(pngBlob => {
        if (!pngBlob) { setDownloading(false); return }
        const link = document.createElement('a')
        link.download = `${flowchart?.title || 'flowchart'}.png`
        link.href = URL.createObjectURL(pngBlob)
        link.click()
        setTimeout(() => { URL.revokeObjectURL(link.href); setDownloading(false) }, 1000)
      }, 'image/png')
    }
    img.onerror = () => { URL.revokeObjectURL(url); setDownloading(false) }
    img.src = url
  }

  // Don't render anything when loading is done and no flowchart was found
  if (!loading && (!flowchart || !flowchart.has_flowchart)) return null

  const typeMeta = flowchart?.flowchart_type
    ? (FLOWCHART_TYPE_LABEL[flowchart.flowchart_type] ?? null)
    : null

  return (
    <Panel title="Process Flowchart">
      {loading ? (
        <Skeleton lines={6} />
      ) : (
        <div className="mm-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>

          {/* Title + type badge row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
            {flowchart!.title && (
              <span style={{ fontSize: 11, fontWeight: 600, color: C.textSecondary, flex: 1, minWidth: 0,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {flowchart!.title}
              </span>
            )}
            {typeMeta && (
              <span style={{
                flexShrink: 0, fontSize: 9, fontWeight: 700,
                textTransform: 'uppercase', letterSpacing: '.07em',
                padding: '2px 7px', borderRadius: 9999,
                background: typeMeta.bg, border: `1px solid ${typeMeta.border}`, color: typeMeta.color,
              }}>
                {typeMeta.label}
              </span>
            )}
          </div>

          {/* SVG diagram */}
          {renderErr ? (
            <p style={{ fontSize: 11, color: C.textMuted, fontStyle: 'italic', margin: 0 }}>
              Could not render diagram.
            </p>
          ) : svgHtml ? (
            <div
              ref={svgContainerRef}
              dangerouslySetInnerHTML={{ __html: svgHtml }}
              style={{
                overflowX: 'auto', borderRadius: 6,
                border: `1px solid ${C.border}`,
                background: C.surface, padding: 8,
              }}
            />
          ) : (
            <Skeleton lines={5} />
          )}

          {/* Download button */}
          {svgHtml && !renderErr && (
            <button
              onClick={handleDownload}
              disabled={downloading}
              style={{
                width: '100%', fontSize: 11, fontWeight: 600,
                padding: '6px 0', borderRadius: 6, cursor: downloading ? 'not-allowed' : 'pointer',
                border: `1px solid ${C.border}`,
                background: downloading ? C.borderFaint : C.surface,
                color: downloading ? C.textDisabled : C.textSecondary,
                transition: 'all .15s', display: 'flex', alignItems: 'center',
                justifyContent: 'center', gap: 5,
              }}
            >
              <span style={{ fontSize: 12 }}>⬇</span>
              {downloading ? 'Downloading…' : 'Download as image'}
            </button>
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
