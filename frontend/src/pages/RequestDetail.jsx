import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { subscribeWS } from '../lib/websocket'
import ScoreBar from '../components/ScoreBar'

// ── Helpers ───────────────────────────────────────────────────────────────────

const SENTIMENT_COLORS = {
  confirmed:  'bg-green-400',
  declined:   'bg-red-500',
  hesitation: 'bg-amber-400',
  unclear:    'bg-gray-300',
}

const DONOR_STATUS_STYLES = {
  confirmed:     { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' },
  sent:          { bg: 'bg-blue-50',  text: 'text-blue-700',  border: 'border-blue-200'  },
  pending:       { bg: 'bg-gray-50',  text: 'text-gray-500',  border: 'border-gray-200'  },
  declined:      { bg: 'bg-red-50',   text: 'text-red-700',   border: 'border-red-200'   },
  amber:         { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' },
  no_response:   { bg: 'bg-gray-100', text: 'text-gray-500',  border: 'border-gray-200'  },
  ready_to_send: { bg: 'bg-blue-50',  text: 'text-blue-600',  border: 'border-blue-200'  },
}

const BG_COLORS = {
  'O Negative': '#b91c1c', 'O Positive': '#ef4444',
  'A Negative': '#1d4ed8', 'A Positive': '#3b82f6',
  'B Negative': '#7c3aed', 'B Positive': '#8b5cf6',
  'AB Negative':'#c2410c', 'AB Positive':'#f97316',
}

function initials(id) {
  return id.slice(-2).toUpperCase()
}

// ── Timeline ──────────────────────────────────────────────────────────────────

function Timeline({ entries }) {
  if (!entries.length) return <p className="text-xs text-on-surface-variant py-2">No interactions yet.</p>
  return (
    <div className="space-y-3">
      {entries.map(e => (
        <div key={e.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${
              e.direction === 'outbound' ? 'bg-secondary' : (SENTIMENT_COLORS[e.sentiment] || 'bg-outline')}`} />
            <div className="w-px flex-1 bg-outline-variant/30 mt-1" />
          </div>
          <div className="pb-3 min-w-0">
            <p className="text-xs font-semibold text-on-surface">
              {e.direction === 'outbound' ? 'Outreach sent' : 'Reply received'}
              {e.sentiment && <span className="font-normal text-on-surface-variant"> · {e.sentiment}</span>}
            </p>
            {e.message_body && (
              <p className="text-xs text-on-surface-variant mt-0.5 italic truncate max-w-[200px]">
                "{e.message_body.slice(0, 80)}{e.message_body.length > 80 ? '…' : ''}"
              </p>
            )}
            <p className="text-[11px] text-outline mt-0.5">
              {e.created_at ? new Date(e.created_at).toLocaleTimeString() : ''}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Donor Card ────────────────────────────────────────────────────────────────

function SmartDonorCard({ donor, requestId, onConfirm }) {
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()

  const st      = DONOR_STATUS_STYLES[donor.outreach_status] || DONOR_STATUS_STYLES.pending
  const bgColor = BG_COLORS[donor.blood_group] || '#6b7280'
  const scoreColor = donor.commitment_score >= 92 ? '#16a34a' : donor.commitment_score >= 80 ? '#d97706' : '#dc2626'

  return (
    <div className={`bg-surface-container-lowest border rounded-xl overflow-hidden hover:border-primary transition-all duration-200
      ${donor.hesitation_detected ? 'border-amber/60 ring-1 ring-amber/20' : 'border-outline-variant'}`}>

      <div className="p-4">
        <div className="flex gap-3">
          {/* Avatar — blood group badge instead of photo */}
          <div className="relative shrink-0">
            <div className="w-14 h-14 rounded-lg flex flex-col items-center justify-center text-white font-black text-xs"
              style={{ backgroundColor: bgColor }}>
              <span className="text-[10px] font-bold opacity-80 leading-none">{donor.blood_group?.split(' ')[0] || '?'}</span>
              <span className="text-[9px] opacity-70 leading-none">{donor.blood_group?.split(' ')[1] || ''}</span>
              <span className="text-base font-black leading-none mt-0.5">{initials(donor.donor_id)}</span>
            </div>
            {donor.rank === 1 && (
              <div className="absolute -top-1.5 -right-1.5 bg-secondary text-white text-[9px] font-black px-1.5 py-0.5 rounded-full border-2 border-white">
                TOP
              </div>
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex justify-between items-start gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <h4 className="font-bold text-on-surface text-sm font-mono">{donor.donor_id.slice(-12)}</h4>
                  {donor.is_primary && (
                    <span className="text-[10px] font-bold bg-primary/10 text-primary px-1.5 py-0.5 rounded-md">PRIMARY</span>
                  )}
                  {donor.is_standby && (
                    <span className="text-[10px] font-bold bg-blue-50 text-secondary px-1.5 py-0.5 rounded-md">STANDBY</span>
                  )}
                </div>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  {donor.total_donations} donation{donor.total_donations !== 1 ? 's' : ''}
                  {donor.lifetime_show_rate != null ? ` · ${(donor.lifetime_show_rate * 100).toFixed(0)}% show rate` : ''}
                </p>
              </div>
              <div className="text-right shrink-0">
                <div className="text-xl font-black tabular-nums" style={{ color: scoreColor }}>
                  {donor.commitment_score}%
                </div>
                <div className="text-[9px] text-on-surface-variant font-bold uppercase tracking-tighter">Match Score</div>
              </div>
            </div>

            {/* AI reason */}
            {donor.reasons?.length > 0 && (
              <div className="mt-2 p-2 bg-surface-container-low rounded-lg border border-outline-variant/50">
                <p className="text-xs text-on-surface leading-snug">
                  <span className="material-symbols-outlined text-[13px] text-secondary align-middle mr-1"
                    style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
                  <span className="font-bold text-secondary">Reason: </span>
                  {donor.reasons[0]}
                </p>
              </div>
            )}

            {/* Flags */}
            {donor.flags?.length > 0 && (
              <p className="text-xs text-amber mt-1.5">
                <span className="material-symbols-outlined text-[12px] align-middle mr-0.5">warning</span>
                {donor.flags[0]}
              </p>
            )}

            {/* Status badge */}
            <div className="mt-2 flex items-center justify-between">
              <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${st.bg} ${st.text} ${st.border}`}>
                {donor.outreach_status.replace(/_/g, ' ')}
              </span>
              <span className={`text-[11px] font-semibold ${donor.confidence === 'high' ? 'text-success' : donor.confidence === 'medium' ? 'text-amber' : 'text-on-surface-variant'}`}>
                {donor.confidence} confidence
              </span>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="mt-3 flex gap-2">
          {donor.outreach_status !== 'confirmed' && (
            <button
              onClick={() => onConfirm(donor.donor_id)}
              className="flex-1 py-2 bg-primary text-white font-bold text-xs rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[14px]">check_circle</span>
              Confirm
            </button>
          )}
          <button
            onClick={() => navigate(`/donors/${donor.donor_id}`)}
            className="flex-1 py-2 border border-outline-variant text-on-surface font-bold text-xs rounded-lg hover:bg-surface-container transition-colors flex items-center justify-center gap-1.5"
          >
            <span className="material-symbols-outlined text-[14px]">person</span>
            Profile
          </button>
          <button
            onClick={() => setExpanded(x => !x)}
            className="px-3 py-2 border border-outline-variant text-on-surface-variant text-xs rounded-lg hover:bg-surface-container transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">{expanded ? 'expand_less' : 'expand_more'}</span>
          </button>
        </div>
      </div>

      {/* Expanded score breakdown */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-outline-variant/30">
          <ScoreBar score={donor.commitment_score} signals={donor.signals || {}} />
        </div>
      )}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function RequestDetail({ onToast }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const [detail, setDetail]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [elapsed, setElapsed] = useState(0)

  const loadDetail = useCallback(async () => {
    try {
      const data = await api.getRequest(id)
      setDetail(data)
    } catch (e) {
      onToast('error', e.message)
    } finally {
      setLoading(false)
    }
  }, [id, onToast])

  useEffect(() => { loadDetail() }, [loadDetail])

  useEffect(() => {
    const unsub = subscribeWS(event => {
      if (event.request_id === id) loadDetail()
    })
    return unsub
  }, [id, loadDetail])

  // Elapsed timer (demo cosmetic)
  useEffect(() => {
    if (!detail) return
    const t = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(t)
  }, [detail])

  const confirm = async (donorId) => {
    try {
      await api.confirmRequest(id, donorId)
      onToast('success', 'Confirmed — feedback loop updated')
      loadDetail()
    } catch (e) { onToast('error', e.message) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="text-sm text-on-surface-variant flex items-center gap-2">
        <span className="material-symbols-outlined animate-pulse-slow">sync</span>
        Loading request…
      </div>
    </div>
  )
  if (!detail) return <div className="p-6 text-sm text-danger">Request not found</div>

  const { request: req, ranked_donors, timeline, ai_summary } = detail
  const days  = req.required_date
    ? Math.ceil((new Date(req.required_date) - new Date()) / 86400000)
    : null
  const bgColor = BG_COLORS[req.patient_blood_group] || '#6b7280'

  const hh = String(Math.floor(elapsed / 3600)).padStart(2, '0')
  const mm = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0')
  const ss = String(elapsed % 60).padStart(2, '0')

  return (
    <div className="flex flex-col min-h-full">
      {/* Active Request Header */}
      <div className="bg-primary text-white px-8 py-5 relative overflow-hidden sticky top-0 z-20">
        <div className="absolute right-0 top-0 opacity-10 pointer-events-none">
          <span className="material-symbols-outlined text-[120px]" style={{ fontVariationSettings: "'FILL' 1" }}>emergency</span>
        </div>
        <div className="flex justify-between items-center relative z-10 max-w-[1440px] mx-auto">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <button onClick={() => navigate(-1)} className="text-white/70 hover:text-white flex items-center gap-1 text-xs transition-colors">
                <span className="material-symbols-outlined text-[16px]">arrow_back</span>
                Back
              </button>
              <span className="bg-white/20 px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider">Active Request</span>
              <span className="text-white/70 font-mono text-xs">#{id.slice(-8)}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                req.status === 'confirmed' ? 'bg-green-500' : req.status === 'failed' ? 'bg-red-800' : 'bg-white/20'
              }`}>
                {req.status.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-6 mt-1">
              <div>
                <p className="text-white/60 text-[10px] uppercase tracking-wider font-semibold">Blood Type</p>
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-black text-xs"
                    style={{ backgroundColor: 'rgba(255,255,255,0.2)' }}>
                    {req.patient_blood_group?.charAt(0) || '?'}
                  </div>
                  <span className="text-xl font-black">{req.patient_blood_group || '?'}</span>
                </div>
              </div>
              <div className="w-px h-10 bg-white/25" />
              <div>
                <p className="text-white/60 text-[10px] uppercase tracking-wider font-semibold">Priority</p>
                <div className="flex items-center gap-1 font-bold text-secondary-fixed">
                  <span className="material-symbols-outlined text-[16px]">bolt</span>
                  {days !== null && days <= 3 ? 'URGENT' : 'ACTIVE'}
                </div>
              </div>
              <div className="w-px h-10 bg-white/25" />
              <div>
                <p className="text-white/60 text-[10px] uppercase tracking-wider font-semibold">Transfusion</p>
                <span className="text-base font-bold">
                  {days !== null
                    ? days < 0 ? `${Math.abs(days)}d overdue` : days === 0 ? 'Today' : `In ${days} day${days !== 1 ? 's' : ''}`
                    : 'Date TBD'}
                </span>
              </div>
              <div className="w-px h-10 bg-white/25" />
              <div>
                <p className="text-white/60 text-[10px] uppercase tracking-wider font-semibold">Ranked</p>
                <span className="text-base font-bold">{ranked_donors.length} Donors</span>
              </div>
            </div>
          </div>
          <div className="text-right">
            <p className="text-white/60 text-xs">Time Elapsed</p>
            <p className="font-mono text-2xl font-black">{hh}:{mm}:{ss}</p>
            {req.notes && <p className="text-white/60 text-xs mt-1">{req.notes}</p>}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 flex">
        <div className="flex-1 flex gap-6 p-6 max-w-[1440px] mx-auto w-full">

          {/* Left: Ranked Donors */}
          <div className="flex-1 flex flex-col gap-4">
            <div className="flex justify-between items-center shrink-0">
              <h3 className="text-lg font-semibold text-on-surface">
                Top Recommended Donors
              </h3>
              <div className="flex items-center gap-2 text-xs text-on-surface-variant">
                <span>Sort by:</span>
                <span className="text-primary font-bold">Match Score</span>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {ranked_donors.map(donor => (
                <SmartDonorCard
                  key={donor.donor_id}
                  donor={donor}
                  requestId={id}
                  onConfirm={confirm}
                />
              ))}
              {ranked_donors.length === 0 && (
                <div className="col-span-2 py-10 text-center text-sm text-on-surface-variant">
                  No eligible donors found for this blood type.
                </div>
              )}
            </div>
          </div>

          {/* Right sidebar */}
          <aside className="w-72 flex flex-col gap-4 shrink-0">

            {/* AI Case Summary */}
            <div className="bg-surface-container-low border border-outline-variant rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className="material-symbols-outlined text-secondary text-[18px]"
                  style={{ fontVariationSettings: "'FILL' 1" }}>psychology</span>
                <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">AI Case Summary</h4>
              </div>
              {ai_summary ? (
                <p className="text-sm text-on-surface leading-relaxed">{ai_summary}</p>
              ) : (
                <p className="text-sm text-on-surface-variant">
                  Deterministic engine selected {ranked_donors.length} compatible donors
                  for <span className="font-semibold">{req.patient_blood_group}</span>.
                  {req.match_time_seconds != null && ` Ranked in ${req.match_time_seconds}s.`}
                </p>
              )}
              <div className="mt-3 p-2 bg-secondary/5 rounded-lg border border-secondary/20">
                <p className="text-[11px] text-secondary">
                  <span className="font-bold">Note:</span> Scores are deterministic — 6 signals, no LLM. Blood compatibility is a hard gate.
                </p>
              </div>
            </div>

            {/* Quick Actions */}
            {req.status === 'open' && ranked_donors[0] && (
              <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 space-y-2">
                <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">Quick Actions</h4>
                <button
                  onClick={() => confirm(ranked_donors[0].donor_id)}
                  className="w-full py-2.5 text-sm font-bold rounded-lg bg-success text-white hover:opacity-90 flex items-center justify-center gap-2"
                >
                  <span className="material-symbols-outlined text-[16px]">check_circle</span>
                  Confirm Rank #1
                </button>
                <p className="text-xs text-on-surface-variant">Triggers feedback loop — memory updated immediately.</p>
              </div>
            )}

            {/* Timeline */}
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex-1">
              <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-3">Interaction Timeline</h4>
              <Timeline entries={timeline} />
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}
