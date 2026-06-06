import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, LineChart, Line, ResponsiveContainer,
} from 'recharts'
import { api } from '../lib/api'

const TABS = [
  { id: 'supply',   label: 'Supply vs Demand' },
  { id: 'churn',    label: 'Churn Risk' },
  { id: 'shortage', label: 'Shortage Alerts' },
  { id: 'health',   label: 'Network Health' },
]

const RISK_COLORS = { High: '#dc2626', Medium: '#d97706', Low: '#16a34a' }

const SEVERITY_STYLES = {
  critical: 'bg-danger/10 text-danger border-danger/30',
  medium:   'bg-amber/10 text-amber border-amber/30',
  low:      'bg-green-50 text-success border-success/20',
}

// ── Tab: Supply vs Demand ────────────────────────────────────────────────────
function SupplyDemandTab({ data }) {
  const chartData = data.map(d => ({
    name: d.blood_group.replace(' ', '\n'),
    'Eligible Donors': d.eligible_donors,
    'Active Patients': d.active_patients,
  }))

  return (
    <div>
      <p className="text-sm text-on-surface-variant mb-4">
        Eligible donors within 20km vs active patients by blood group.
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e4beba" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: '8px', border: '1px solid #e4beba' }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="Eligible Donors" fill="#16a34a" radius={[4,4,0,0]} />
          <Bar dataKey="Active Patients" fill="#af101a" radius={[4,4,0,0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Gap table */}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-outline-variant/30">
              <th className="text-left py-2 pr-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Blood Group</th>
              <th className="text-right py-2 pr-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Donors</th>
              <th className="text-right py-2 pr-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Patients</th>
              <th className="text-right py-2 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">Gap</th>
            </tr>
          </thead>
          <tbody>
            {data.map(d => (
              <tr key={d.blood_group} className={`border-b border-outline-variant/20 ${d.gap > 0 ? 'bg-danger/5' : ''}`}>
                <td className="py-2 pr-4 font-semibold">{d.blood_group}</td>
                <td className="py-2 pr-4 text-right tabular-nums text-success">{d.eligible_donors}</td>
                <td className="py-2 pr-4 text-right tabular-nums">{d.active_patients}</td>
                <td className={`py-2 text-right tabular-nums font-semibold ${d.gap > 0 ? 'text-danger' : 'text-on-surface-variant'}`}>
                  {d.gap > 0 ? `-${d.gap}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tab: Churn Risk ──────────────────────────────────────────────────────────
function ChurnRiskTab({ data }) {
  return (
    <div>
      {/* Summary chips */}
      {data.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {['High', 'Medium', 'Low'].map(level => {
            const count = data.filter(d => d.risk_level === level).length
            if (!count) return null
            return (
              <span key={level} className="text-xs font-semibold px-3 py-1 rounded-full"
                style={{ backgroundColor: RISK_COLORS[level] + '18', color: RISK_COLORS[level] }}>
                {count} {level} risk
              </span>
            )
          })}
        </div>
      )}
      <p className="text-sm text-on-surface-variant mb-4">
        Donors not contacted in 180+ days — re-engagement needed.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-outline-variant/30">
              {['Donor ID','Blood','Days Silent','Donations','Risk'].map(h => (
                <th key={h} className="text-left py-2 pr-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map(d => (
              <tr key={d.donor_id} className="border-b border-outline-variant/20 hover:bg-surface-container/50">
                <td className="py-2 pr-4 font-mono text-xs">{d.donor_id.slice(-12)}</td>
                <td className="py-2 pr-4">{d.blood_group || '—'}</td>
                <td className="py-2 pr-4 tabular-nums">{d.days_since_contact < 0 ? 'Never' : d.days_since_contact}</td>
                <td className="py-2 pr-4 tabular-nums">{d.total_donations}</td>
                <td className="py-2">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full`}
                    style={{ backgroundColor: RISK_COLORS[d.risk_level] + '20', color: RISK_COLORS[d.risk_level] }}>
                    {d.risk_level}
                  </span>
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr><td colSpan={5} className="py-4 text-center text-on-surface-variant">No churn-risk donors</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Tab: Shortage Alerts ─────────────────────────────────────────────────────
function ShortageAlertsTab({ data }) {
  return (
    <div>
      <p className="text-sm text-on-surface-variant mb-4">
        Active shortage alerts by blood group and severity.
      </p>
      <div className="grid grid-cols-1 gap-3">
        {data.map(a => (
          <div key={a.id} className={`border rounded-xl px-4 py-3 ${SEVERITY_STYLES[a.severity] || ''}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-lg font-black">{a.blood_group}</span>
                <div>
                  <p className="text-sm font-semibold">{a.city_cluster}</p>
                  <p className="text-xs opacity-80">
                    {a.eligible_donor_count} eligible donor{a.eligible_donor_count !== 1 ? 's' : ''} ·{' '}
                    {a.active_patient_count} patient{a.active_patient_count !== 1 ? 's' : ''} needing
                  </p>
                </div>
              </div>
              <span className="text-xs font-bold uppercase tracking-wider px-2 py-1 rounded-full border opacity-80">
                {a.severity}
              </span>
            </div>
          </div>
        ))}
        {data.length === 0 && (
          <p className="text-sm text-on-surface-variant">No active shortage alerts — supply is healthy.</p>
        )}
      </div>
    </div>
  )
}

// ── Tab: Network Health ──────────────────────────────────────────────────────
const DONUT_COLORS = ['#af101a', '#e4beba']

function DonutStat({ label, pct }) {
  const data = [{ value: pct }, { value: 100 - pct }]
  return (
    <div className="flex flex-col items-center">
      <ResponsiveContainer width={120} height={120}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={35} outerRadius={50}
            dataKey="value" startAngle={90} endAngle={-270} strokeWidth={0}>
            <Cell fill={DONUT_COLORS[0]} />
            <Cell fill={DONUT_COLORS[1]} />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <p className="text-xl font-black text-on-surface tabular-nums -mt-2">{pct}%</p>
      <p className="text-xs text-on-surface-variant text-center">{label}</p>
    </div>
  )
}

function NetworkHealthTab({ data }) {
  if (!data) return <p className="text-sm text-on-surface-variant">Loading…</p>
  return (
    <div>
      <p className="text-sm text-on-surface-variant mb-4">
        {data.total_donors.toLocaleString()} total donors in network.
      </p>
      <div className="grid grid-cols-4 gap-6 mb-6">
        <DonutStat label="Eligible" pct={data.pct_eligible} />
        <DonutStat label="Active" pct={data.pct_active} />
        <DonutStat label="With History" pct={data.pct_with_donation_history} />
        <DonutStat label="Complete Profile" pct={data.pct_complete_profile} />
      </div>
      <div className="bg-surface-container rounded-xl p-4 text-sm space-y-1">
        <div className="flex justify-between">
          <span className="text-on-surface-variant">Eligible donors</span>
          <span className="tabular-nums font-semibold">{Math.round(data.total_donors * data.pct_eligible / 100).toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-on-surface-variant">Active donors</span>
          <span className="tabular-nums font-semibold">{Math.round(data.total_donors * data.pct_active / 100).toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-on-surface-variant">Donors with complete profile</span>
          <span className="tabular-nums font-semibold">{Math.round(data.total_donors * data.pct_complete_profile / 100).toLocaleString()}</span>
        </div>
      </div>
    </div>
  )
}

// ── Main ─────────────────────────────────────────────────────────────────────
export default function Analytics() {
  const [tab, setTab] = useState('supply')
  const [supplyData, setSupplyData]   = useState([])
  const [churnData, setChurnData]     = useState([])
  const [shortageData, setShortageData] = useState([])
  const [healthData, setHealthData]   = useState(null)
  const [loading, setLoading]         = useState(true)

  useEffect(() => {
    Promise.all([
      api.getSupplyDemand(),
      api.getChurnRisk(),
      api.getShortageAlerts(),
      api.getNetworkHealth(),
    ]).then(([sd, cr, sa, nh]) => {
      setSupplyData(sd)
      setChurnData(cr)
      setShortageData(sa)
      setHealthData(nh)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-on-surface">Analytics</h1>
        <p className="text-sm text-on-surface-variant mt-0.5">Supply, demand, and network health</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface-container rounded-xl p-1 w-fit">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              tab === t.id ? 'bg-white text-on-surface shadow-sm' : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-white border border-outline-variant/50 rounded-2xl p-6">
        {loading ? <p className="text-sm text-on-surface-variant">Loading…</p> : (
          <>
            {tab === 'supply'   && <SupplyDemandTab   data={supplyData} />}
            {tab === 'churn'    && <ChurnRiskTab       data={churnData} />}
            {tab === 'shortage' && <ShortageAlertsTab  data={shortageData} />}
            {tab === 'health'   && <NetworkHealthTab   data={healthData} />}
          </>
        )}
      </div>
    </div>
  )
}
