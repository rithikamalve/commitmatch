const SIGNAL_LABELS = {
  blood_compatibility: 'Blood Compatibility',
  proximity:           'Proximity',
  reliability:         'Reliability',
  engagement:          'Engagement',
  recency:             'Recency',
  cycle_health:        'Cycle Health',
  active_status:       'Active Status',
}

function barColor(v) {
  if (v >= 80) return 'bg-success'
  if (v >= 50) return 'bg-amber'
  return 'bg-danger'
}

function scoreRingColor(v) {
  if (v >= 92) return 'text-success'
  if (v >= 80) return 'text-amber'
  return 'text-danger'
}

export default function ScoreBar({ score, signals = {}, signalExplanations = {} }) {
  return (
    <div>
      {/* Total score */}
      <div className="flex items-center gap-3 mb-4">
        <span className={`text-4xl font-black tabular-nums ${scoreRingColor(score)}`}>{score}</span>
        <div>
          <p className="text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Commitment Score</p>
          <p className="text-xs text-on-surface-variant">
            {score >= 92 ? 'High confidence' : score >= 80 ? 'Medium confidence' : 'Low confidence'}
          </p>
        </div>
      </div>

      {/* Signals */}
      <div className="space-y-3">
        {Object.entries(signals).map(([key, value]) => (
          <div key={key}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-on-surface">
                {SIGNAL_LABELS[key] || key}
              </span>
              <span className={`text-xs font-bold tabular-nums ${barColor(value).replace('bg-', 'text-')}`}>
                {value}
              </span>
            </div>
            <div className="h-1.5 bg-surface-container rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${barColor(value)}`}
                style={{ width: `${value}%` }}
              />
            </div>
            {signalExplanations[key] && (
              <p className="text-[11px] text-on-surface-variant mt-0.5">{signalExplanations[key]}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
