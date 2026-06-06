import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

const BG_COLOR = {
  'O Negative': '#b91c1c', 'O Positive': '#ef4444',
  'A Negative': '#1d4ed8', 'A Positive': '#3b82f6',
  'B Negative': '#7c3aed', 'B Positive': '#8b5cf6',
  'AB Negative':'#c2410c', 'AB Positive':'#f97316',
}

const OUTCOME_STYLE = {
  confirmed:   { label: 'Last: Confirmed',   color: '#16a34a' },
  declined:    { label: 'Last: Declined',    color: '#dc2626' },
  no_response: { label: 'Last: No Response', color: '#9ca3af' },
  hesitation:  { label: 'Last: Hesitated',  color: '#d97706' },
}

function StatBox({ value, label, accent }) {
  return (
    <div className="flex flex-col items-center justify-center bg-white border border-outline-variant rounded-xl py-4 px-3 text-center">
      <span className="text-3xl font-black tabular-nums" style={{ color: accent || '#1c1b1f' }}>
        {value ?? '—'}
      </span>
      <span className="text-[11px] text-on-surface-variant font-semibold uppercase tracking-wide mt-1">{label}</span>
    </div>
  )
}

function Field({ label, value }) {
  if (!value) return null
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-outline-variant/40 last:border-0">
      <span className="text-xs text-on-surface-variant font-medium">{label}</span>
      <span className="text-sm font-semibold text-on-surface">{value}</span>
    </div>
  )
}

export default function DonorProfile() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  useEffect(() => {
    api.getDonor(id)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className="flex items-center justify-center h-48 text-sm text-on-surface-variant gap-2">
      <span className="material-symbols-outlined animate-pulse">sync</span> Loading…
    </div>
  )
  if (error) return (
    <div className="p-6 text-sm text-red-600">
      <span className="material-symbols-outlined align-middle mr-1">error</span>{error}
    </div>
  )
  if (!data) return (
    <div className="p-6 text-sm text-on-surface-variant">Donor not found.</div>
  )

  const bgColor   = BG_COLOR[data.blood_group] || '#6b7280'
  const isEligible = data.eligibility_status?.toLowerCase().includes('eligible') &&
                     !data.eligibility_status?.toLowerCase().includes('ineligible')
  const showRate  = data.lifetime_show_rate != null
    ? `${(data.lifetime_show_rate * 100).toFixed(0)}%` : null
  const outcome   = OUTCOME_STYLE[data.last_outcome]

  return (
    <div className="p-6 max-w-lg mx-auto space-y-4">
      <button onClick={() => navigate(-1)}
        className="flex items-center gap-1 text-sm text-on-surface-variant hover:text-on-surface transition-colors">
        <span className="material-symbols-outlined text-[16px]">arrow_back</span>
        Back
      </button>

      {/* ID Card */}
      <div className="rounded-2xl overflow-hidden shadow-lg border border-outline-variant">

        {/* Card header — blood group banner */}
        <div className="px-6 py-5 flex items-center justify-between" style={{ backgroundColor: bgColor }}>
          <div>
            <p className="text-white/70 text-[10px] font-bold uppercase tracking-widest mb-0.5">Blood Warriors</p>
            <p className="text-white text-4xl font-black tracking-tight">{data.blood_group || '?'}</p>
            <p className="text-white/80 text-xs mt-1 font-medium">Verified Donor</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className={`text-xs font-bold px-3 py-1 rounded-full ${
              isEligible ? 'bg-white/20 text-white' : 'bg-black/30 text-white/70'
            }`}>
              {isEligible ? '✓ Eligible' : '✗ Ineligible'}
            </span>
            {data.user_donation_active_status && (
              <span className="text-white/60 text-[10px] font-semibold uppercase">
                {data.user_donation_active_status}
              </span>
            )}
          </div>
        </div>

        {/* Card body */}
        <div className="bg-white px-6 py-4 space-y-0">

          {/* Donor ID */}
          <div className="py-3 border-b border-outline-variant/40">
            <p className="text-[10px] text-on-surface-variant font-semibold uppercase tracking-wider">Donor ID</p>
            <p className="font-mono text-sm font-bold text-on-surface mt-0.5 break-all">{id}</p>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-3 py-4">
            <StatBox value={data.total_donations} label="Donations" accent={bgColor} />
            <StatBox value={showRate} label="Show Rate" accent={showRate ? (parseFloat(showRate) >= 70 ? '#16a34a' : '#d97706') : undefined} />
            <StatBox
              value={data.total_confirmations > 0 ? data.total_confirmations : null}
              label="Confirmed"
              accent="#16a34a"
            />
          </div>

          {/* Details */}
          <div className="border-t border-outline-variant/40 pt-1">
            <Field label="Last Donation"   value={data.last_donation_date} />
            <Field label="Next Eligible"   value={data.next_eligible_date} />
            <Field label="Donation Cycle"  value={data.frequency_in_days ? `Every ${data.frequency_in_days} days` : null} />
            <Field label="Donor Type"      value={data.donor_type} />
            <Field label="Role"            value={data.role} />
            <Field label="Language"        value={data.preferred_language} />
          </div>

          {/* Memory footer */}
          {(data.last_outcome || data.total_declines > 0 || data.total_no_responses > 0) && (
            <div className="mt-2 pt-3 border-t border-outline-variant/40 flex items-center justify-between flex-wrap gap-2">
              {outcome && (
                <span className="text-[11px] font-semibold" style={{ color: outcome.color }}>
                  {outcome.label}
                </span>
              )}
              <div className="flex gap-3 text-[11px] text-on-surface-variant">
                {data.total_declines > 0 && <span>{data.total_declines} declined</span>}
                {data.total_no_responses > 0 && <span>{data.total_no_responses} no-response</span>}
              </div>
            </div>
          )}
        </div>

        {/* Card footer */}
        <div className="bg-surface-container-low px-6 py-3 flex items-center justify-between">
          <span className="text-[10px] text-on-surface-variant">
            {data.last_updated
              ? `Updated ${new Date(data.last_updated).toLocaleDateString()}`
              : 'No interactions yet'}
          </span>
          <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ backgroundColor: bgColor }}>
            <span className="material-symbols-outlined text-white text-[14px]"
              style={{ fontVariationSettings: "'FILL' 1" }}>water_drop</span>
          </div>
        </div>
      </div>
    </div>
  )
}
