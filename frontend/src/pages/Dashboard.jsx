import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Tooltip, Popup } from 'react-leaflet'
import { api } from '../lib/api'
import { subscribeWS } from '../lib/websocket'

// ── Helpers ───────────────────────────────────────────────────────────────────

const BG_COLORS = {
  'O Negative': 'bg-red-700',   'O Positive': 'bg-red-500',
  'A Negative': 'bg-blue-700',  'A Positive': 'bg-blue-500',
  'B Negative': 'bg-violet-700','B Positive': 'bg-violet-500',
  'AB Negative':'bg-orange-700','AB Positive':'bg-orange-500',
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
              {[...patients]
                .sort((a, b) => {
                  const rarity = ['AB Negative','O Negative','AB Positive','B Negative','A Negative','O Positive','B Positive','A Positive']
                  return (rarity.indexOf(a.bridge_blood_group) + 1 || 99) - (rarity.indexOf(b.bridge_blood_group) + 1 || 99)
                })
                .map(p => (
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

// ── Regional Map (Leaflet + OpenStreetMap) ─────────────────────────────────────

const SEVERITY_COLOR = { critical: '#ef4444', medium: '#f59e0b', low: '#22c55e' }

const HOSPITALS = [
  { pos: [17.4128, 78.4069], name: 'NIMS Hospital',          shortageIdx: 0 },
  { pos: [17.4416, 78.4982], name: 'Yashoda Secunderabad',   shortageIdx: 1 },
  { pos: [17.4239, 78.4429], name: 'Care Hospitals',         shortageIdx: 2 },
  { pos: [17.3850, 78.4867], name: 'Gandhi Hospital',        shortageIdx: -1 },
  { pos: [17.4374, 78.4487], name: 'Apollo Jubilee Hills',   shortageIdx: -1 },
]

const DONOR_CLUSTERS = [
  { pos: [17.4124, 78.4482], area: 'Banjara Hills',  count: 48 },
  { pos: [17.4329, 78.4072], area: 'Jubilee Hills',  count: 35 },
  { pos: [17.4344, 78.5013], area: 'Secunderabad',   count: 72 },
  { pos: [17.4849, 78.4138], area: 'Kukatpally',     count: 54 },
  { pos: [17.3474, 78.5527], area: 'LB Nagar',       count: 31 },
  { pos: [17.5100, 78.3960], area: 'Bachupally',     count: 22 },
  { pos: [17.3616, 78.4747], area: 'Mehdipatnam',    count: 19 },
]

function RegionalMap({ shortages, requests }) {
  return (
    <div className="relative overflow-hidden rounded-b-xl" style={{ height: 420 }}>
      <MapContainer
        center={[17.405, 78.475]}
        zoom={12}
        style={{ height: 420, width: '100%' }}
        scrollWheelZoom={false}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OSM &copy; CARTO'
          subdomains="abcd"
          maxZoom={19}
        />

        {/* Donor cluster rings */}
        {DONOR_CLUSTERS.map(c => (
          <CircleMarker
            key={c.area}
            center={c.pos}
            radius={Math.sqrt(c.count) * 1.8}
            pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.18, weight: 1 }}
          >
            <Tooltip direction="top">
              <strong>{c.area}</strong> — {c.count} donors
            </Tooltip>
          </CircleMarker>
        ))}

        {/* Hospital markers — outer glow ring + inner dot */}
        {HOSPITALS.map(h => {
          const s = shortages[h.shortageIdx] || null
          const severity = s?.severity || (h.shortageIdx === -1 ? 'low' : 'medium')
          const color = SEVERITY_COLOR[severity]
          return (
            <CircleMarker
              key={h.name}
              center={h.pos}
              radius={severity === 'critical' ? 14 : 10}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.75, weight: 2 }}
            >
              <Tooltip direction="top" permanent={false}>
                <div style={{ minWidth: 130 }}>
                  <strong>{h.name}</strong><br />
                  {s ? (
                    <span>{s.blood_group} · <span style={{ color }}>{s.severity}</span> shortage</span>
                  ) : (
                    <span style={{ color: '#22c55e' }}>Supply stable</span>
                  )}
                </div>
              </Tooltip>
              <Popup>
                <div style={{ fontSize: 12, lineHeight: 1.7, minWidth: 170 }}>
                  <strong style={{ fontSize: 13 }}>{h.name}</strong><br />
                  {s ? (
                    <>Blood group: <strong>{s.blood_group}</strong><br />
                    Severity: <strong style={{ color }}>{s.severity}</strong><br />
                    Donors: {s.eligible_donor_count} · Patients: {s.active_patient_count}</>
                  ) : (
                    <span style={{ color: '#22c55e' }}>No active shortage</span>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-[1000] flex flex-col gap-1.5 bg-black/70 backdrop-blur-sm rounded-lg px-3 py-2.5 pointer-events-none">
        {[
          { color: '#ef4444', label: 'Critical shortage' },
          { color: '#f59e0b', label: 'Moderate demand'  },
          { color: '#22c55e', label: 'Stable supply'     },
          { color: '#3b82f6', label: 'Donor cluster'     },
        ].map(l => (
          <div key={l.label} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: l.color }} />
            <span className="text-[10px] text-white/60">{l.label}</span>
          </div>
        ))}
      </div>

      {requests.length > 0 && (
        <div className="absolute top-3 right-3 z-[1000] flex items-center gap-1.5 bg-black/70 backdrop-blur-sm rounded-full px-3 py-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-error animate-pulse" />
          <span className="text-[11px] font-semibold text-white">{requests.length} active request{requests.length !== 1 ? 's' : ''}</span>
        </div>
      )}
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
      if (['confirmed','declined','amber_alert','standby_promoted','shortage_alert','outreach_sent','standby_alerted'].includes(event.type))
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

  // Milestones: sort amber → open → confirmed, then by recency
  const urgencyRank = r => r.has_amber_alert ? 0 : r.status === 'open' ? 1 : 2
  const milestones = [...requests]
    .sort((a, b) => urgencyRank(a) - urgencyRank(b) || (b.created_at || '').localeCompare(a.created_at || ''))
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
