/**
 * Gmail compose window injection utilities.
 *
 * Finds the active contenteditable compose body and replaces its content
 * with a given plain-text reply. Tries execCommand first so Gmail's own
 * mutation listeners fire; falls back to innerHTML for resilience.
 */

// Ordered: most specific first
const COMPOSE_SELECTORS = [
  'div[aria-label="Message Body"][contenteditable="true"]',
  'div[g_editable="true"][contenteditable="true"]',
  'div.Am.Al.editable[contenteditable="true"]',
  'div.LW-avf[contenteditable="true"]',
]

/** Returns the most recently rendered compose body div, or null if none is open. */
export function findComposeBody(): HTMLElement | null {
  for (const sel of COMPOSE_SELECTORS) {
    const els = document.querySelectorAll<HTMLElement>(sel)
    if (els.length > 0) return els[els.length - 1]
  }
  return null
}

export type InsertResult = 'success' | 'no_compose' | 'error'

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/**
 * Replaces the Gmail compose body with the given plain-text reply.
 *
 * Returns:
 *   'success'    — text was inserted
 *   'no_compose' — no compose window is currently open
 *   'error'      — unexpected DOM error
 */
export function insertIntoCompose(text: string): InsertResult {
  const body = findComposeBody()
  if (!body) return 'no_compose'

  try {
    body.focus()

    // Attempt 1: use Selection API + execCommand — fires Gmail's native listeners
    const sel = window.getSelection()
    if (sel) {
      sel.selectAllChildren(body)
      sel.deleteFromDocument()
    } else {
      body.innerHTML = ''
    }

    const inserted = document.execCommand('insertText', false, text)

    // Attempt 2: direct innerHTML if execCommand returned false or left body empty
    if (!inserted || body.innerText.trim() === '') {
      body.innerHTML = text
        .split('\n')
        .map(line => line === '' ? '<div><br></div>' : `<div>${escapeHtml(line)}</div>`)
        .join('')
      body.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }))
      body.dispatchEvent(new Event('change', { bubbles: true }))
    }

    body.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    return 'success'
  } catch {
    return 'error'
  }
}
