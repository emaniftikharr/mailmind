import { useState } from 'react'
import type { ReactNode } from 'react'
import {
  SUPPORTED_LANGUAGES,
  type SupportedLanguage,
  translateText,
} from '../lib/api'

interface SidebarProps {
  emailOpen: boolean
  onVisibilityChange?: (visible: boolean) => void
}

const W = 320

export function Sidebar({ emailOpen, onVisibilityChange }: SidebarProps) {
  const [open, setOpen] = useState(true)

  function show() {
    setOpen(true)
    onVisibilityChange?.(true)
  }

  function hide() {
    setOpen(false)
    onVisibilityChange?.(false)
  }

  if (!open) {
    return (
      <button
        onClick={show}
        aria-label="Open MailMind"
        style={{
          position: 'fixed',
          right: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          zIndex: 2147483647,
          width: 28,
          padding: '20px 0',
          background: '#2563eb',
          color: '#fff',
          border: 'none',
          borderRadius: '6px 0 0 6px',
          cursor: 'pointer',
          fontSize: 13,
          boxShadow: '-2px 0 8px rgba(0,0,0,.15)',
        }}
      >
        ✉
      </button>
    )
  }

  return (
    /*
     * Bug fixes applied here:
     * 1. All critical layout props use inline styles — Gmail's global CSS
     *    (box-sizing, font-family, line-height) cannot override inline styles.
     * 2. height: 100vh instead of Tailwind h-screen, which Gmail's flex
     *    context can squash.
     * 3. zIndex: 2147483647 (max int32) ensures we're above Gmail overlays.
     * 4. fontFamily / fontSize reset prevents Gmail's font from bleeding in.
     */
    <div
      style={{
        position: 'fixed',
        right: 0,
        top: 0,
        width: W,
        height: '100vh',
        zIndex: 2147483647,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: 14,
        lineHeight: 1.5,
        color: '#111827',
        boxSizing: 'border-box',
        background: '#fff',
        borderLeft: '1px solid #e5e7eb',
        boxShadow: '-4px 0 16px rgba(0,0,0,.1)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          background: '#2563eb',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color: '#fff', fontSize: 16 }}>✉</span>
          <span style={{ color: '#fff', fontWeight: 600, fontSize: 14, letterSpacing: '.02em' }}>
            MailMind
          </span>
        </div>
        <button
          onClick={hide}
          aria-label="Close MailMind"
          style={{
            background: 'none',
            border: 'none',
            color: 'rgba(255,255,255,.7)',
            fontSize: 22,
            cursor: 'pointer',
            lineHeight: 1,
            padding: 0,
          }}
        >
          ×
        </button>
      </div>

      {/* Status strip */}
      <div
        style={{
          padding: '6px 16px',
          background: '#eff6ff',
          borderBottom: '1px solid #dbeafe',
          flexShrink: 0,
        }}
      >
        <StatusBadge active={emailOpen} />
      </div>

      {/* Scrollable body */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 12,
          background: '#f9fafb',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        {emailOpen ? <EmailOpenPanels /> : <InboxPanels />}
        <TranslatePanel emailOpen={emailOpen} />
      </div>

      {/* Footer */}
      <div
        style={{
          padding: '6px 16px',
          borderTop: '1px solid #e5e7eb',
          background: '#fff',
          textAlign: 'center',
          flexShrink: 0,
          fontSize: 11,
          color: '#9ca3af',
        }}
      >
        MailMind · AI Email Assistant
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 11,
        fontWeight: 500,
        padding: '2px 8px',
        borderRadius: 9999,
        background: active ? '#dcfce7' : '#f3f4f6',
        color: active ? '#15803d' : '#6b7280',
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: active ? '#22c55e' : '#9ca3af',
          display: 'inline-block',
        }}
      />
      {active ? 'Email open' : 'No email selected'}
    </span>
  )
}

function EmailOpenPanels() {
  return (
    <>
      <Panel title="Summary">
        <Placeholder>Analyzing email…</Placeholder>
      </Panel>
      <Panel title="Action Items">
        <Placeholder>Detecting tasks…</Placeholder>
      </Panel>
      <Panel title="Quick Reply">
        <Placeholder>Generating suggestions…</Placeholder>
      </Panel>
      <Panel title="Tone &amp; Grammar">
        <Placeholder>Reading tone…</Placeholder>
      </Panel>
    </>
  )
}

function InboxPanels() {
  return (
    <>
      <Panel title="Summary">
        <Placeholder>Open an email to summarize it.</Placeholder>
      </Panel>
      <Panel title="Compose Assist">
        <Placeholder>Start composing to get suggestions.</Placeholder>
      </Panel>
      <Panel title="Action Items">
        <Placeholder>No email selected.</Placeholder>
      </Panel>
    </>
  )
}

function TranslatePanel({ emailOpen }: { emailOpen: boolean }) {
  const [language, setLanguage] = useState<SupportedLanguage>('Spanish')
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleTranslate() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await translateText(
        emailOpen ? '[Email body will be extracted here]' : 'No email selected.',
        language,
      )
      setResult(data.translated_text)
    } catch {
      setError('Could not reach the server. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Panel title="Translate">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <select
          value={language}
          onChange={(e) => {
            setLanguage(e.target.value as SupportedLanguage)
            setResult(null)
          }}
          style={{
            width: '100%',
            fontSize: 13,
            padding: '4px 8px',
            border: '1px solid #e5e7eb',
            borderRadius: 6,
            background: '#fff',
            color: '#374151',
            cursor: 'pointer',
          }}
        >
          {SUPPORTED_LANGUAGES.map((lang) => (
            <option key={lang} value={lang}>{lang}</option>
          ))}
        </select>

        <button
          onClick={handleTranslate}
          disabled={loading}
          style={{
            width: '100%',
            fontSize: 13,
            fontWeight: 500,
            padding: '5px 0',
            background: loading ? '#93c5fd' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'background .15s',
          }}
        >
          {loading ? 'Translating…' : 'Translate'}
        </button>

        {error && (
          <p style={{ fontSize: 12, color: '#dc2626', margin: 0 }}>{error}</p>
        )}

        {result && (
          <div
            style={{
              fontSize: 13,
              color: '#374151',
              background: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              padding: '8px 10px',
              lineHeight: 1.6,
            }}
          >
            {result}
          </div>
        )}
      </div>
    </Panel>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div
      style={{
        background: '#fff',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        padding: 12,
        boxShadow: '0 1px 3px rgba(0,0,0,.06)',
        boxSizing: 'border-box',
      }}
    >
      <p
        style={{
          fontSize: 10,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '.08em',
          color: '#6b7280',
          margin: '0 0 8px',
        }}
      >
        {title}
      </p>
      {children}
    </div>
  )
}

function Placeholder({ children }: { children: ReactNode }) {
  return (
    <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic', margin: 0 }}>
      {children}
    </p>
  )
}
