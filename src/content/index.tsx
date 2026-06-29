import React from 'react'
import ReactDOM from 'react-dom/client'
import { Sidebar } from '../sidebar/Sidebar'
import { waitForGmail, isEmailOpen, watchNavigation, setGmailMargin } from './gmail'
import '../styles/content.css'

const SIDEBAR_WIDTH = 320

async function bootstrap() {
  await waitForGmail()

  // Guard against double-injection (e.g. script re-evaluated)
  if (document.getElementById('mailmind-root')) return

  const container = document.createElement('div')
  container.id = 'mailmind-root'
  document.body.appendChild(container)

  const root = ReactDOM.createRoot(container)

  function renderSidebar(emailOpen: boolean) {
    root.render(
      <React.StrictMode>
        <Sidebar
          emailOpen={emailOpen}
          onVisibilityChange={(visible) => setGmailMargin(visible ? SIDEBAR_WIDTH : 0)}
        />
      </React.StrictMode>
    )
  }

  renderSidebar(isEmailOpen())
  setGmailMargin(SIDEBAR_WIDTH) // sidebar starts open

  watchNavigation(renderSidebar)
}

bootstrap().catch((err) => console.error('[MailMind]', err))
