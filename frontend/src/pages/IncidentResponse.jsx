import { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet'

const CENTER = [17.3850, 78.4867]

const INCIDENTS = [
  {
    id:'i1', type:'accident', icon:'emergency', color:'#dc2626',
    title:'Multi-vehicle collision — NH44 Shamshabad',
    location:'Shamshabad, Rangareddy', lat:17.2403, lng:78.4294,
    age:'14 min ago', banks:4, donors:23, status:'responding', eta:'8 min to first unit',
    units:['3× O Negative','5× O Positive','2× B Positive'],
  },
  {
    id:'i2', type:'outbreak', icon:'coronavirus', color:'#d97706',
    title:'Dengue cluster — Secunderabad zone',
    location:'Secunderabad', lat:17.4439, lng:78.4983,
    age:'2h 14min ago', banks:6, donors:0, status:'monitoring', eta:null,
    units:['12× Platelets'],
    deferral:'31 donors deferred (28-day exclusion window)',
  },
  {
    id:'i3', type:'mass_casualty', icon:'local_fire_department', color:'#9333ea',
    title:'Factory explosion — Patancheru Industrial',
    location:'Patancheru, Sangareddy', lat:17.5355, lng:78.2631,
    age:'52 min ago', banks:7, donors:45, status:'resolved', eta:null,
    units:['6× O Negative','4× A Positive','3× B Positive'],
  },
]

const BANKS = [
  { name:'AIIMS Hyderabad',    lat:17.4156, lng:78.4347, stock:'high'     },
  { name:'KIMS Secunderabad',  lat:17.4439, lng:78.4983, stock:'low'      },
  { name:'Apollo Jubilee Hills',lat:17.4196,lng:78.4086, stock:'adequate' },
  { name:'Nizam Blood Bank',   lat:17.3978, lng:78.4725, stock:'critical' },
  { name:'Rainbow Children',   lat:17.4489, lng:78.3936, stock:'adequate' },
]

const BANK_COLOR = { high:'#16a34a', adequate:'#3b82f6', low:'#d97706', critical:'#dc2626' }

const RESPONSE_ROUTES = [
  [[17.2403,78.4294],[17.4156,78.4347]],
  [[17.2403,78.4294],[17.3978,78.4725]],
]

const RULES = [
  {
    id:'r1', type:'deferral', icon:'person_cancel', color:'#dc2626',
    bg:'bg-red-50', border:'border-red-200', badge:'bg-red-100 text-red-700',
    trigger:'Dengue cluster — Secunderabad (active)',
    effect:'31 donors temporarily deferred from this zone',
    detail:'28-day exclusion window applied. Platelet priority raised for compatible donors outside affected area.',
    groups:['Platelets','B+','O+'],
  },
  {
    id:'r2', type:'priority_boost', icon:'priority_high', color:'#2563eb',
    bg:'bg-blue-50', border:'border-blue-200', badge:'bg-blue-100 text-blue-700',
    trigger:'Multi-vehicle accident — NH44 (responding)',
    effect:'O Negative elevated to Priority 1 across 6km radius',
    detail:'Emergency protocol active: donors within proximity boundary auto-notified via WhatsApp within 90 seconds of incident.',
    groups:['O Neg','O+'],
  },
  {
    id:'r3', type:'screening', icon:'health_and_safety', color:'#d97706',
    bg:'bg-amber-50', border:'border-amber-200', badge:'bg-amber-100 text-amber-700',
    trigger:'Monsoon season protocol (Jun–Sep)',
    effect:'Malaria-endemic zone enhanced screening active',
    detail:'Donors from flagged localities require 30-day travel clearance. Eligibility engine updated automatically.',
    groups:['All'],
  },
]

const STATUS_CLS = {
  responding: 'bg-red-100 text-red-700',
  monitoring:  'bg-amber-100 text-amber-700',
  resolved:    'bg-gray-100 text-gray-500',
}

export default function IncidentResponse() {
  const [selected, setSelected] = useState('i1')
  const inc = INCIDENTS.find(i => i.id === selected)
  const critical = INCIDENTS.filter(i => i.status !== 'resolved')

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">
      {critical.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-3 flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shrink-0" />
          <span className="text-sm font-bold text-red-700">
            {critical.length} active incident{critical.length > 1 ? 's' : ''} — nearest donors notified automatically
          </span>
          <span className="ml-auto text-xs text-red-400">Updated 14s ago</span>
        </div>
      )}

      <div>
        <h2 className="text-xl font-black text-on-surface">Hyper-Local Incident Response</h2>
        <p className="text-sm text-on-surface-variant mt-0.5">Real-time accident alerts, outbreak adaptation, and proximity donor activation</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon:'crisis_alert',   value:'3',  label:'Active Incidents',             color:'#dc2626' },
          { icon:'account_balance',value:'17', label:'Banks Notified',               color:'#3b82f6' },
          { icon:'groups',         value:'68', label:'Donors Activated',             color:'#16a34a' },
          { icon:'person_cancel',  value:'31', label:'Donors Deferred (outbreak)',   color:'#d97706' },
        ].map(s => (
          <div key={s.label} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="material-symbols-outlined text-[18px]" style={{ color: s.color }}>{s.icon}</span>
              <span className="text-2xl font-black text-on-surface">{s.value}</span>
            </div>
            <p className="text-xs text-on-surface-variant">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Incident feed */}
        <div className="lg:col-span-2 space-y-3">
          <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Incident Feed</h3>
          {INCIDENTS.map(i => (
            <div key={i.id} onClick={() => setSelected(i.id)}
              className={`cursor-pointer bg-surface-container-lowest rounded-xl p-4 border transition-all ${
                selected === i.id ? 'border-primary ring-1 ring-primary/20' : 'border-outline-variant hover:border-primary/50'
              }`}>
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ backgroundColor: i.color + '20' }}>
                  <span className="material-symbols-outlined text-[18px]" style={{ color: i.color }}>{i.icon}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-sm text-on-surface leading-tight mb-0.5">{i.title}</h4>
                  <p className="text-xs text-on-surface-variant mb-2">{i.location} · {i.age}</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${STATUS_CLS[i.status]}`}>
                      {i.status.toUpperCase()}
                    </span>
                    <span className="text-[10px] text-on-surface-variant">{i.banks} banks</span>
                    {i.donors > 0 && <span className="text-[10px] text-green-600 font-semibold">{i.donors} donors activated</span>}
                  </div>
                  {i.status === 'responding' && i.eta && (
                    <p className="text-[11px] text-blue-600 font-semibold mt-1.5">⏱ {i.eta}</p>
                  )}
                  {i.deferral && (
                    <p className="text-[11px] text-amber-600 font-semibold mt-1.5">⚠ {i.deferral}</p>
                  )}
                </div>
              </div>
              {selected === i.id && (
                <div className="mt-3 pt-3 border-t border-outline-variant/40">
                  <p className="text-[10px] font-bold text-on-surface-variant uppercase tracking-wider mb-2">Blood Units Needed</p>
                  <div className="flex flex-wrap gap-1.5">
                    {i.units.map(u => (
                      <span key={u} className="text-[11px] font-semibold px-2 py-0.5 rounded-full text-white" style={{ backgroundColor: i.color }}>
                        {u}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Map */}
        <div className="lg:col-span-3">
          <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-3">Incident Map — Greater Hyderabad</h3>
          <div className="rounded-xl overflow-hidden border border-outline-variant" style={{ height: 380 }}>
            <MapContainer center={CENTER} zoom={11} style={{ height:'100%', width:'100%' }} scrollWheelZoom={false}>
              <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                attribution='&copy; <a href="https://carto.com">CARTO</a>' />
              {BANKS.map(b => (
                <CircleMarker key={b.name} center={[b.lat, b.lng]} radius={7}
                  pathOptions={{ color:'#fff', weight:1.5, fillColor: BANK_COLOR[b.stock], fillOpacity:0.9 }}>
                  <Popup><b>{b.name}</b><br />Stock: {b.stock}</Popup>
                </CircleMarker>
              ))}
              {INCIDENTS.map(i => (
                <CircleMarker key={i.id} center={[i.lat, i.lng]}
                  radius={i.id === selected ? 16 : 10}
                  pathOptions={{ color: i.color, weight:2, fillColor: i.color, fillOpacity: i.status === 'resolved' ? 0.25 : 0.65 }}>
                  <Popup><b>{i.title}</b><br />Status: {i.status}<br />Banks notified: {i.banks}</Popup>
                </CircleMarker>
              ))}
              {RESPONSE_ROUTES.map((r, idx) => (
                <Polyline key={idx} positions={r}
                  pathOptions={{ color:'#3b82f6', weight:2, dashArray:'5,8', opacity:0.7 }} />
              ))}
            </MapContainer>
          </div>
          <div className="flex gap-5 mt-2 flex-wrap">
            {[
              { color:'#dc2626', label:'Critical incident', opacity:0.65 },
              { color:'#d97706', label:'Outbreak zone', opacity:0.65 },
              { color:'#16a34a', label:'Blood bank (adequate)', opacity:1 },
              { color:'#dc2626', label:'Blood bank (critical)', opacity:1, bank:true },
            ].map(({ color, label, opacity }) => (
              <div key={label} className="flex items-center gap-1.5 text-xs text-on-surface-variant">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color, opacity }} />
                {label}
              </div>
            ))}
            <div className="flex items-center gap-1.5 text-xs text-on-surface-variant">
              <div className="w-5 border-t-2 border-dashed border-blue-400" />
              Response route
            </div>
          </div>
        </div>
      </div>

      {/* Adaptation Rules */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Adaptive Prioritization Rules — Auto-Applied</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {RULES.map(r => (
            <div key={r.id} className={`rounded-xl border p-4 ${r.bg} ${r.border}`}>
              <div className="flex items-start gap-2 mb-2">
                <span className="material-symbols-outlined text-[18px] mt-0.5" style={{ color: r.color }}>{r.icon}</span>
                <div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${r.badge}`}>
                    {r.type.replace(/_/g,' ').toUpperCase()}
                  </span>
                  <p className="text-[11px] text-on-surface-variant mt-1">{r.trigger}</p>
                </div>
              </div>
              <p className="text-sm font-bold text-on-surface mb-1">{r.effect}</p>
              <p className="text-xs text-on-surface-variant leading-relaxed mb-2">{r.detail}</p>
              <div className="flex flex-wrap gap-1">
                {r.groups.map(g => (
                  <span key={g} className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-white/60 text-on-surface border border-outline-variant/40">
                    {g}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
