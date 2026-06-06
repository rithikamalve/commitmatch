import { BrowserRouter, Routes, Route, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import Dashboard from './pages/Dashboard'
import RequestDetail from './pages/RequestDetail'
import MatchingCenter from './pages/MatchingCenter'
import Analytics from './pages/Analytics'
import DonorProfile from './pages/DonorProfile'
import Donors from './pages/Donors'
import { subscribeWS } from './lib/websocket'

function Sidebar({ onUrgentRequest }) {
  const location = useLocation()

  const nav = [
    { to: '/',          match: ['/'],                icon: 'dashboard',      label: 'Executive Overview'    },
    { to: '/matching',  match: ['/matching','/requests'], icon: 'clinical_notes', label: 'Smart Matching Center' },
    { to: '/donors',    match: ['/donors'],          icon: 'groups',         label: 'Donor Intelligence'    },
    { to: '/analytics', match: ['/analytics'],       icon: 'analytics',      label: 'Analytics'             },
  ]

  return (
    <aside className="flex flex-col h-screen w-64 shrink-0 z-40" style={{ backgroundColor: '#303030' }}>
      {/* Logo */}
      <div className="px-4 py-5 flex items-center gap-3">
        <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-white text-[22px]"
            style={{ fontVariationSettings: "'FILL' 1" }}>
            water_drop
          </span>
        </div>
        <div>
          <h2 className="text-white font-black tracking-tight text-[15px] leading-tight">CommitMatch</h2>
          <p className="text-white/50 text-xs">Blood Warriors</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-2 space-y-0.5">
        {nav.map(item => {
          const isActive = item.match.some(prefix =>
            prefix === '/' ? location.pathname === '/' : location.pathname.startsWith(prefix)
          )
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={() =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-semibold tracking-wide transition-all duration-100 ${
                  isActive
                    ? 'bg-primary text-white scale-95'
                    : 'text-white/60 hover:text-white/90 hover:bg-white/5'
                }`
              }
            >
              <span
                className="material-symbols-outlined text-[20px]"
                style={isActive ? { fontVariationSettings: "'FILL' 1" } : {}}
              >
                {item.icon}
              </span>
              {item.label}
            </NavLink>
          )
        })}
      </nav>

      {/* Urgent Request CTA */}
      <div className="px-3 mb-3">
        <button
          onClick={onUrgentRequest}
          className="w-full bg-primary py-3 rounded-lg text-white font-semibold text-[13px] flex items-center justify-center gap-2 hover:opacity-90 active:scale-95 transition-all"
        >
          <span className="material-symbols-outlined text-[18px]">add_alert</span>
          Urgent Request
        </button>
      </div>

      {/* Footer links */}
      <div className="px-3 pb-4 border-t border-white/10 pt-3 space-y-0.5">
        <a className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-white/50 hover:text-white/80 hover:bg-white/5 transition-colors" href="#">
          <span className="material-symbols-outlined text-[16px]">check_circle</span>
          System Status
        </a>
        <a className="flex items-center gap-3 px-3 py-2 rounded-lg text-xs text-white/50 hover:text-white/80 hover:bg-white/5 transition-colors" href="#">
          <span className="material-symbols-outlined text-[16px]">help</span>
          Support
        </a>
      </div>
    </aside>
  )
}

function TopHeader() {
  return (
    <header className="h-16 flex justify-between items-center px-8 bg-surface border-b border-outline-variant sticky top-0 z-30 shrink-0">
      {/* Search */}
      <div className="relative w-64">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">search</span>
        <input
          className="w-full bg-surface-container-low border-none rounded-full pl-10 pr-4 py-1.5 text-sm focus:ring-1 focus:ring-primary outline-none"
          placeholder="Search operations…"
          type="text"
        />
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1 pr-4 border-r border-outline-variant">
          <button className="relative p-2 text-on-surface-variant hover:bg-surface-container rounded-lg transition-colors">
            <span className="material-symbols-outlined">notifications</span>
            <span className="absolute top-2 right-2 w-2 h-2 bg-primary rounded-full ring-2 ring-surface"></span>
          </button>
          <button className="p-2 text-on-surface-variant hover:bg-surface-container rounded-lg transition-colors">
            <span className="material-symbols-outlined">settings</span>
          </button>
        </div>
        <div className="flex items-center gap-2.5">
          <div className="text-right hidden sm:block">
            <p className="text-[13px] font-semibold text-on-surface leading-tight">Coordinator</p>
            <p className="text-xs text-on-surface-variant">Blood Warriors</p>
          </div>
          <div className="w-9 h-9 rounded-full bg-primary/10 border border-outline-variant flex items-center justify-center">
            <span className="material-symbols-outlined text-primary text-[22px]"
              style={{ fontVariationSettings: "'FILL' 1" }}>account_circle</span>
          </div>
        </div>
      </div>
    </header>
  )
}

function Toast({ toasts }) {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end">
      {toasts.map(t => (
        <div
          key={t.id}
          className={`px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white max-w-xs
            ${t.type === 'amber'   ? 'bg-amber' :
              t.type === 'success' ? 'bg-success' :
              t.type === 'error'   ? 'bg-danger' : 'bg-[#303030]'}`}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}

function AppShell({ addToast }) {
  const navigate = useNavigate()

  const handleUrgentRequest = () => navigate('/matching')

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar onUrgentRequest={handleUrgentRequest} />
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <TopHeader />
        <main className="flex-1 overflow-y-auto bg-background">
          <Routes>
            <Route path="/"              element={<Dashboard onToast={addToast} />} />
            <Route path="/matching"      element={<MatchingCenter onToast={addToast} />} />
            <Route path="/requests/:id"  element={<RequestDetail onToast={addToast} />} />
            <Route path="/analytics"     element={<Analytics />} />
            <Route path="/donors"        element={<Donors />} />
            <Route path="/donors/:id"    element={<DonorProfile />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

function App() {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((type, message) => {
    const id = Date.now()
    setToasts(t => [...t, { id, type, message }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000)
  }, [])

  useEffect(() => {
    const unsub = subscribeWS(event => {
      if (event.type === 'confirmed')
        addToast('success', `✓ Donor confirmed donation`)
      else if (event.type === 'amber_alert')
        addToast('amber', `⚠ Hesitation detected — amber alert`)
      else if (event.type === 'declined')
        addToast('error', `✗ Declined — standby promoting`)
      else if (event.type === 'standby_promoted')
        addToast('default', `↑ Standby promoted`)
    })
    return unsub
  }, [addToast])

  return (
    <BrowserRouter>
      <AppShell addToast={addToast} />
      <Toast toasts={toasts} />
    </BrowserRouter>
  )
}

export default App
