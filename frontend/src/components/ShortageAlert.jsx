const SEVERITY_STYLES = {
  critical: 'border-danger/30 bg-danger/5',
  medium:   'border-amber/30  bg-amber/5',
  low:      'border-outline/20 bg-surface-container',
}

const BG_COLORS = {
  'O Negative':  'bg-red-100 text-red-700',
  'O Positive':  'bg-red-50  text-red-600',
  'A Negative':  'bg-blue-100 text-blue-700',
  'A Positive':  'bg-blue-50  text-blue-600',
  'B Negative':  'bg-purple-100 text-purple-700',
  'B Positive':  'bg-purple-50  text-purple-600',
  'AB Negative': 'bg-orange-100 text-orange-700',
  'AB Positive': 'bg-orange-50  text-orange-600',
}

export default function ShortageAlert({ alert }) {
  const { blood_group, city_cluster, eligible_donor_count, active_patient_count, severity } = alert
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.low
  const bgColor = BG_COLORS[blood_group] || 'bg-gray-100 text-gray-700'
  const isCritical = severity === 'critical'

  return (
    <div className={`rounded-lg border px-4 py-3 ${style}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className={`text-xs font-bold px-2 py-1 rounded-full ${bgColor}`}>
            {blood_group}
          </span>
          <div>
            <p className={`text-sm font-semibold leading-tight ${isCritical ? 'text-danger' : 'text-amber'}`}>
              {isCritical ? 'Critical Shortage' : 'Low Supply'}
            </p>
            <p className="text-xs text-on-surface-variant">
              {eligible_donor_count} eligible donor{eligible_donor_count !== 1 ? 's' : ''} ·{' '}
              {active_patient_count} patient{active_patient_count !== 1 ? 's' : ''} ·{' '}
              {city_cluster}
            </p>
          </div>
        </div>
        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded-full
          ${isCritical ? 'bg-danger/10 text-danger' : 'bg-amber/10 text-amber'}`}>
          {severity}
        </span>
      </div>
    </div>
  )
}
