import { useEffect, useState, type ReactNode } from 'react'
import { ArrowUpRight, Cpu, HardDrive, MemoryStick, Thermometer } from 'lucide-react'

export type HardwareSample = {
  available: boolean; vram_used_mib?: number; vram_total_mib?: number;
  ram_used_mib?: number; ram_total_mib?: number; gpu_util_percent?: number;
  gpu_temp_c?: number; disk_free_gib: number; sample_age_seconds: number
}

export function useHardware(intervalMs = 6000) {
  const [sample, setSample] = useState<HardwareSample | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let disposed = false
    const load = async () => {
      try {
        const response = await fetch('/api/system/status', { cache: 'no-store' })
        if (!response.ok) throw new Error('Hardware sample unavailable')
        const data: HardwareSample = await response.json()
        if (!disposed) setSample(data)
      } catch { if (!disposed) setSample(null) }
      finally { if (!disposed) setLoading(false) }
    }
    void load()
    const timer = window.setInterval(load, intervalMs)
    return () => { disposed = true; window.clearInterval(timer) }
  }, [intervalMs])
  return { sample, loading }
}

export function hardwareWarnings(sample: HardwareSample | null) {
  const warnings: string[] = []
  if (!sample) return warnings
  const ramFree = sample.ram_total_mib && sample.ram_used_mib !== undefined ? sample.ram_total_mib - sample.ram_used_mib : null
  if (ramFree !== null && ramFree < 2048) warnings.push('נותרו פחות מ־2GB בזיכרון המחשב. עדיף לסגור יישומים כבדים לפני היצירה.')
  if (sample.disk_free_gib < 20) warnings.push('נותרו פחות מ־20GB בדיסק. רינדור H3 משתמש גם בדיסק לזיכרון זמני.')
  return warnings
}

function Meter({ icon, label, value, ratio }: { icon: ReactNode; label: string; value: string; ratio?: number }) {
  const level = ratio === undefined ? '' : ratio > 0.92 ? 'high' : ratio > 0.75 ? 'mid' : ''
  return <div className={`hw-meter ${level}`}>
    <span className="hw-meter-label">{icon}{label}</span>
    <b dir="ltr">{value}</b>
    {ratio !== undefined && <i><em style={{ width: `${Math.round(Math.min(1, Math.max(0, ratio)) * 100)}%` }} /></i>}
  </div>
}

export function HardwarePanel({ sample, loading }: { sample: HardwareSample | null; loading: boolean }) {
  const [showcase, setShowcase] = useState<string | null>(null)
  useEffect(() => {
    let disposed = false
    void fetch('/api/showcase', { cache: 'no-store' }).then(response => response.ok ? response.json() : null)
      .then(data => { if (!disposed) setShowcase(data?.video_url || null) }).catch(() => {})
    return () => { disposed = true }
  }, [])
  const gb = (value?: number) => value === undefined ? '—' : (value / 1024).toFixed(1)
  const ratio = (used?: number, total?: number) => used !== undefined && total ? used / total : undefined
  return <section className="hw-panel" aria-label="מצב המחשב">
    <div className="hw-grid">
      <Meter icon={<Cpu size={15} />} label="זיכרון GPU" value={sample ? `${gb(sample.vram_used_mib)} / ${gb(sample.vram_total_mib)} GB` : '—'} ratio={ratio(sample?.vram_used_mib, sample?.vram_total_mib)} />
      <Meter icon={<MemoryStick size={15} />} label="זיכרון מחשב" value={sample ? `${gb(sample.ram_used_mib)} / ${gb(sample.ram_total_mib)} GB` : '—'} ratio={ratio(sample?.ram_used_mib, sample?.ram_total_mib)} />
      <Meter icon={<Thermometer size={15} />} label="עומס GPU" value={sample?.available ? `${sample.gpu_util_percent ?? '—'}% · ${sample.gpu_temp_c ?? '—'}°C` : '—'} ratio={sample?.gpu_util_percent !== undefined ? sample.gpu_util_percent / 100 : undefined} />
      <Meter icon={<HardDrive size={15} />} label="דיסק פנוי" value={sample ? `${sample.disk_free_gib} GB` : '—'} />
    </div>
    {hardwareWarnings(sample).map(warning => <p className="hw-note warning" key={warning}>{warning}</p>)}
    {!sample && <p className="hw-note">{loading ? 'טוען נתוני חומרה…' : 'נתוני החומרה אינם זמינים כרגע.'}</p>}
    {showcase && <div className="studio-showcase"><div><h3>סרט הדוגמה</h3></div><video controls playsInline preload="metadata" src={showcase} aria-label="סרט הדוגמה" /><a href={showcase} download>הורדת הסרט <ArrowUpRight size={15} /></a></div>}
  </section>
}
