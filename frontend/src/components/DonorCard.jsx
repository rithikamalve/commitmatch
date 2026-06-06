import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ScoreBar from './ScoreBar'
import AmberAlert from './AmberAlert'

const STATUS_STYLES = {
  confirmed:     'bg-green-50 text-green-700 border-green-200',
  sent:          'bg-blue-50 text-blue-700 border-blue-200',
  pending:       'bg-gray-50 text-gray-500 border-gray-200',
  declined:      'bg-red-50 text-red-700 border-red-200',
  amber:         'bg-amber-50 text-amber-700 border-amber-200',
  no_response:   'bg-gray-100 text-gray-500 border-gray-200',
  ready_to_send: 'bg-blue-50 text-blue-600 border-blue-200',
}

const CONFIDENCE_COLORS = {
  high:   'text-green-600',
  medium: 'text-amber-600',
  low:    'text-red-500',
}

export default function DonorCard({ donor, requestId, onPromoteStandby }) {
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()

  const statusStyle = STATUS_STYLES[donor.outreach_status] || STATUS_STYLES.pending
  const scoreColor  = donor.commitment_score >= 92 ? 'bg-green-500 text-white' :
                      donor.commitment_score >= 80 ? 'bg-amber-500 text-white' : 'bg-red-500 text-white'
  const confColor   = CONFIDENCE_COLORS[donor.confidence] || 'text-gray-500'

  return (
    <div className={`bg-white border rounded-xl overflow-hidden
      ${donor.hesitation_detected ? 'border-amber/40 ring-1 ring-amber/20' : 'border-outline-variant/50'}`}>

      <div className="px-4 py-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="w-7 h-7 rounded-full bg-surface-container text-xs font-bold text-on-surface-variant flex items-center justify-center shrink-0">
              #{donor.rank}
            </span>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <p className="text-sm font-semibold text-on-surface font-mono">
                  {donor.donor_id.slice(-12)}
                </p>
                {donor.is_primary && (
                  <span className="text-[10px] font-bold bg-primary/10 text-primary px-1.5 py-0.5 rounded">PRIMARY</span>
                )}
                {donor.is_standby && (
                  <span className="text-[10px] font-bold bg-blue-50 text-secondary px-1.5 py-0.5 rounded">STANDBY</span>
                )}
              </div>
              <p className="text-xs text-on-surface-variant mt-0.5">
                {donor.blood_group || '?'} · {donor.total_donations} donation{donor.total_donations !== 1 ? 's' : ''}
                {donor.lifetime_show_rate !== null && donor.lifetime_show_rate !== undefined
                  ? ` · ${(donor.lifetime_show_rate * 100).toFixed(0)}% show rate`
                  : ' · no history'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="text-right">
              <span className={`text-sm font-black px-2.5 py-1 rounded-full tabular-nums ${scoreColor}`}>
                {donor.commitment_score}
              </span>
              <p className={`text-[10px] font-semibold mt-0.5 ${confColor}`}>
                {donor.confidence} confidence
              </p>
            </div>
            <span className={`text-[11px] font-semibold px-2 py-1 rounded-full border ${statusStyle}`}>
              {donor.outreach_status.replace('_', ' ')}
            </span>
          </div>
        </div>

        {/* Memory summary */}
        {donor.memory_summary && donor.memory_summary !== 'No interaction history.' && (
          <p className="text-xs text-secondary ml-10 mt-1.5 italic">{donor.memory_summary}</p>
        )}

        {/* Standby note */}
        {donor.is_standby && (
          <p className="text-xs text-secondary mt-1.5 ml-10">
            Standby — contacted automatically if primary declines or does not respond in 4 hours
          </p>
        )}

        {/* Amber alert */}
        {donor.hesitation_detected && (
          <div className="mt-2">
            <AmberAlert
              donorName={donor.donor_id.slice(-8)}
              replyText={donor.donor_reply_raw || 'Hesitation detected in reply'}
              requestId={requestId}
              onPromote={onPromoteStandby}
            />
          </div>
        )}

        {/* Reason pills */}
        {donor.reasons && donor.reasons.length > 0 && (
          <div className="mt-2 ml-10 flex flex-wrap gap-1">
            {donor.reasons.slice(0, 3).map((r, i) => (
              <span key={i} className="text-[11px] bg-green-50 text-green-700 px-2 py-0.5 rounded-full border border-green-100">
                ✓ {r}
              </span>
            ))}
          </div>
        )}

        {/* Flags */}
        {donor.flags && donor.flags.length > 0 && (
          <div className="mt-1 ml-10 flex flex-wrap gap-1">
            {donor.flags.slice(0, 2).map((f, i) => (
              <span key={i} className="text-[11px] bg-amber/10 text-amber px-2 py-0.5 rounded-full border border-amber/20">
                ⚠ {f}
              </span>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="mt-2 ml-10 flex gap-3">
          <button
            onClick={() => setExpanded(x => !x)}
            className="text-xs text-secondary hover:text-secondary/80 flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">
              {expanded ? 'expand_less' : 'expand_more'}
            </span>
            {expanded ? 'Hide' : 'Show'} full breakdown
          </button>
          <button
            onClick={() => navigate(`/donors/${donor.donor_id}`)}
            className="text-xs text-on-surface-variant hover:text-secondary"
          >
            Profile →
          </button>
        </div>
      </div>

      {/* Score breakdown */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-outline-variant/30">
          <ScoreBar score={donor.commitment_score} signals={donor.signals || {}} />
        </div>
      )}
    </div>
  )
}
