const WS_URL = import.meta.env.VITE_WS_URL || null

let ws = null
const listeners = new Set()
let retryDelay = 1000

export function subscribeWS(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

function dispatch(event) {
  listeners.forEach(fn => fn(event))
}

function connect() {
  if (!WS_URL) return

  ws = new WebSocket(WS_URL)

  ws.onopen = () => {
    retryDelay = 1000
    dispatch({ type: 'ws_connected' })
  }

  ws.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data)
      dispatch(event)
    } catch { /* ignore malformed messages */ }
  }

  ws.onclose = () => {
    dispatch({ type: 'ws_disconnected' })
    setTimeout(() => {
      retryDelay = Math.min(retryDelay * 2, 30000)
      connect()
    }, retryDelay)
  }

  ws.onerror = () => ws.close()
}

// Auto-connect on first import
connect()
