import { useState } from 'react'

const BLOOD_GROUPS = [
  'O Negative','O Positive','A Negative','A Positive',
  'B Negative','B Positive','AB Negative','AB Positive',
]
const BG_COLOR = {
  'O Negative':'#b91c1c','O Positive':'#ef4444',
  'A Negative':'#1d4ed8','A Positive':'#3b82f6',
  'B Negative':'#7c3aed','B Positive':'#8b5cf6',
  'AB Negative':'#c2410c','AB Positive':'#f97316',
}

const CAMPAIGNS = [
  { id:'c1', name:'O Negative Emergency Drive', bg:'O Negative', platform:'WhatsApp + Instagram', status:'active', reach:4820, rsvps:143, donated:67, target:200, icon:'campaign' },
  { id:'c2', name:'World Blood Donor Day 2026', bg:null, platform:'Instagram + Twitter', status:'active', reach:18400, rsvps:891, donated:312, target:1000, icon:'favorite' },
  { id:'c3', name:'B Negative Awareness Post', bg:'B Negative', platform:'WhatsApp Broadcast', status:'completed', reach:2340, rsvps:78, donated:41, target:80, icon:'broadcast_on_personal' },
  { id:'c4', name:'Monsoon Season Prep Drive', bg:null, platform:'All Platforms', status:'scheduled', reach:0, rsvps:0, donated:0, target:500, icon:'schedule' },
]

const POSTS = [
  { id:'p1', platform:'WhatsApp', icon:'chat', color:'#25D366', time:'2h ago', reach:1240, replies:89, committed:34,
    msg:'🩸 Blood Warriors Alert: Hyderabad mein O Negative ka stock critically low hai. Ek donation 3 lives bacha sakti hai. Reply HAAN for slot. 🙏' },
  { id:'p2', platform:'Instagram', icon:'photo_camera', color:'#E1306C', time:'5h ago', reach:6820, replies:412, committed:0,
    msg:'❤️ 1 in 7 patients needs blood. Aaj ka chhota kadam kal ka bada farak bana sakta hai. #BloodWarriors #Hyderabad #DonateBlood' },
  { id:'p3', platform:'Twitter / X', icon:'alternate_email', color:'#1DA1F2', time:'1d ago', reach:3100, replies:201, committed:0,
    msg:'URGENT: B- blood needed at KIMS Secunderabad before 6 PM. DM us — Blood Warriors sab arrange kar denge. 🙏 #BloodDonation' },
]

const TEMPLATES = {
  'O Negative': {
    whatsapp: '🩸 Blood Warriors Emergency!\n\nO Negative critically short — stock sirf 6 hours ka bacha hai.\n\nEligibility check:\n✓ 18–65 years\n✓ Last donation 90+ din pehle\n✓ Nearby Hyderabad\n\nReply HAAN — slot + transport arrange kar dete hain. 🙏',
    instagram: 'Every 2 seconds, someone needs blood. Today, that someone needs YOUR type — O Negative. Be the reason someone sees tomorrow.\n\n#BloodWarriors #ONegative #Hyderabad #DonateBlood #SaveLives',
    twitter: '🚨 CRITICAL: O- stock < 6 hrs in Hyderabad. If you\'re O- and eligible, DM now. Slot + transport — zero friction. Just show up.\n\n#DonateBlood #BloodWarriors',
  },
  'B Negative': {
    whatsapp: '🩸 B Negative donors needed urgently!\n\nAaj KIMS Secunderabad mein B Negative chahiye. Sirf 3 units.\n\nReply READY — hum sab coordinate kar dete hain. 🙏',
    instagram: 'B Negative is rare. So are heroes. If you\'re B-, you have the power to save a life today. Swipe to learn how.\n\n#BloodWarriors #BNegative #RareBlood #Hyderabad',
    twitter: 'B- donors in Secunderabad — DM now. Patient waiting at KIMS. 3 units needed. We arrange everything.\n\n5 minutes → one life. #BloodDonation',
  },
}
const DEFAULT_TPL = {
  whatsapp: '🩸 Blood Warriors Appeal!\n\nHyderabad mein aaj aapki zaroorat hai. Agar eligible ho, ek reply pe sab arrange ho jayega.\n\nReply HAAN — hum connect karte hain. 🙏',
  instagram: 'Your blood can give someone another birthday, another anniversary, another ordinary Tuesday. Donate today.\n\n#BloodWarriors #DonateBlood #Hyderabad',
  twitter: 'Blood donors in Hyderabad — someone needs you today. DM @BloodWarriorsHYD. Zero hassle, full support.\n\n#DonateBlood #BloodWarriors',
}

export default function CampaignEngine() {
  const [selectedBG, setSelectedBG] = useState('O Negative')
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated]   = useState(null)
  const [deployed, setDeployed]     = useState(false)

  const generate = () => {
    setGenerating(true)
    setGenerated(null)
    setTimeout(() => { setGenerated(TEMPLATES[selectedBG] || DEFAULT_TPL); setGenerating(false) }, 1600)
  }
  const deploy = () => { setDeployed(true); setTimeout(() => setDeployed(false), 2500) }

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-black text-on-surface">Social Awareness Engine</h2>
          <p className="text-sm text-on-surface-variant mt-0.5">Automated donor outreach — posts, RSVP drives, broadcast campaigns</p>
        </div>
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 px-3 py-1.5 rounded-full">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs font-semibold text-green-700">2 campaigns live</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon:'visibility',   value:'23.6K', label:'Total Reach (7d)',          color:'#3b82f6' },
          { icon:'how_to_reg',   value:'1,112', label:'RSVPs Collected',           color:'#16a34a' },
          { icon:'water_drop',   value:'420',   label:'Donations Triggered',       color:'#b91c1c' },
          { icon:'trending_up',  value:'37.8%', label:'RSVP → Donation Rate',      color:'#d97706' },
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
        {/* Campaign cards */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Active Campaigns</h3>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            {CAMPAIGNS.map(c => {
              const color = c.bg ? BG_COLOR[c.bg] : '#6b7280'
              const pct   = c.target > 0 ? Math.min(100, Math.round((c.rsvps / c.target) * 100)) : 0
              const sCls  = c.status === 'active' ? 'bg-green-100 text-green-700'
                : c.status === 'completed' ? 'bg-gray-100 text-gray-500'
                : 'bg-amber-100 text-amber-700'
              return (
                <div key={c.id} className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden hover:border-primary transition-all">
                  <div className="h-1" style={{ backgroundColor: color }} />
                  <div className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="material-symbols-outlined text-[17px]" style={{ color }}>{c.icon}</span>
                          <h4 className="font-bold text-sm text-on-surface truncate">{c.name}</h4>
                        </div>
                        <p className="text-xs text-on-surface-variant">{c.platform}</p>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ml-2 shrink-0 ${sCls}`}>
                        {c.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 mb-3">
                      {[
                        { v: c.reach > 0 ? `${(c.reach/1000).toFixed(1)}K` : '—', l:'Reach' },
                        { v: c.rsvps  || '—', l:'RSVPs' },
                        { v: c.donated || '—', l:'Donated' },
                      ].map(({ v, l }) => (
                        <div key={l} className="text-center">
                          <p className="text-base font-black text-on-surface">{v}</p>
                          <p className="text-[10px] text-on-surface-variant">{l}</p>
                        </div>
                      ))}
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-on-surface-variant mb-1">
                        <span>RSVP target</span><span>{pct}%</span>
                      </div>
                      <div className="h-1.5 bg-surface-container rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width:`${pct}%`, backgroundColor: color }} />
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Post Generator */}
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 h-fit">
          <div className="flex items-center gap-2 mb-4">
            <span className="material-symbols-outlined text-secondary text-[18px]" style={{ fontVariationSettings:"'FILL' 1" }}>auto_awesome</span>
            <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">AI Post Generator</h4>
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-on-surface-variant block mb-1">Blood Group in Focus</label>
              <select value={selectedBG} onChange={e => setSelectedBG(e.target.value)}
                className="w-full text-sm bg-surface-container border border-outline-variant rounded-lg px-3 py-2 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary">
                {BLOOD_GROUPS.map(bg => <option key={bg}>{bg}</option>)}
              </select>
            </div>
            <button onClick={generate} disabled={generating}
              className="w-full py-2.5 bg-primary text-white text-sm font-bold rounded-lg hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-2">
              {generating
                ? <><span className="material-symbols-outlined text-[15px] animate-spin">sync</span>Generating…</>
                : <><span className="material-symbols-outlined text-[15px]">auto_awesome</span>Generate Posts</>}
            </button>

            {generated && (
              <div className="space-y-2">
                {[
                  { key:'whatsapp',  icon:'chat',            color:'#25D366', label:'WhatsApp'  },
                  { key:'instagram', icon:'photo_camera',    color:'#E1306C', label:'Instagram' },
                  { key:'twitter',   icon:'alternate_email', color:'#1DA1F2', label:'X / Twitter' },
                ].map(({ key, icon, color, label }) => (
                  <div key={key} className="rounded-lg border border-outline-variant/60 p-3" style={{ borderLeft:`3px solid ${color}` }}>
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <span className="material-symbols-outlined text-[13px]" style={{ color }}>{icon}</span>
                      <span className="text-[10px] font-bold text-on-surface-variant uppercase">{label}</span>
                    </div>
                    <p className="text-[11px] text-on-surface leading-relaxed whitespace-pre-line">{generated[key]}</p>
                  </div>
                ))}
                <button onClick={deploy}
                  className={`w-full py-2 text-xs font-bold rounded-lg flex items-center justify-center gap-1.5 transition-all ${
                    deployed ? 'bg-green-600 text-white' : 'border border-primary text-primary hover:bg-primary/5'
                  }`}>
                  <span className="material-symbols-outlined text-[13px]">{deployed ? 'check_circle' : 'send'}</span>
                  {deployed ? 'Scheduled!' : 'Schedule & Deploy All'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Recent Broadcasts */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">Recent Broadcasts</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {POSTS.map(p => (
            <div key={p.id} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: p.color + '22' }}>
                  <span className="material-symbols-outlined text-[15px]" style={{ color: p.color }}>{p.icon}</span>
                </div>
                <span className="text-xs font-bold text-on-surface">{p.platform}</span>
                <span className="text-[10px] text-on-surface-variant ml-auto">{p.time}</span>
              </div>
              <p className="text-xs text-on-surface leading-relaxed mb-3 pl-3 italic" style={{ borderLeft:`2px solid ${p.color}` }}>
                {p.msg}
              </p>
              <div className="flex gap-4 text-[11px] text-on-surface-variant flex-wrap">
                <span><b className="text-on-surface">{(p.reach/1000).toFixed(1)}K</b> reached</span>
                <span><b className="text-on-surface">{p.replies}</b> replies</span>
                {p.committed > 0 && <span><b className="text-green-600">{p.committed}</b> committed</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
