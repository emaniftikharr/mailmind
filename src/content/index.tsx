import React from 'react'
import ReactDOM from 'react-dom/client'
import { Sidebar } from '../sidebar/Sidebar'
import {
  waitForGmail,
  isEmailOpen,
  watchNavigation,
  setGmailMargin,
  scrapeEmailData,
  type EmailData,
} from './gmail'
import '../styles/content.css'

const SIDEBAR_WIDTH = 340

async function bootstrap() {
  await waitForGmail()

  // Guard against double-injection (e.g. script re-evaluated)
  if (document.getElementById('mailmind-root')) return

  const container = document.createElement('div')
  container.id = 'mailmind-root'
  document.body.appendChild(container)

  const root = ReactDOM.createRoot(container)

  function renderSidebar(emailOpen: boolean, emailData?: EmailData | null) {
    root.render(
      <React.StrictMode>
        <Sidebar
          emailOpen={emailOpen}
          emailData={emailData}
          onVisibilityChange={(visible) => setGmailMargin(visible ? SIDEBAR_WIDTH : 0)}
        />
      </React.StrictMode>
    )
  }

  const initialOpen = isEmailOpen()
  renderSidebar(initialOpen, initialOpen ? scrapeEmailData() : null)
  setGmailMargin(SIDEBAR_WIDTH)

  watchNavigation((open) => {
    renderSidebar(open, open ? scrapeEmailData() : null)
  })
}

bootstrap().catch((err) => console.error('[MailMind]', err))
