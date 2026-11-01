import { useState } from 'react'
import Icon from './Icon.jsx'
import Sheet from './Sheet.jsx'

// How to add Fuori to the Home screen where the browser has no one-tap install.
export function InstallSteps({ platform }) {
  const [copied, setCopied] = useState(false)
  if (platform === 'installed') return <p className="install-ok"><Icon name="check" size={16} strokeWidth={2.6} />Fuori è già sulla tua schermata Home.</p>
  if (platform === 'ios') {
    return (
      <ol className="install-steps">
        <li><span className="step-n">1</span><span>Tocca il tasto <b>Condividi</b> <span className="key" aria-label="Condividi"><Icon name="upload" size={15} strokeWidth={2} /></span>. Con iOS 26 lo trovi nel menu <b>•••</b> accanto all'indirizzo.</span></li>
        <li><span className="step-n">2</span><span>Scegli <b>Aggiungi alla schermata Home</b>. Se non lo vedi, scorri il menu verso il basso.</span></li>
        <li><span className="step-n">3</span><span>Lascia attivo <b>Apri come web app</b> e tocca <b>Aggiungi</b>.</span></li>
      </ol>
    )
  }
  if (platform === 'android-manual') {
    return (
      <ol className="install-steps">
        <li><span className="step-n">1</span><span>Apri il menu del browser <span className="key"><Icon name="dots" size={15} strokeWidth={2.4} /></span>, in alto o in basso a destra.</span></li>
        <li><span className="step-n">2</span><span>Tocca <b>Installa app</b> oppure <b>Aggiungi a schermata Home</b>.</span></li>
        <li><span className="step-n">3</span><span>Conferma con <b>Installa</b>.</span></li>
      </ol>
    )
  }
  if (platform === 'inapp') {
    const copy = async () => {
      try { await navigator.clipboard.writeText(window.location.origin + '/'); setCopied(true) } catch { setCopied(false) }
    }
    return (
      <div className="install-inapp">
        <p>Sei nel browser interno di un'altra app (Instagram, Facebook…), che non permette di installare. Apri Fuori nel browser del telefono: tocca <b>•••</b> e scegli <b>Apri nel browser</b>, poi installala da lì.</p>
        <button type="button" className="btn-secondary" onClick={copy}>{copied ? 'Link copiato' : 'Copia il link di Fuori'}</button>
      </div>
    )
  }
  return <p className="note">Sul computer: in Chrome o Edge tocca l'icona di installazione nella barra dell'indirizzo. Oppure apri Fuori dal telefono e installala lì.</p>
}

export function InstallSheet({ platform, onClose }) {
  return (
    <Sheet title="Fuori sulla schermata Home" onClose={onClose}>
      <p className="note" style={{ marginTop: -6 }}>Bastano tre tocchi. Niente store, niente account: si apre come un'app.</p>
      <InstallSteps platform={platform} />
    </Sheet>
  )
}

const COPY = {
  save: ['Salvato. Vuoi Fuori sul telefono?', 'Aggiungila alla schermata Home: ritrovi i mercatini salvati con un tocco.'],
  open: ['Mettiti Fuori in tasca', 'Si apre dalla schermata Home come un\'app. Gratis, senza store, occupa pochissimo.'],
}

// The invitation: above the tabs, never a modal, always with "Non ora".
export function InstallBanner({ trigger, onInstall, onDismiss }) {
  const [title, text] = COPY[trigger] || COPY.open
  return (
    <div className="install-banner" role="dialog" aria-label="Installa Fuori">
      <img src="/icons/icon-192.png" alt="" width="44" height="44" />
      <div className="install-text"><strong>{title}</strong><span>{text}</span></div>
      <div className="install-actions">
        <button type="button" className="btn-primary" onClick={onInstall}>Installa</button>
        <button type="button" className="link" onClick={onDismiss}>Non ora</button>
      </div>
    </div>
  )
}
