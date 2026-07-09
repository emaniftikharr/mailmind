/** Ordered selector fallbacks for Gmail's main scrolling container */
const SCROLL_SELECTORS = ['.AO', 'div[role="main"]']

export function findScrollContainer(): HTMLElement | null {
  for (const sel of SCROLL_SELECTORS) {
    const el = document.querySelector<HTMLElement>(sel)
    if (el) return el
  }
  return null
}

/**
 * Resolves when Gmail's main content area is present in the DOM.
 * Gmail is a SPA that builds its DOM asynchronously after page load.
 */
export function waitForGmail(timeoutMs = 15_000): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector('div[role="main"]')) {
      resolve()
      return
    }

    const timer = setTimeout(() => {
      observer.disconnect()
      reject(new Error('[MailMind] Gmail main content did not appear'))
    }, timeoutMs)

    const observer = new MutationObserver(() => {
      if (document.querySelector('div[role="main"]')) {
        clearTimeout(timer)
        observer.disconnect()
        resolve()
      }
    })

    observer.observe(document.documentElement, { childList: true, subtree: true })
  })
}

/**
 * Returns true when the URL hash indicates an open email thread.
 * Gmail hash pattern: #inbox/THREAD_ID, #label/NAME/THREAD_ID, etc.
 */
export function isEmailOpen(): boolean {
  return /[#][^/]+\/[A-Za-z0-9]{10,}/.test(window.location.hash)
}

/**
 * Fires callback on Gmail SPA navigation (hashchange).
 * Returns a cleanup function to remove the listener.
 */
export function watchNavigation(callback: (emailOpen: boolean) => void): () => void {
  const handler = () => callback(isEmailOpen())
  window.addEventListener('hashchange', handler)
  return () => window.removeEventListener('hashchange', handler)
}

/** Nudge Gmail's scroll container right so sidebar doesn't cover content. */
export function setGmailMargin(px: number): void {
  const el = findScrollContainer()
  if (el) el.style.marginRight = px > 0 ? `${px}px` : ''
}

export interface EmailData {
  emailId: string
  subject: string
  body: string
  sender: string
}

/** Scrape the open email's subject, body text, and sender from the Gmail DOM. */
export function scrapeEmailData(): EmailData | null {
  const hash = window.location.hash
  const threadMatch = hash.match(/[A-Za-z0-9]{10,}/)
  if (!threadMatch) return null
  const emailId = threadMatch[0]

  const subjectEl = document.querySelector<HTMLElement>('h2[data-thread-perm-id], .hP')
  const subject = subjectEl?.textContent?.trim() ?? ''

  const bodyEls = document.querySelectorAll<HTMLElement>('.a3s.aiL, div[data-message-id] .a3s')
  const body = Array.from(bodyEls)
    .map(el => el.innerText?.trim())
    .filter(Boolean)
    .join('\n\n')

  const senderEl = document.querySelector<HTMLElement>('.gD[email], span[email]')
  const sender = senderEl?.getAttribute('email') ?? ''

  if (!body) return null
  return { emailId, subject, body, sender }
}
