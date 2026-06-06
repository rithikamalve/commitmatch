import { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet'

const CENTER = [17.4200, 78.4400]

const BANKS = [
  { id:'b1', name:'AIIMS Hyderabad',     short:'AIIMS',   lat:17.4156, lng:78.4347, level:'adequate',
    stock:{'O Neg':8,'O Pos':12,'A Neg':3,'A Pos':9,'B Neg':2,'B Pos':7,'AB Neg':1,'AB Pos':4} },
  { id:'b2', name:'KIMS Secunderabad',   short:'KIMS',    lat:17.4439, lng:78.4983, level:'low',
    stock:{'O Neg':1,'O Pos':4,'A Neg':0,'A Pos':3,'B Neg':0,'B Pos':5,'AB Neg':0,'AB Pos':2} },
  { id:'b3', name:'Apollo Jubilee Hills',short:'Apollo',  lat:17.4196, lng:78.4086, level:'adequate',
    stock:{'O Neg':5,'O Pos':8,'A Neg':2,'A Pos':11,'B Neg':1,'B Pos':6,'AB Neg':1,'AB Pos':3} },
  { id:'b4', name:'Nizam Blood Bank',    short:'Nizam',   lat:17.3978, lng:78.4725, level:'critical',
    stock:{'O Neg':0,'O Pos':3,'A Neg':0,'A Pos':8,'B Neg':0,'B Pos':4,'AB Neg':0,'AB Pos':2} },
  { id:'b5', name:'Rainbow Children',   short:'Rainbow', lat:17.4489, lng:78.3936, level:'adequate',
    stock:{'O Neg':7,'O Pos':10,'A Neg':4,'A Pos':9,'B Neg':3,'B Pos':8,'AB Neg':2,'AB Pos':5} },
]

const LEVEL_COLOR = { adequate:'#16a34a', low:'#d97706', critical:'#dc2626' }

const SHIPMENTS = [
  { id:'s1', from:'AIIMS Hyderabad', to:'KIMS Secunderabad',
    fc:[17.4156,78.4347], tc:[17.4439,78.4983],
    units:'4× O Neg, 2× O Pos', status:'in_transit',  eta:'22 min', temp:'4.1°C', tempOk:true,  vehicle:'VH-001' },
  { id:'s2', from:'Nizam Blood Bank', to:'Apollo Jubilee Hills',
    fc:[17.3978,78.4725], tc:[17.4196,78.4086],
    units:'6× A Pos', status:'approaching', eta:'8 min',  temp:'5.2°C', tempOk:true,  vehicle:'VH-002' },
  { id:'s3', from:'Rainbow Children', to:'Nizam Blood Bank',
    fc:[17.4489,78.3936], tc:[17.3978,78.4725],
    units:'3× O Neg, 2× B Neg', status:'pending', eta:'45 min', temp:'—', tempOk:null, vehicle:'VH-003' },
  { id:'s4', from:'AIIMS Hyderabad', to:'Nizam Blood Bank',
    fc:[17.4156,78.4347], tc:[17.3978,78.4725],
    units:'2× A Neg, 1× AB Neg', status:'scheduled', eta:'1h 15 min', temp:'—', tempOk:null, vehicle:'VH-001' },
]

const STATUS_STYLE = {
  in_transit:  { label:'In Transit',  cls:'bg-blue-100 text-blue-700',  routeColor:'#3b82f6' },
  approaching: { label:'Approaching', cls:'bg-green-100 text-green-700', routeColor:'#16a34a' },
  pending:     { label:'Pending',     cls:'bg-amber-100 text-amber-700', routeColor:null },
  scheduled:   { label:'Scheduled',  cls:'bg-gray-100 text-gray-500',   routeColor:null },
}

const FORECAST = [
  { day:'Mon', units:14, type:'medium' },
  { day:'Tue', units:18, type:'high'   },
  { day:'Wed', units:11, type:'medium' },
  { day:'Thu', units:22, type:'high'   },
  { day:'Fri', units:19, type:'high'   },
  { day:'Sat', units:27, type:'critical'},
  { day:'Sun', units:24, type:'high'   },
]
const FORECAST_COLOR = { critical:'#dc2626', high:'#d97706', medium:'#3b82f6' }
const maxUnits = Math.max(...FORECAST.map(d => d.units))

const activeRoutes = SHIPMENTS.filter(s => STATUS_STYLE[s.status].routeColor)

export default function LogisticsNetwork() {
  const [activeBank, setActiveBank] = useState('b4')
  const bank = BANKS.find(b => b.id === activeBank)

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">
      {/* Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-3 flex items-center gap-3">
        <span className="material-symbols-outlined text-amber-600 text-[16px]">warning</span>
        <span className="text-sm font-bold text-amber-700">
          2 banks at critical stock — resupply routes active
        </span>
        <span className="ml-auto text-xs text-amber-500">Inventory synced 3 min ago</span>
      </div>

      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-black text-on-surface">Blood Logistics Network</h2>
          <p className="text-sm text-on-surface-variant mt-0.5">Cross-bank routing, cold chain monitoring, and inventory optimization</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon:'local_shipping', value:'4',     label:'Active Shipments',         color:'#3b82f6' },
          { icon:'schedule',       value:'91.4%', label:'On-Time Delivery (30d)',   color:'#16a34a' },
          { icon:'thermostat',     value:'4.6°C', label:'Avg Cold Chain Temp',      color:'#6366f1' },
          { icon:'water_drop',     value:'23',    label:'Units in Transit',         color:'#b91c1c' },
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Shipments + Forecast */}
        <div className="lg:col-span-2 space-y-5">
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Active Shipments</h3>
            {SHIPMENTS.map(s => {
              const st = STATUS_STYLE[s.status]
              return (
                <div key={s.id} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-primary text-[17px]">local_shipping</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
                        <span className="text-sm font-bold text-on-surface">{s.from}</span>
                        <span className="material-symbols-outlined text-[13px] text-on-surface-variant">arrow_forward</span>
                        <span className="text-sm font-bold text-on-surface">{s.to}</span>
                      </div>
                      <div className="flex items-center gap-2 flex-wrap text-xs text-on-surface-variant">
                        <span className="font-medium text-on-surface">{s.units}</span>
                        <span>·</span>
                        <span className={`font-bold ${s.tempOk === true ? 'text-green-600' : s.tempOk === false ? 'text-red-600' : 'text-on-surface-variant'}`}>
                          {s.tempOk !== null && (
                            <span className="material-symbols-outlined text-[12px] align-middle mr-0.5">
                              {s.tempOk ? 'check_circle' : 'error'}
                            </span>
                          )}
                          {s.temp}
                        </span>
                        <span>·</span>
                        <span>{s.vehicle}</span>
                      </div>
                    </div>
                    <div className="text-right shrink-0 space-y-1">
                      <div>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${st.cls}`}>{st.label}</span>
                      </div>
                      <p className="text-xs text-on-surface-variant">ETA {s.eta}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Demand Forecast */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">O Negative Demand Forecast — Next 7 Days</h3>
            <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-5">
              <div className="flex items-end gap-3 h-32">
                {FORECAST.map(d => {
                  const h = Math.round((d.units / maxUnits) * 100)
                  const col = FORECAST_COLOR[d.type]
                  return (
                    <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                      <span className="text-[10px] font-bold text-on-surface">{d.units}</span>
                      <div className="w-full rounded-t" style={{ height:`${h}%`, backgroundColor: col, minHeight:4 }} />
                      <span className="text-[10px] text-on-surface-variant font-medium">{d.day}</span>
                    </div>
                  )
                })}
              </div>
              <div className="flex gap-5 mt-3 pt-3 border-t border-outline-variant/30">
                {[['#dc2626','Critical'],['#d97706','High'],['#3b82f6','Moderate']].map(([c,l]) => (
                  <div key={l} className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: c }} />
                    <span className="text-[10px] text-on-surface-variant">{l}</span>
                  </div>
                ))}
                <span className="ml-auto text-[10px] text-on-surface-variant">units required</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Inventory + Map */}
        <div className="space-y-5">
          {/* Bank selector + stock */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Bank Inventory</h3>
            <div className="flex gap-2 flex-wrap">
              {BANKS.map(b => (
                <button key={b.id} onClick={() => setActiveBank(b.id)}
                  className={`text-[11px] font-bold px-2.5 py-1 rounded-lg border transition-all ${
                    activeBank === b.id
                      ? 'bg-primary text-white border-primary'
                      : 'border-outline-variant text-on-surface-variant hover:border-primary/50'
                  }`}>
                  {b.short}
                </button>
              ))}
            </div>

            {bank && (
              <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-bold text-on-surface">{bank.name}</h4>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white"
                    style={{ backgroundColor: LEVEL_COLOR[bank.level] }}>
                    {bank.level.toUpperCase()}
                  </span>
                </div>
                <div className="space-y-2">
                  {Object.entries(bank.stock).map(([bg, count]) => {
                    const pct   = Math.min(100, (count / 12) * 100)
                    const barCl = count === 0 ? '#dc2626' : count <= 2 ? '#d97706' : '#16a34a'
                    return (
                      <div key={bg}>
                        <div className="flex justify-between text-[11px] mb-0.5">
                          <span className="text-on-surface font-medium">{bg}</span>
                          <span className="font-bold" style={{ color: barCl }}>
                            {count === 0 ? 'OUT' : `${count} units`}
                          </span>
                        </div>
                        <div className="h-1.5 bg-surface-container rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width:`${Math.max(pct,0)}%`, backgroundColor: barCl }} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Route map */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Route Map</h3>
            <div className="rounded-xl overflow-hidden border border-outline-variant" style={{ height: 240 }}>
              <MapContainer center={CENTER} zoom={12} style={{ height:'100%', width:'100%' }} scrollWheelZoom={false}>
                <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://carto.com">CARTO</a>' />
                {BANKS.map(b => (
                  <CircleMarker key={b.id} center={[b.lat, b.lng]}
                    radius={activeBank === b.id ? 10 : 7}
                    pathOptions={{
                      color: activeBank === b.id ? '#fff' : LEVEL_COLOR[b.level],
                      weight: activeBank === b.id ? 3 : 1.5,
                      fillColor: LEVEL_COLOR[b.level], fillOpacity: 0.85,
                    }}>
                    <Popup>{b.name}</Popup>
                  </CircleMarker>
                ))}
                {activeRoutes.map(s => (
                  <Polyline key={s.id} positions={[s.fc, s.tc]}
                    pathOptions={{ color: STATUS_STYLE[s.status].routeColor, weight:2.5, dashArray:'6,6', opacity:0.85 }} />
                ))}
              </MapContainer>
            </div>
            <div className="flex gap-4 flex-wrap">
              {[['#16a34a','Adequate'],['#d97706','Low'],['#dc2626','Critical']].map(([c,l]) => (
                <div key={l} className="flex items-center gap-1.5 text-[10px] text-on-surface-variant">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c }} />{l}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
