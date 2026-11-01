import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'
import { captureInstallPrompt } from './lib/installEvents.js'

captureInstallPrompt()

// Links shared from the old site (/evento/<id>) open the same market.
const legacyLink = window.location.pathname.match(/^\/evento\/([^/]+)/)
if (legacyLink) window.history.replaceState(null, '', '/#mercato=' + legacyLink[1])

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
