import { useEffect, useState } from 'react'
import { ArrowUpRight, Cpu, Film, Gauge, Leaf, Zap } from 'lucide-react'

export type StudioPreset = 'preview' | 'balanced' | 'quality'
type Sample = {
  available: boolean; vram_used_mib?: number; vram_total_mib?: number;
  ram_used_mib?: number; ram_total_mib?: number; gpu_util_percent?: number;
  gpu_temp_c?: number; disk_free_gib: number; sample_age_seconds: number
}

export function PerformancePanel({ onPreset, selected, compactReady, enabled }: {
  onPreset: (preset: StudioPreset) => void; selected: StudioPreset | null;
  compactReady: boolean; enabled: boolean
}) {
  const [sample, setSample] = useState<Sample | null>(null)
  const [loading, setLoading] = useState(true)
  const [showcase, setShowcase] = useState<string | null>(null)
  useEffect(() => {
    let disposed = false
    const load = async () => {
      try {
        const response = await fetch('/api/system/status', { cache: 'no-store' })
        if (!response.ok) throw new Error('Hardware sample unavailable')
        const data: Sample = await response.json()
        if (!disposed) setSample(data)
      } catch { if (!disposed) setSample(null) }
      finally { if (!disposed) setLoading(false) }
    }
    void load()
    void fetch('/api/showcase', { cache: 'no-store' }).then(response => response.ok ? response.json() : null).then(data => { if (!disposed) setShowcase(data?.video_url || null) }).catch(() => {})
    const timer = window.setInterval(load, 6000)
    return () => { disposed = true; window.clearInterval(timer) }
  }, [])
  const memory = (used?: number, total?: number) => used !== undefined && total ? `${(used / 1024).toFixed(1)} / ${(total / 1024).toFixed(1)} GB` : '—'
  const ramFree = sample?.ram_total_mib && sample.ram_used_mib !== undefined ? sample.ram_total_mib - sample.ram_used_mib : null
  return <section className="studio-overview" aria-label="מצב המחשב ופרופילי יצירה">
    <div className="studio-intro"><div><span className="studio-kicker"><Film size={14} /> LOCAL VIDEO LAB <i /></span><h2>מרעיון לפריים. <em>מהמחשב שלך.</em></h2><p>בחר נקודת פתיחה, כתוב סצנה — ותן ל־H3 ליצור.</p></div><span className="studio-stamp" aria-hidden="true">H3<br/><small>STUDIO / 01</small></span></div>
    <div className="hardware-strip" aria-live="off"><span className="hardware-label"><Cpu size={16}/> עומס חי</span><span><small>GPU MEMORY</small><b dir="ltr">{memory(sample?.vram_used_mib, sample?.vram_total_mib)}</b></span><span><small>SYSTEM RAM</small><b dir="ltr">{memory(sample?.ram_used_mib, sample?.ram_total_mib)}</b></span><span><small>GPU / TEMP</small><b dir="ltr">{sample?.available ? `${sample.gpu_util_percent ?? '—'}% · ${sample.gpu_temp_c ?? '—'}°C` : '—'}</b></span><span><small>FREE DISK</small><b dir="ltr">{sample ? `${sample.disk_free_gib} GB` : '—'}</b></span></div>
    <div className="preset-heading"><span>איך תרצה להתחיל?</span><small>אפשר לשנות כל הגדרה בהמשך</small></div>
    <div className="studio-presets">
      {([
        { id: 'preview', icon: Zap, title: 'בדיקה מהירה', detail: 'Turbo · 4 סטפים · 512×288', text: 'לבדיקת רעיון ותנועה' },
        { id: 'balanced', icon: Leaf, title: 'חסכוני בזיכרון', detail: 'Turbo · ClipProj · 736×416', text: 'Encoder קטן · איכות ניסיונית' },
        { id: 'quality', icon: Gauge, title: 'איכות גבוהה', detail: 'Standard · 20 סטפים · 864×480', text: 'Encoder מקורי · רינדור ארוך יותר' },
      ] as const).map(preset => <button type="button" key={preset.id} aria-pressed={selected === preset.id} disabled={!enabled || (preset.id === 'balanced' && !compactReady)} onClick={() => onPreset(preset.id)}><preset.icon size={19}/><strong>{preset.title}</strong><small dir="ltr">{preset.detail}</small><span>{preset.text}</span><ArrowUpRight size={15}/></button>)}
    </div>
    {!enabled && <p className="hardware-note">הפרופילים זמינים במצב טקסט או פריימים. הגדרות הרפרנס והדיבוב נשארות בשליטתך.</p>}
    {ramFree !== null && ramFree < 2048 && <p className="hardware-note warning">נותרו פחות מ־2GB בזיכרון המחשב. עדיף לסגור יישומים כבדים לפני היצירה.</p>}
    {sample && sample.disk_free_gib < 20 && <p className="hardware-note warning">נותרו פחות מ־20GB בדיסק. רינדור H3 משתמש גם בדיסק לזיכרון זמני; עדיף לפנות מקום לפני יצירה נוספת.</p>}
    {!sample && <p className="hardware-note">{loading ? 'טוען נתוני חומרה…' : 'נתוני החומרה אינם זמינים כרגע.'}</p>}
    {showcase && <div className="studio-showcase"><div><span className="studio-kicker">MADE HERE / H3</span><h3>אור קטן ביער</h3><p>סרט הדוגמה · 30 שניות · שוטים מחוברים</p></div><video controls playsInline preload="metadata" src={showcase} aria-label="סרט הדוגמה: אור קטן ביער"/><a href={showcase} download="forest-light-30s.mp4">הורדת הסרט <ArrowUpRight size={15}/></a></div>}
  </section>
}
