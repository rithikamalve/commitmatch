import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { subscribeWS } from '../lib/websocket'

// ── Helpers ───────────────────────────────────────────────────────────────────

const BG_COLORS = {
  'O Negative': 'bg-red-700',   'O Positive': 'bg-red-500',
  'A Negative': 'bg-blue-700',  'A Positive': 'bg-blue-500',
  'B Negative': 'bg-violet-700','B Positive': 'bg-violet-500',
  'AB Negative':'bg-orange-700','AB Positive':'bg-orange-500',
}

const SEVERITY_RING = {
  critical: 'border-2 border-error shadow-lg shadow-error/20',
  medium:   'border border-amber',
  low:      'border border-success/50',
}

function daysUntil(d) {
  if (!d) return null
  return Math.ceil((new Date(d) - new Date()) / 86400000)
}

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ icon, label, value, sub, trend, trendUp, accent, children }) {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant p-6 rounded-xl flex flex-col justify-between min-h-[120px]">
      <div className="flex justify-between items-start mb-1">
        <span className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">{label}</span>
        <span className={`material-symbols-outlined text-[22px] ${accent || 'text-on-surface-variant'}`}>{icon}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className={`text-4xl font-black tabular-nums ${accent || 'text-on-surface'}`}>{value}</span>
        {trend && (
          <span className={`text-sm flex items-center ${trendUp ? 'text-error' : 'text-success'}`}>
            <span className="material-symbols-outlined text-[15px]">{trendUp ? 'trending_up' : 'trending_down'}</span>
            {trend}
          </span>
        )}
      </div>
      {children}
      {sub && <p className="text-sm text-on-surface-variant mt-2">{sub}</p>}
    </div>
  )
}

// ── New Request Modal ─────────────────────────────────────────────────────────

function NewMatchModal({ patients, onClose, onMatch }) {
  const [patientId, setPatientId] = useState('')
  const [date, setDate] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    if (!patientId) return
    setLoading(true)
    try { await onMatch(patientId, date, notes) }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-surface-container-lowest rounded-2xl shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
            <span className="material-symbols-outlined text-primary">bloodtype</span>
          </div>
          <div>
            <h2 className="text-base font-bold text-on-surface">New Blood Request</h2>
            <p className="text-xs text-on-surface-variant">CommitMatch ranks donors and begins outreach automatically.</p>
          </div>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Patient</label>
            <select value={patientId} onChange={e => setPatientId(e.target.value)}
              className="mt-1 w-full border border-outline-variant rounded-lg px-3 py-2 text-sm bg-surface focus:outline-none focus:border-primary">
              <option value="">Select patient…</option>
              {patients.map(p => (
                <option key={p.bridge_id} value={p.bridge_id}>
                  {p.bridge_blood_group} — {p.bridge_id.slice(-8)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Transfusion Date</label>
            <input type="date" value={date} onChange={e => setDate(e.target.value)}
              className="mt-1 w-full border border-outline-variant rounded-lg px-3 py-2 text-sm bg-surface focus:outline-none focus:border-primary" />
          </div>
          <div>
            <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Notes</label>
            <input type="text" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional"
              className="mt-1 w-full border border-outline-variant rounded-lg px-3 py-2 text-sm bg-surface focus:outline-none focus:border-primary" />
          </div>
        </div>
        <div className="flex gap-2 mt-5 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg border border-outline-variant hover:bg-surface-container">Cancel</button>
          <button onClick={submit} disabled={loading || !patientId}
            className="px-4 py-2 text-sm font-bold rounded-lg bg-primary text-white hover:opacity-90 disabled:opacity-50">
            {loading ? 'Matching…' : 'Find Donors'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Regional Map Placeholder ──────────────────────────────────────────────────

function RegionalMap({ shortages, requests }) {
  // Simulated hospital markers from real shortage data
  const markers = [
    { id: 'c1', x: '48%', y: '32%', severity: 'critical', label: 'NIMS Hospital',    sub: shortages[0]?.blood_group || 'O Negative', note: 'Critical shortage' },
    { id: 'c2', x: '28%', y: '58%', severity: 'medium',   label: 'Yashoda Secunderabad', sub: shortages[1]?.blood_group || 'AB Negative', note: 'Moderate supply' },
    { id: 'c3', x: '68%', y: '62%', severity: 'low',      label: 'Care Hospitals',   sub: 'B Positive', note: 'Stable supply' },
  ]

  return (
    <div className="relative flex-1 min-h-[420px] bg-[#0f1924] overflow-hidden rounded-b-xl">
      {/* City grid overlay */}
      <div className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />
      {/* District blobs */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute w-96 h-64 bg-[#1a2d45] rounded-full blur-3xl top-1/4 left-1/4 opacity-60" />
        <div className="absolute w-72 h-48 bg-[#1a2d35] rounded-full blur-3xl bottom-1/4 right-1/4 opacity-40" />
        <div className="absolute w-48 h-32 bg-[#2a1818] rounded-full blur-3xl top-[40%] left-[55%] opacity-50" />
      </div>

      {/* Hospital markers */}
      {markers.map(m => (
        <div key={m.id} className="absolute" style={{ left: m.x, top: m.y, transform: 'translate(-50%,-50%)' }}>
          {m.severity === 'critical' && (
            <div className="absolute -inset-6 bg-error/20 rounded-full blur-xl animate-pulse-slow pointer-events-none" />
          )}
          <div className={`flex items-center gap-2 bg-[#1b1b1c]/90 backdrop-blur-sm px-3 py-2 rounded-lg cursor-pointer hover:scale-105 transition-transform ${SEVERITY_RING[m.severity]}`}>
            <span className={`material-symbols-outlined text-[16px] ${m.severity === 'critical' ? 'text-error animate-pulse-slow' : m.severity === 'medium' ? 'text-amber' : 'text-success'}`}
              style={{ fontVariationSettings: "'FILL' 1" }}>
              {m.severity === 'critical' ? 'emergency' : 'local_hospital'}
            </span>
            <div>
              <p className="text-[11px] font-bold text-white leading-tight">{m.label}</p>
              <p className={`text-[10px] ${m.severity === 'critical' ? 'text-red-400' : m.severity === 'medium' ? 'text-amber' : 'text-green-400'}`}>{m.note} · {m.sub}</p>
            </div>
          </div>
        </div>
      ))}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex flex-col gap-1.5">
        {[
          { color: 'bg-error', label: 'Critical shortage' },
          { color: 'bg-amber', label: 'Moderate demand' },
          { color: 'bg-success', label: 'Stable supply' },
        ].map(l => (
          <div key={l.label} className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${l.color}`} />
            <span className="text-[10px] text-white/50">{l.label}</span>
          </div>
        ))}
      </div>

      {/* Map controls */}
      <div className="absolute bottom-4 right-4 flex flex-col gap-1.5">
        {['+', '−'].map(c => (
          <button key={c} className="w-8 h-8 bg-[#1b1b1c]/90 border border-white/10 rounded text-white/70 hover:text-white text-sm font-bold flex items-center justify-center transition-colors">
            {c}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function Dashboard({ onToast }) {
  const [requests, setRequests]   = useState([])
  const [patients, setPatients]   = useState([])
  const [shortages, setShortages] = useState([])
  const [health, setHealth]       = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [loading, setLoading]     = useState(true)
  const navigate   = useNavigate()
  const [params]   = useSearchParams()

  // Auto-open modal if ?new=1 (from sidebar "Urgent Request")
  useEffect(() => {
    if (params.get('new') === '1') setShowModal(true)
  }, [params])

  const loadData = useCallback(async () => {
    try {
      const [reqs, pts, sa, nh] = await Promise.all([
        api.getRequests(), api.getPatients(), api.getShortageAlerts(), api.getNetworkHealth(),
      ])
      setRequests(reqs); setPatients(pts); setShortages(sa); setHealth(nh)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadData() }, [loadData])

  useEffect(() => {
    const unsub = subscribeWS(event => {
      if (['confirmed','declined','amber_alert','standby_promoted','shortage_alert'].includes(event.type))
        loadData()
    })
    return unsub
  }, [loadData])

  const handleMatch = async (patientId, date, notes) => {
    try {
      const result = await api.createMatch(patientId, date || null, notes || null)
      setShowModal(false)
      onToast('success', `Match found in ${result.match_time_ms}ms — ${result.ranked_donors.length} donors ranked`)
      await loadData()
      navigate(`/requests/${result.request_id}`)
    } catch (e) { onToast('error', e.message) }
  }

  const open      = requests.filter(r => r.status === 'open')
  const confirmed = requests.filter(r => r.status === 'confirmed')
  const amber     = requests.filter(r => r.has_amber_alert)

  const activeCount   = health ? Math.round(health.total_donors * health.pct_active / 100) : 0
  const responseRate  = health ? health.pct_eligible : 0

  // Milestones: recent requests formatted as activity items
  const milestones = [...requests]
    .slice(0, 5)
    .map(r => ({
      id:        r.id,
      icon:      r.status === 'confirmed' ? 'celebration' : r.has_amber_alert ? 'warning' : 'emergency',
      iconBg:    r.status === 'confirmed' ? '#ffdad6' : r.has_amber_alert ? '#ffdfa0' : '#d4e3ff',
      iconColor: r.status === 'confirmed' ? '#af101a'  : r.has_amber_alert ? '#715300' : '#005faf',
      title:     r.status === 'confirmed' ? 'Match Confirmed' : r.has_amber_alert ? 'Amber Alert' : 'Active Request',
      sub:       `${r.patient_blood_group || '?'} · Patient ···${r.id.slice(-6)}`,
      time:      r.status === 'confirmed' ? 'Confirmed' : r.has_amber_alert ? 'Needs attention' : 'In progress',
    }))

  // AI insight: top shortage or a predictive note
  const topShortage = shortages[0]

  return (
    <div className="p-8 space-y-6 max-w-[1440px] mx-auto">
      {/* Hero KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon="priority_high" label="Active Requests" value={open.length}
          trend={open.length > 3 ? '+high' : undefined} trendUp={open.length > 3}
          accent="text-primary"
          sub={`${confirmed.length > 0 ? confirmed.length + ' confirmed' : 'Critical demand'} · ${amber.length} amber`}
        />
        <KpiCard
          icon="diversity_3" label="Available Donors" value={activeCount.toLocaleString()}
          accent="text-on-surface"
          sub={`${health?.total_donors?.toLocaleString() || '…'} total in network`}
        >
          <span className="text-sm text-success flex items-center gap-1 mt-1">
            <span className="material-symbols-outlined text-[15px]">verified</span>
            Active &amp; ready
          </span>
        </KpiCard>
        <KpiCard
          icon="speed" label="Eligibility Rate" value={`${responseRate}%`}
          accent="text-on-surface"
          sub="Target: 70%"
        >
          <div className="w-full bg-surface-container h-1.5 rounded-full mt-2 overflow-hidden">
            <div className="bg-secondary h-full rounded-full" style={{ width: `${Math.min(100, responseRate)}%` }} />
          </div>
        </KpiCard>
        <KpiCard
          icon="rebase_edit" label="Live Matches" value={confirmed.length}
          accent="text-primary"
          sub="Currently confirmed"
        >
          {confirmed.length > 0 && (
            <div className="flex -space-x-2 mt-1">
              {[0,1,2].map(i => (
                <div key={i} className="w-6 h-6 rounded-full bg-primary-fixed border-2 border-surface-container-lowest" />
              ))}
            </div>
          )}
        </KpiCard>
      </div>

      {/* Bento Grid */}
      <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(12, minmax(0, 1fr))' }}>

        {/* Left: Regional Supply Map */}
        <div className="col-span-12 xl:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden flex flex-col shadow-sm">
          <div className="px-6 py-4 border-b border-outline-variant flex justify-between items-center shrink-0">
            <div>
              <h3 className="text-xl font-semibold text-on-surface">Regional Supply Map</h3>
              <p className="text-sm text-on-surface-variant">Demand vs Supply · Hyderabad</p>
            </div>
            <div className="flex gap-2 items-center">
              {shortages.length > 0 && (
                <span className="px-3 py-1 bg-error-container text-on-error-container text-xs font-semibold rounded-full flex items-center gap-1.5">
                  <span className="w-2 h-2 bg-error rounded-full animate-pulse-slow" />
                  {shortages.filter(s => s.severity === 'critical').length} Critical
                </span>
              )}
              <span className="px-3 py-1 bg-surface-container text-on-surface-variant text-xs font-semibold rounded-full">
                Hyderabad
              </span>
            </div>
          </div>
          <RegionalMap shortages={shortages} requests={open} />
        </div>

        {/* Right column */}
        <div className="col-span-12 xl:col-span-4 space-y-6">

          {/* AI Predictive Insight */}
          <div className="p-6 rounded-xl relative overflow-hidden shadow-xl"
            style={{ backgroundColor: '#1e2530', borderLeft: '4px solid #f8bd2a' }}>
            <div className="absolute top-0 right-0 opacity-10 pointer-events-none select-none">
              <span className="material-symbols-outlined" style={{ fontSize: 100 }}>psychology</span>
            </div>
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-3">
                <span className="material-symbols-outlined text-[18px]"
                  style={{ color: '#f8bd2a', fontVariationSettings: "'FILL' 1" }}>bolt</span>
                <span className="text-xs font-bold uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.55)' }}>
                  AI Predictive Insight
                </span>
              </div>

              {topShortage ? (
                <>
                  <h3 className="text-xl font-bold text-white mb-2">
                    {topShortage.blood_group} Shortage Detected
                  </h3>
                  <p className="text-sm mb-4 leading-relaxed" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    <span className="font-bold" style={{ color: '#f8bd2a' }}>{topShortage.city_cluster}</span> is flagging a
                    {topShortage.severity === 'critical' ? ' critical' : ' moderate'} shortage.{' '}
                    {topShortage.eligible_donor_count} eligible donor{topShortage.eligible_donor_count !== 1 ? 's' : ''} available
                    vs {topShortage.active_patient_count} patient{topShortage.active_patient_count !== 1 ? 's' : ''} needing.
                  </p>
                  <div className="p-3 rounded-lg border mb-4"
                    style={{ backgroundColor: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)' }}>
                    <div className="flex justify-between items-center text-xs mb-1.5">
                      <span style={{ color: 'rgba(255,255,255,0.5)' }}>Supply gap</span>
                      <span className="font-bold" style={{ color: '#f8bd2a' }}>
                        {topShortage.active_patient_count - topShortage.eligible_donor_count > 0
                          ? `−${topShortage.active_patient_count - topShortage.eligible_donor_count} units`
                          : 'Balanced'}
                      </span>
                    </div>
                    <div className="w-full h-1 rounded-full" style={{ backgroundColor: 'rgba(255,255,255,0.1)' }}>
                      <div className="h-full rounded-full" style={{
                        backgroundColor: '#f8bd2a',
                        width: `${Math.min(100, (topShortage.eligible_donor_count / Math.max(1, topShortage.active_patient_count)) * 100)}%`,
                      }} />
                    </div>
                  </div>
                  <button
                    onClick={() => setShowModal(true)}
                    className="w-full font-bold text-sm py-3 rounded-lg hover:opacity-90 transition-opacity"
                    style={{ backgroundColor: '#f8bd2a', color: '#261a00' }}
                  >
                    Mobilize {topShortage.blood_group} Donors
                  </button>
                </>
              ) : (
                <>
                  <h3 className="text-xl font-bold text-white mb-2">Supply Balanced</h3>
                  <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    No critical shortages detected. Network is healthy across all blood groups in Hyderabad.
                  </p>
                  <button
                    onClick={() => setShowModal(true)}
                    className="w-full font-bold text-sm py-3 rounded-lg hover:opacity-90 transition-opacity"
                    style={{ backgroundColor: '#f8bd2a', color: '#261a00' }}
                  >
                    Create New Request
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Recent Milestones */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm">
            <div className="px-5 py-4 border-b border-outline-variant">
              <h3 className="text-sm font-semibold text-on-surface">Recent Milestones</h3>
            </div>
            <div className="divide-y divide-outline-variant/40">
              {loading ? (
                <div className="px-5 py-4 text-sm text-on-surface-variant">Loading…</div>
              ) : milestones.length === 0 ? (
                <div className="px-5 py-6 text-center">
                  <span className="material-symbols-outlined text-[28px] text-on-surface-variant">bloodtype</span>
                  <p className="text-sm text-on-surface-variant mt-1">No requests yet.</p>
                  <button onClick={() => setShowModal(true)} className="mt-2 text-sm text-primary font-semibold hover:underline">
                    Create first →
                  </button>
                </div>
              ) : (
                milestones.map(m => (
                  <div key={m.id}
                    onClick={() => navigate(`/requests/${m.id}`)}
                    className="px-4 py-3 flex gap-3 hover:bg-surface-container-low transition-colors cursor-pointer">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                      style={{ backgroundColor: m.iconBg }}>
                      <span className="material-symbols-outlined text-[18px]"
                        style={{ color: m.iconColor, fontVariationSettings: "'FILL' 1" }}>{m.icon}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-start">
                        <p className="text-[13px] font-semibold text-on-surface">{m.title}</p>
                        <span className="text-xs text-on-surface-variant ml-2 shrink-0">{m.time}</span>
                      </div>
                      <p className="text-xs text-on-surface-variant truncate">{m.sub}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
            <button
              onClick={() => navigate('/analytics')}
              className="w-full py-3 border-t border-outline-variant text-xs font-semibold text-primary hover:bg-surface-container-low transition-colors"
            >
              View All Operations
            </button>
          </div>
        </div>
      </div>

      {showModal && (
        <NewMatchModal patients={patients} onClose={() => setShowModal(false)} onMatch={handleMatch} />
      )}
    </div>
  )
}
