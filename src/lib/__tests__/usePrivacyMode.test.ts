import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePrivacyMode } from '../usePrivacyMode'
import type { PrivacyMode } from '../usePrivacyMode'

// ── Chrome storage mock factory ───────────────────────────────────────────────
type OnChangedListener = (
  changes: Record<string, { oldValue?: unknown; newValue: unknown }>,
  area: string,
) => void

function makeChromeMock(initial: Record<string, unknown> = {}) {
  const store: Record<string, unknown> = { ...initial }
  const listeners: OnChangedListener[] = []

  const chromeMock = {
    storage: {
      sync: {
        get: vi.fn((key: string, cb: (res: Record<string, unknown>) => void) => {
          // Synchronous callback so the state update lands inside act()
          cb({ [key]: store[key] })
        }),
        set: vi.fn((data: Record<string, unknown>, cb?: () => void) => {
          const changes: Record<string, { oldValue?: unknown; newValue: unknown }> = {}
          for (const [k, v] of Object.entries(data)) {
            changes[k] = { oldValue: store[k], newValue: v }
            store[k] = v
          }
          listeners.forEach(l => l(changes, 'sync'))
          cb?.()
        }),
      },
      onChanged: {
        addListener: vi.fn((l: OnChangedListener) => listeners.push(l)),
        removeListener: vi.fn((l: OnChangedListener) => {
          const i = listeners.indexOf(l)
          if (i !== -1) listeners.splice(i, 1)
        }),
      },
    },
  }

  return { chromeMock, store, listeners }
}

// ── Tests ─────────────────────────────────────────────────────────────────────
describe('usePrivacyMode', () => {
  beforeEach(() => { vi.resetAllMocks() })

  it('defaults to smart when storage is empty', async () => {
    const { chromeMock } = makeChromeMock()
    vi.stubGlobal('chrome', chromeMock)

    const { result } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    expect(result.current[0]).toBe('smart')
  })

  it('reads "off" mode persisted in storage', async () => {
    const { chromeMock } = makeChromeMock({ privacyMode: 'off' })
    vi.stubGlobal('chrome', chromeMock)

    const { result } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    expect(result.current[0]).toBe('off')
  })

  it('reads "manual" mode persisted in storage', async () => {
    const { chromeMock } = makeChromeMock({ privacyMode: 'manual' })
    vi.stubGlobal('chrome', chromeMock)

    const { result } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    expect(result.current[0]).toBe('manual')
  })

  it('ignores unknown values from storage and keeps the default', async () => {
    const { chromeMock } = makeChromeMock({ privacyMode: 'stealth-mode' })
    vi.stubGlobal('chrome', chromeMock)

    const { result } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    expect(result.current[0]).toBe('smart')
  })

  it('persists mode change to chrome.storage.sync', async () => {
    const { chromeMock } = makeChromeMock()
    vi.stubGlobal('chrome', chromeMock)

    const { result } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    act(() => { result.current[1]('off') })

    expect(chromeMock.storage.sync.set).toHaveBeenCalledWith({ privacyMode: 'off' })
    expect(result.current[0]).toBe('off')
  })

  it('cycles through all three modes correctly', async () => {
    const { chromeMock } = makeChromeMock()
    vi.stubGlobal('chrome', chromeMock)

    const { result } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    const modes: PrivacyMode[] = ['off', 'manual', 'smart']
    for (const m of modes) {
      act(() => { result.current[1](m) })
      expect(result.current[0]).toBe(m)
    }
  })

  it('updates mode when storage changes externally (cross-context sync)', async () => {
    const { chromeMock, listeners } = makeChromeMock()
    vi.stubGlobal('chrome', chromeMock)

    const { result } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    expect(result.current[0]).toBe('smart')

    act(() => {
      listeners.forEach(l =>
        l({ privacyMode: { oldValue: 'smart', newValue: 'manual' } }, 'sync'),
      )
    })

    expect(result.current[0]).toBe('manual')
  })

  it('ignores onChanged events for unrelated storage keys', async () => {
    const { chromeMock, listeners } = makeChromeMock()
    vi.stubGlobal('chrome', chromeMock)

    const { result } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    act(() => {
      listeners.forEach(l =>
        l({ someOtherKey: { oldValue: 'x', newValue: 'y' } }, 'sync'),
      )
    })

    expect(result.current[0]).toBe('smart')
  })

  it('removes the onChanged listener on unmount', async () => {
    const { chromeMock } = makeChromeMock()
    vi.stubGlobal('chrome', chromeMock)

    const { unmount } = renderHook(() => usePrivacyMode())
    await act(async () => {})

    unmount()

    expect(chromeMock.storage.onChanged.removeListener).toHaveBeenCalledOnce()
  })

  it('does not throw when storage changes fire after unmount', async () => {
    const { chromeMock, listeners } = makeChromeMock()
    vi.stubGlobal('chrome', chromeMock)

    const { unmount } = renderHook(() => usePrivacyMode())
    await act(async () => {})
    unmount()

    expect(() => {
      listeners.forEach(l =>
        l({ privacyMode: { oldValue: 'smart', newValue: 'off' } }, 'sync'),
      )
    }).not.toThrow()
  })
})

// ── Privacy-mode blocking contract ────────────────────────────────────────────
// Structural invariants verified by reading Sidebar.tsx — documented here for
// the audit trail rather than as runtime assertions.
//
//  Off mode    → runAnalysis is never called:
//                - auto-analyze effect guards: `if (privacyMode !== 'smart') return`
//                - off-mode effect: cancelRef.current() cancels any in-flight call
//                - ManualAnalysisPrompt / GrammarPanel / ToneRewritePanel are not
//                  rendered (body renders PrivacyOffState exclusively)
//
//  Manual mode → runAnalysis is NOT called automatically:
//                - auto-analyze effect returns early: `privacyMode !== 'smart'`
//                - runAnalysis is only reachable via the "Analyze this email" button
//
//  Smart mode  → runAnalysis runs on mount and on every new email:
//                - auto-analyze effect fires when emailData?.emailId changes or
//                  privacyMode transitions to 'smart' with an email already open
//
//  Off switch while call in flight (data-leak fix):
//                - off-mode effect: cancelRef.current() sets `cancelled = true`,
//                  so every .then/.catch/.finally in the promise chain is a no-op
