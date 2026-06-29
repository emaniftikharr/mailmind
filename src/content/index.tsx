import React from 'react'
import ReactDOM from 'react-dom/client'
import { Sidebar } from '../sidebar/Sidebar'
import '../styles/content.css'

const root = document.createElement('div')
root.id = 'mailmind-root'
document.body.appendChild(root)

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <Sidebar />
  </React.StrictMode>
)
