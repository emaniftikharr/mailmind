import { useState } from 'react'

export function Sidebar() {
  const [open, setOpen] = useState(true)

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-[9999] bg-blue-600 text-white px-2 py-4 rounded-l-lg text-sm font-medium shadow-lg hover:bg-blue-700 transition-colors"
      >
        ✉<br />AI
      </button>
    )
  }

  return (
    <div className="fixed right-0 top-0 h-screen w-80 z-[9999] bg-white border-l border-gray-200 shadow-xl flex flex-col font-sans">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-blue-600 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-white text-base">✉</span>
          <h1 className="text-white font-semibold text-sm tracking-wide">MailMind</h1>
        </div>
        <button
          onClick={() => setOpen(false)}
          className="text-white/70 hover:text-white text-xl leading-none transition-colors"
          aria-label="Close sidebar"
        >
          ×
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
        <Panel title="Summary">
          <p className="text-sm text-gray-400 italic">Select an email to summarize…</p>
        </Panel>

        <Panel title="Compose Assist">
          <p className="text-sm text-gray-400 italic">Start composing to get suggestions…</p>
        </Panel>

        <Panel title="Action Items">
          <p className="text-sm text-gray-400 italic">No actions detected yet…</p>
        </Panel>

        <Panel title="Quick Reply">
          <p className="text-sm text-gray-400 italic">Open a thread to generate replies…</p>
        </Panel>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-200 bg-white shrink-0">
        <p className="text-xs text-gray-400 text-center">MailMind · AI Email Assistant</p>
      </div>
    </div>
  )
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{title}</p>
      {children}
    </div>
  )
}
