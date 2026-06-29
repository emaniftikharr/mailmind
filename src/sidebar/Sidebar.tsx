import { useState } from 'react'
import type { ReactNode } from 'react'

interface SidebarProps {
  emailOpen: boolean
  onVisibilityChange?: (visible: boolean) => void
}

const SIDEBAR_WIDTH = 320

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
        style={{ width: 28 }}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-[9999] bg-blue-600 text-white py-5 rounded-l-lg shadow-lg hover:bg-blue-700 transition-colors text-xs"
        aria-label="Open MailMind"
      >
        ✉
      </button>
    )
  }

  return (
    <div
      style={{ width: SIDEBAR_WIDTH }}
      className="fixed right-0 top-0 h-screen z-[9999] bg-white border-l border-gray-200 shadow-xl flex flex-col font-sans text-gray-900"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-blue-600 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-white text-base">✉</span>
          <span className="text-white font-semibold text-sm tracking-wide">MailMind</span>
        </div>
        <button
          onClick={hide}
          className="text-white/70 hover:text-white text-xl leading-none transition-colors"
          aria-label="Close MailMind"
        >
          ×
        </button>
      </div>

      {/* Status badge */}
      <div className="px-4 py-2 bg-blue-50 border-b border-blue-100 shrink-0">
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full ${
          emailOpen
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-gray-500'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${emailOpen ? 'bg-green-500' : 'bg-gray-400'}`} />
          {emailOpen ? 'Email open' : 'No email selected'}
        </span>
      </div>

      {/* Panels */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gray-50">
        {emailOpen ? <EmailOpenPanels /> : <InboxPanels />}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-200 bg-white shrink-0 text-center">
        <p className="text-xs text-gray-400">MailMind · AI Email Assistant</p>
      </div>
    </div>
  )
}

function EmailOpenPanels() {
  return (
    <>
      <Panel title="Summary">
        <p className="text-sm text-gray-400 italic">Analyzing email…</p>
      </Panel>
      <Panel title="Action Items">
        <p className="text-sm text-gray-400 italic">Detecting tasks…</p>
      </Panel>
      <Panel title="Quick Reply">
        <p className="text-sm text-gray-400 italic">Generating suggestions…</p>
      </Panel>
      <Panel title="Tone & Sentiment">
        <p className="text-sm text-gray-400 italic">Reading tone…</p>
      </Panel>
    </>
  )
}

function InboxPanels() {
  return (
    <>
      <Panel title="Summary">
        <p className="text-sm text-gray-400 italic">Open an email to summarize it.</p>
      </Panel>
      <Panel title="Compose Assist">
        <p className="text-sm text-gray-400 italic">Start composing to get suggestions.</p>
      </Panel>
      <Panel title="Action Items">
        <p className="text-sm text-gray-400 italic">No email selected.</p>
      </Panel>
    </>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</p>
      {children}
    </div>
  )
}
