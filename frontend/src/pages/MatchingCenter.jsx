import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export default function MatchingCenter({ onToast }) {
  const [requests, setRequests]   = useState([])
  const [patients, setPatients]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [matching, setMatching]   = useState(false)
  const [patientId, setPatientId] = useState('')
  const [date, setDate]           = useState('')
  const [notes, setNotes]         = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([api.getRequests(), api.getPatients()])
      .then(([reqs, pts]) => { setRequests(reqs); setPatients(pts) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // Auto-redirect if there's exactly one open request
  useEffect(() => {
    const open = requests.filter(r => r.status === 'open' || r.status === 'confirmed')
    if (open.length === 1) navigate(`/requests/${open[0].id}`, { replace: true })
  }, [requests, navigate])

  const handleMatch = async () => {
    if (!patientId) return
    setMatching(true)
    try {
      const result = await api.createMatch(patientId, date || null, notes || null)
      onToast('success', `Match found — ${result.ranked_donors.length} donors ranked`)
      navigate(`/requests/${result.request_id}`)
    } catch (e) {
      onToast('error', e.message)
    } finally {
      setMatching(false)
    }
  }

  const open = requests.filter(r => r.status === 'open')

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-sm text-on-surface-variant">
      Loading…
    </div>
  )

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-on-surface">Smart Matching Center</h1>
        <p className="text-sm text-on-surface-variant mt-0.5">
          Deterministic donor ranking — 6 signals, no LLM
        </p>
      </div>

      <div className="grid grid-cols-5 gap-6">
        {/* Left: Create new match */}
        <div className="col-span-3 bg-white border border-outline-variant rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
              <span className="material-symbols-outlined text-primary"
                style={{ fontVariationSettings: "'FILL' 1" }}>clinical_notes</span>
            </div>
            <div>
              <h2 className="font-bold text-on-surface">New Match Request</h2>
              <p className="text-xs text-on-surface-variant">CommitMatch ranks donors and begins outreach automatically</p>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Patient</label>
              <select value={patientId} onChange={e => setPatientId(e.target.value)}
                className="mt-1 w-full border border-outline-variant rounded-lg px-3 py-2.5 text-sm bg-surface focus:outline-none focus:border-primary">
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
                className="mt-1 w-full border border-outline-variant rounded-lg px-3 py-2.5 text-sm bg-surface focus:outline-none focus:border-primary" />
            </div>
            <div>
              <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Notes</label>
              <input type="text" value={notes} onChange={e => setNotes(e.target.value)} placeholder="Optional"
                className="mt-1 w-full border border-outline-variant rounded-lg px-3 py-2.5 text-sm bg-surface focus:outline-none focus:border-primary" />
            </div>
          </div>

          <button
            onClick={handleMatch}
            disabled={!patientId || matching}
            className="w-full py-3 bg-primary text-white font-bold rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]"
              style={{ fontVariationSettings: "'FILL' 1" }}>
              {matching ? 'sync' : 'search'}
            </span>
            {matching ? 'Matching…' : 'Find Best Donors'}
          </button>

          <div className="pt-2 border-t border-outline-variant/50">
            <p className="text-xs text-on-surface-variant text-center">
              Scores are deterministic · Blood compatibility is a hard gate
            </p>
          </div>
        </div>

        {/* Right: Active requests */}
        <div className="col-span-2 space-y-3">
          <h2 className="text-xs font-semibold text-on-surface-variant uppercase tracking-wide">
            Active Requests ({open.length})
          </h2>
          {open.length === 0 ? (
            <div className="bg-white border border-outline-variant rounded-xl p-5 text-center">
              <span className="material-symbols-outlined text-[28px] text-on-surface-variant">bloodtype</span>
              <p className="text-sm text-on-surface-variant mt-1">No open requests</p>
            </div>
          ) : (
            open.map(r => (
              <div
                key={r.id}
                onClick={() => navigate(`/requests/${r.id}`)}
                className="bg-white border border-outline-variant rounded-xl p-4 cursor-pointer hover:border-primary hover:shadow-md transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-black text-white px-2.5 py-1 rounded-lg"
                      style={{ backgroundColor: '#af101a' }}>
                      {r.patient_blood_group || '?'}
                    </span>
                    <span className="text-xs font-mono text-on-surface-variant">···{r.id.slice(-6)}</span>
                  </div>
                  {r.has_amber_alert && (
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: '#fef3c7', color: '#92400e' }}>⚠ Amber</span>
                  )}
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-xs text-on-surface-variant">
                    {r.top_donor ? `Top score: ${r.top_donor.commitment_score}` : 'Awaiting match'}
                  </span>
                  <span className="text-xs text-primary font-semibold">Open →</span>
                </div>
              </div>
            ))
          )}

          {requests.filter(r => r.status === 'confirmed').length > 0 && (
            <>
              <h2 className="text-xs font-semibold text-on-surface-variant uppercase tracking-wide pt-2">
                Confirmed ({requests.filter(r => r.status === 'confirmed').length})
              </h2>
              {requests.filter(r => r.status === 'confirmed').map(r => (
                <div key={r.id}
                  onClick={() => navigate(`/requests/${r.id}`)}
                  className="bg-green-50 border border-green-200 rounded-xl p-4 cursor-pointer hover:shadow-md transition-all">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-black text-white px-2.5 py-1 rounded-lg bg-green-600">
                        {r.patient_blood_group || '?'}
                      </span>
                      <span className="text-xs font-mono text-on-surface-variant">···{r.id.slice(-6)}</span>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-green-100 text-green-700">✓ Done</span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
