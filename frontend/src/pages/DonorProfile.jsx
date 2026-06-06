import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import ScoreBar from '../components/ScoreBar'

const CONFIDENCE_STYLE = {
  high:    'bg-green-50 text-green-700 border-green-200',
  medium:  'bg-amber-50 text-amber-700 border-amber-200',
  low:     'bg-red-50 text-red-600 border-red-200',
  unknown: 'bg-gray-50 text-gray-500 border-gray-200',
}

const PRIORITY_LABELS = {
  donate_now:   { label: 'Donate Now',    color: 'bg-green-500 text-white' },
  window_soon:  { label: 'Window Soon',   color: 'bg-amber-500 text-white' },
  not_ready:    { label: 'Not Ready Yet', color: 'bg-gray-200 text-gray-600' },
  unknown:      { label: 'Unknown',       color: 'bg-gray-100 text-gray-500' },
}

function EngagementBadge({ engagement }) {
  if (!engagement) return null
  const pl = PRIORITY_LABELS[engagement.priority_label] || PRIORITY_LABELS.unknown
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${pl.color}`}>
        {pl.label}
      </span>
      {engagement.days_until_window !== null && engagement.days_until_window !== undefined && (
        <span className="text-xs text-on-surface-variant">
          {engagement.days_until_window >= 0
            ? `next window in ${engagement.days_until_window} day(s)`
            : `window opened ${Math.abs(engagement.days_until_window)}d ago`}
        </span>
      )}
      <span className={`text-xs border px-2 py-1 rounded-full ${CONFIDENCE_STYLE[engagement.confidence] || CONFIDENCE_STYLE.unknown}`}>
        {engagement.confidence} confidence
      </span>
    </div>
  )
}

export default function DonorProfile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getDonorScore(id)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="p-6 text-sm text-on-surface-variant">Loading…</div>
  if (error)   return <div className="p-6 text-sm text-danger">{error}</div>
  if (!data)   return null

  const { commitment_score, confidence, signals, reasons, flags, engagement,
          blood_group, eligibility_status, total_donations,
          lifetime_show_rate, memory_summary } = data

  const scoreColor = commitment_score >= 92 ? 'text-green-600' :
                     commitment_score >= 80 ? 'text-amber-600' : 'text-red-500'

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-5">
      <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-on-surface-variant hover:text-on-surface">
        <span className="material-symbols-outlined text-[16px]">arrow_back</span>
        Back
      </button>

      {/* Header */}
      <div className="bg-white border border-outline-variant/50 rounded-2xl p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs text-on-surface-variant uppercase tracking-wide font-semibold">Donor ID</p>
            <p className="text-base font-bold font-mono text-on-surface mt-0.5">{id}</p>
            <div className="flex flex-wrap gap-2 mt-2">
              {blood_group && (
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary">
                  {blood_group}
                </span>
              )}
              {eligibility_status && (
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full
                  ${eligibility_status.toLowerCase().includes('eligible') && !eligibility_status.toLowerCase().includes('in')
                    ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
                  {eligibility_status}
                </span>
              )}
              <span className="text-xs px-2.5 py-1 rounded-full bg-surface-container text-on-surface-variant">
                {total_donations} donation{total_donations !== 1 ? 's' : ''}
              </span>
              {lifetime_show_rate !== null && lifetime_show_rate !== undefined && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-surface-container text-on-surface-variant">
                  {(lifetime_show_rate * 100).toFixed(0)}% historical show rate
                </span>
              )}
            </div>
          </div>
          <div className="text-right">
            <span className={`text-5xl font-black tabular-nums ${scoreColor}`}>
              {commitment_score}
            </span>
            <p className={`text-xs font-semibold mt-1 ${CONFIDENCE_STYLE[confidence]?.split(' ')[1] || 'text-gray-500'}`}>
              {confidence} confidence
            </p>
          </div>
        </div>

        {/* Memory summary */}
        {memory_summary && (
          <div className="mt-3 text-xs text-on-surface-variant bg-surface-container rounded-lg px-3 py-2">
            <span className="material-symbols-outlined text-[12px] align-middle mr-1 text-secondary">history</span>
            {memory_summary}
          </div>
        )}

        {/* Engagement assessment */}
        <div className="mt-3">
          <p className="text-xs text-on-surface-variant uppercase tracking-wide font-semibold mb-2">
            Prioritization Window
          </p>
          <EngagementBadge engagement={engagement} />
          {engagement?.reasoning && (
            <p className="text-xs text-on-surface-variant mt-1">{engagement.reasoning}</p>
          )}
        </div>
      </div>

      {/* Why selected: reasons + flags */}
      {(reasons?.length > 0 || flags?.length > 0) && (
        <div className="bg-white border border-outline-variant/50 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-on-surface-variant uppercase tracking-wide mb-3">
            Why This Donor?
          </h2>
          {reasons?.length > 0 && (
            <ul className="space-y-1.5 mb-3">
              {reasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="text-green-500 mt-0.5 shrink-0">✓</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          )}
          {flags?.length > 0 && (
            <>
              <p className="text-xs font-semibold text-amber uppercase tracking-wide mb-1.5">Coordinator Notes</p>
              <ul className="space-y-1.5">
                {flags.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-on-surface-variant">
                    <span className="text-amber mt-0.5 shrink-0">⚠</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {/* Signal breakdown */}
      <div className="bg-white border border-outline-variant/50 rounded-2xl p-5">
        <h2 className="text-sm font-semibold text-on-surface-variant uppercase tracking-wide mb-4">
          Signal Breakdown
        </h2>
        <ScoreBar score={commitment_score} signals={signals} />
      </div>

      <div className="bg-surface-container rounded-xl p-4 text-xs text-on-surface-variant">
        <span className="material-symbols-outlined text-[14px] align-middle mr-1">info</span>
        Score is deterministic — 6 signals, no LLM. Every point is traceable to raw donor data.
        Blood compatibility is a hard gate, not a scored signal. Memory-adjusted show rate updates after each resolved interaction.
      </div>
    </div>
  )
}
