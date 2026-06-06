import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

const BG_PILL = {
  'O Negative': 'bg-red-700',   'O Positive': 'bg-red-400',
  'A Negative': 'bg-blue-700',  'A Positive': 'bg-blue-400',
  'B Negative': 'bg-violet-700','B Positive': 'bg-violet-400',
  'AB Negative':'bg-orange-700','AB Positive':'bg-orange-400',
}

const BLOOD_GROUPS = [
  'A Positive','A Negative','B Positive','B Negative',
  'AB Positive','AB Negative','O Positive','O Negative',
]

function statusBadge(activeStatus, eligStatus) {
  const s = (activeStatus || '').toLowerCase().trim()
  const e = (eligStatus   || '').toLowerCase()
  const isActive   = s === 'active'
  const isEligible = e.includes('eligible') && !e.includes('not eligible') && !e.includes('ineligible')
  if (isActive && isEligible) return { label: 'Active · Eligible', cls: 'bg-green-50 text-green-700' }
  if (isActive)               return { label: 'Active',            cls: 'bg-blue-50 text-blue-700'  }
  if (isEligible)             return { label: 'Eligible',          cls: 'bg-teal-50 text-teal-700'  }
  return { label: 'Inactive', cls: 'bg-gray-100 text-gray-500' }
}

export default function Donors() {
  const [donors, setDonors]         = useState([])
  const [loading, setLoading]       = useState(true)
  const [filter, setFilter]         = useState('')
  const [bgFilter, setBgFilter]     = useState('')
  const [activeOnly, setActiveOnly] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.getDonors({ limit: 500 })
      .then(setDonors)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const visible = donors.filter(d => {
    if (bgFilter && d.blood_group !== bgFilter) return false
    if (activeOnly && (d.user_donation_active_status || '').toLowerCase().trim() !== 'active') return false
    if (filter) {
      const q = filter.toLowerCase()
      if (!d.user_id.toLowerCase().includes(q)) return false
    }
    return true
  })

  return (
    <div className="p-6 space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-on-surface">Donor Network</h1>
        <p className="text-xs text-on-surface-variant mt-0.5">
          {loading ? 'Loading…' : `${donors.length.toLocaleString()} donors total`}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative">
          <span className="material-symbols-outlined absolute left-2.5 top-1/2 -translate-y-1/2 text-[16px] text-on-surface-variant">search</span>
          <input
            value={filter}
            onChange={e => setFilter(e.target.value)}
            placeholder="Search donor ID…"
            className="pl-8 pr-3 py-2 text-sm border border-outline-variant rounded-lg focus:outline-none focus:border-primary w-56"
          />
        </div>

        <select
          value={bgFilter}
          onChange={e => setBgFilter(e.target.value)}
          className="px-3 py-2 text-sm border border-outline-variant rounded-lg focus:outline-none focus:border-primary"
        >
          <option value="">All blood groups</option>
          {BLOOD_GROUPS.map(bg => <option key={bg} value={bg}>{bg}</option>)}
        </select>

        <label className="flex items-center gap-2 text-sm text-on-surface-variant cursor-pointer select-none">
          <input type="checkbox" checked={activeOnly} onChange={e => setActiveOnly(e.target.checked)}
            className="rounded accent-primary" />
          Active only
        </label>

        {(filter || bgFilter || activeOnly) && (
          <button onClick={() => { setFilter(''); setBgFilter(''); setActiveOnly(false) }}
            className="text-xs text-on-surface-variant hover:text-on-surface underline">
            Clear filters
          </button>
        )}

        <span className="ml-auto text-xs text-on-surface-variant tabular-nums">
          {visible.length} shown
        </span>
      </div>

      {/* Table */}
      <div className="bg-white border border-outline-variant/50 rounded-2xl overflow-hidden">
        {loading ? (
          <div className="py-10 text-center text-sm text-on-surface-variant">Loading donors…</div>
        ) : visible.length === 0 ? (
          <div className="py-10 text-center text-sm text-on-surface-variant">No donors match these filters.</div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-outline-variant/30 bg-surface-container/50">
                <th className="text-left px-4 py-3 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Donor ID</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Blood Group</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Status</th>
                <th className="text-right px-4 py-3 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Donations</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Last Donated</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {visible.map((d, i) => {
                const badge  = statusBadge(d.user_donation_active_status, d.eligibility_status)
                const bgPill = BG_PILL[d.blood_group] || 'bg-gray-400'
                const lastDate = d.last_donation_date && d.last_donation_date !== 'None'
                  ? d.last_donation_date.slice(0, 10) : '—'

                return (
                  <tr key={d.user_id}
                    className={`border-b border-outline-variant/10 hover:bg-surface-container/40 cursor-pointer transition-colors
                      ${i % 2 === 0 ? '' : 'bg-surface-container/10'}`}
                    onClick={() => navigate(`/donors/${d.user_id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-on-surface">{d.user_id.slice(-16)}</td>
                    <td className="px-4 py-3">
                      {d.blood_group ? (
                        <span className={`text-xs font-bold text-white px-2.5 py-1 rounded-lg ${bgPill}`}>
                          {d.blood_group}
                        </span>
                      ) : <span className="text-on-surface-variant">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${badge.cls}`}>
                        {badge.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-sm">
                      {d.donations_till_date ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-on-surface-variant tabular-nums">
                      {lastDate}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs text-secondary hover:underline">View →</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
