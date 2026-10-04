import React, { useEffect, useState, useRef } from 'react'
import {
  Sparkles,
  Image as ImageIcon,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
  Download,
  Trash2,
  Clapperboard,
  RefreshCw,
  X,
  Plus,
  Copy,
  Check,
  ZoomIn,
  LoaderCircle,
  AlertCircle,
  Clock,
} from 'lucide-react'

export type AspectRatio = '1:1' | '16:9' | '9:16' | '4:3' | '3:4'

export type ImageJob = {
  id: string
  prompt: string
  negative_prompt?: string
  model_profile: 'standard' | 'viggle_turbo'
  aspect_ratio: AspectRatio
  width: number
  height: number
  steps: number
  cfg: number
  seed: string
  status: 'queued' | 'starting' | 'running' | 'completed' | 'failed' | 'canceled'
  position: number
  progress: number
  step: number
  total_steps: number
  reference_images?: string[]
  output_path?: string
  image_url?: string
  error?: string
  eta_seconds?: number | null
  generation_seconds?: number
  metrics?: {
    generation_seconds?: number
    peak_gpu?: number
  }
  created_at: string
  started_at?: string
  finished_at?: string
}

function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds))
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainder = seconds % 60
  if (hours) return `${hours}:${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`
  return `${minutes}:${String(remainder).padStart(2, '0')}`
}

function getJobDuration(job: ImageJob): number | undefined {
  if (job.metrics?.generation_seconds && job.metrics.generation_seconds > 0) {
    return job.metrics.generation_seconds
  }
  if (job.generation_seconds && job.generation_seconds > 0) {
    return job.generation_seconds
  }
  if (job.finished_at && job.started_at) {
    const start = Date.parse(job.started_at)
    const end = Date.parse(job.finished_at)
    if (!isNaN(start) && !isNaN(end) && end >= start) {
      return Math.max(1, Math.round((end - start) / 1000))
    }
  }
  return undefined
}

export type ImageGenStudioProps = {
  csrf: string
  qwenImageReady?: boolean
  onUseInStudio: (imageFile: File, promptText?: string) => void
}

const ASPECT_RATIO_PRESETS: { id: AspectRatio; label: string; dims: string; ratio: string }[] = [
  { id: '1:1', label: 'ריבוע', dims: '1024×1024', ratio: '1:1' },
  { id: '16:9', label: 'לרוחב', dims: '1344×768', ratio: '16:9' },
  { id: '9:16', label: 'לאורך', dims: '768×1344', ratio: '9:16' },
  { id: '4:3', label: 'סטנדרטי', dims: '1152×896', ratio: '4:3' },
  { id: '3:4', label: 'גבוה', dims: '896×1152', ratio: '3:4' },
]

export function ImageGenStudio({ csrf, qwenImageReady = true, onUseInStudio }: ImageGenStudioProps) {
  const [prompt, setPrompt] = useState('')
  const [modelProfile, setModelProfile] = useState<'standard' | 'viggle_turbo'>('standard')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [showNegative, setShowNegative] = useState(false)
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('1:1')
  const [steps, setSteps] = useState(25)
  const [cfg, setCfg] = useState(4.0)
  const [seed, setSeed] = useState('')
  const [referenceImages, setReferenceImages] = useState<File[]>([])
  const [refPreviews, setRefPreviews] = useState<string[]>([])
  const [showAdvanced, setShowAdvanced] = useState(false)

  const [imageJobs, setImageJobs] = useState<ImageJob[]>([])
  const [qwenImageTurboReady, setQwenImageTurboReady] = useState(false)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [transferringId, setTransferringId] = useState<string | null>(null)
  const [lightboxJob, setLightboxJob] = useState<ImageJob | null>(null)

  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Generate object URLs for reference images
  useEffect(() => {
    const urls = referenceImages.map(file => URL.createObjectURL(file))
    setRefPreviews(urls)
    return () => {
      urls.forEach(url => URL.revokeObjectURL(url))
    }
  }, [referenceImages])

  // Fetch image jobs
  const fetchJobs = async () => {
    try {
      const res = await fetch('/api/image-jobs', { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data.image_jobs)) {
          setImageJobs(data.image_jobs)
        }
        if (typeof data.qwen_image_turbo_ready === 'boolean') {
          setQwenImageTurboReady(data.qwen_image_turbo_ready)
        }
      }
    } catch {
      // transient network error
    }
  }

  useEffect(() => {
    void fetchJobs()
    const timer = setInterval(() => {
      void fetchJobs()
    }, 2500)
    return () => clearInterval(timer)
  }, [])

  // Handle adding reference images (up to 3)
  const handleAddFiles = (newFiles: FileList | null) => {
    if (!newFiles) return
    const incoming = Array.from(newFiles).filter(f => f.type.startsWith('image/'))
    setReferenceImages(prev => {
      const combined = [...prev, ...incoming].slice(0, 3)
      return combined
    })
  }

  const handleRemoveRef = (index: number) => {
    setReferenceImages(prev => prev.filter((_, i) => i !== index))
  }

  // Submit job
  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) return
    setError('')
    setSubmitting(true)

    try {
      const formData = new FormData()
      formData.append('prompt', prompt.trim())
      formData.append('model_profile', modelProfile)
      if (modelProfile !== 'viggle_turbo' && negativePrompt.trim()) {
        formData.append('negative_prompt', negativePrompt.trim())
      }
      formData.append('aspect_ratio', aspectRatio)
      formData.append('steps', String(modelProfile === 'viggle_turbo' ? 4 : steps))
      formData.append('cfg', String(modelProfile === 'viggle_turbo' ? 1.0 : cfg))
      if (seed.trim()) {
        formData.append('seed', seed.trim())
      }
      referenceImages.forEach(file => {
        formData.append('reference_images', file)
      })

      const headers: Record<string, string> = {}
      if (csrf) {
        headers['X-CSRF-Token'] = csrf
      }

      const res = await fetch('/api/image-jobs', {
        method: 'POST',
        headers,
        body: formData,
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || 'Failed to submit image job')
      }

      await fetchJobs()
    } catch (err: any) {
      setError(err?.message || 'Error creating image job')
    } finally {
      setSubmitting(false)
    }
  }

  // Cancel job
  const handleCancel = async (jobId: string) => {
    try {
      const headers: Record<string, string> = {}
      if (csrf) headers['X-CSRF-Token'] = csrf
      await fetch(`/api/image-jobs/${jobId}/cancel`, { method: 'POST', headers })
      await fetchJobs()
    } catch {
      // ignore
    }
  }

  // Delete job
  const handleDelete = async (jobId: string) => {
    try {
      const headers: Record<string, string> = {}
      if (csrf) headers['X-CSRF-Token'] = csrf
      await fetch(`/api/image-jobs/${jobId}`, { method: 'DELETE', headers })
      setImageJobs(prev => prev.filter(j => j.id !== jobId))
    } catch {
      // ignore
    }
  }

  // Use in Studio I2V
  const handleUseInStudio = async (job: ImageJob) => {
    if (!job.image_url) return
    setTransferringId(job.id)
    try {
      const res = await fetch(job.image_url)
      if (!res.ok) throw new Error('Could not load image file')
      const blob = await res.blob()
      const file = new File([blob], `qwen_${job.id}.png`, { type: 'image/png' })
      onUseInStudio(file, job.prompt)
    } catch (err: any) {
      setError(`Failed to transfer image to studio: ${err?.message || err}`)
    } finally {
      setTransferringId(null)
    }
  }

  const copyPrompt = (id: string, text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 1500)
  }

  const activeJob = imageJobs.find(j => j.status === 'running' || j.status === 'starting' || j.status === 'queued')
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    if (!activeJob) return
    setNow(Date.now())
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [Boolean(activeJob)])

  const activeElapsedSeconds = activeJob?.started_at
    ? Math.max(0, Math.round((now - Date.parse(activeJob.started_at)) / 1000))
    : undefined
  const isViggleTurbo = modelProfile === 'viggle_turbo'
  const selectedModelReady = isViggleTurbo ? qwenImageTurboReady : qwenImageReady

  return (
    <div className="image-gen-studio">
      {/* Model status banner */}
      <div className="image-gen-header-bar">
        <div className="model-info">
          <div className="model-badge">
            <Sparkles size={14} />
            <span>{isViggleTurbo ? 'Qwen-Image-2.1 Viggle Turbo' : 'Qwen-Image-2.1 GGUF'}</span>
          </div>
          <span className="model-pill">{isViggleTurbo ? 'Q4_K_M Turbo (4.19 GB)' : 'Q4_K_M (4.6 GB)'}</span>
          <span className="model-pill">8B Int8 Text Encoder</span>
          {selectedModelReady ? (
            <span className="status-pill ready">● מוכן ליצירה</span>
          ) : (
            <span className="status-pill warning">● {isViggleTurbo ? 'קובץ Turbo לא מותקן' : 'דגמי Qwen לא מותקנים'}</span>
          )}
        </div>
        <button
          type="button"
          className="icon-button"
          onClick={() => { void fetchJobs() }}
          title="רענן רשימה"
          aria-label="Refresh"
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {error && (
        <div className="error-banner" style={{ margin: '8px 0 14px' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
          <button type="button" onClick={() => setError('')} style={{ background: 'transparent', border: 0, color: 'inherit', marginLeft: 'auto', cursor: 'pointer' }}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* Composer Section */}
      <section className="composer image-composer">
        <div className="eyebrow">
          <ImageIcon size={16} />
          <span>יצירת תמונה חדשה (Text / Reference to Image)</span>
        </div>

        <form onSubmit={handleGenerate}>
          <div className="image-model-section">
            <div className="section-title">
              <span>מודל תמונה</span>
              <small>בחרי בין המודל הרגיל לגרסת 4 הצעדים</small>
            </div>
            <div className="image-model-options">
              <button
                type="button"
                className={`image-model-option ${!isViggleTurbo ? 'active' : ''}`}
                aria-pressed={!isViggleTurbo}
                onClick={() => setModelProfile('standard')}
              >
                <strong>Qwen-Image-2.1</strong>
                <span>רגיל · Q4_K_M</span>
              </button>
              <button
                type="button"
                className={`image-model-option ${isViggleTurbo ? 'active' : ''}`}
                aria-pressed={isViggleTurbo}
                onClick={() => setModelProfile('viggle_turbo')}
              >
                <strong>Viggle Turbo</strong>
                <span>{qwenImageTurboReady ? '4 צעדים · CFG 1' : 'קובץ המודל חסר'}</span>
              </button>
            </div>
            {isViggleTurbo && (
              <p className="image-turbo-note">
                מצב Turbo נעול ל־4 צעדים ו־CFG 1.0. הפרומפט השלילי לא נשלח. זו גרסת preview.
              </p>
            )}
          </div>

          {/* Prompt input */}
          <div className="prompt-container">
            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder="תאר את התמונה שברצונך ליצור בפירוט (באנגלית או עברית)…"
              rows={4}
              required
            />
            <div className="composer-meta">
              <span>{prompt.length} תווים</span>
              {prompt && (
                <button
                  type="button"
                  className="link-button"
                  onClick={() => setPrompt('')}
                  style={{ color: '#88948c', fontSize: '11px', background: 'transparent', border: 0, cursor: 'pointer' }}
                >
                  נקה
                </button>
              )}
            </div>
          </div>

          {/* Negative prompt toggle */}
          {!isViggleTurbo && (
            <div className="collapsible-section">
              <button
                type="button"
                className="section-toggle-button"
                onClick={() => setShowNegative(prev => !prev)}
              >
                <span>פרומפט שלילי (Negative Prompt)</span>
                {showNegative ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {showNegative && (
                <div className="collapsible-content">
                  <input
                    type="text"
                    className="styled-input"
                    value={negativePrompt}
                    onChange={e => setNegativePrompt(e.target.value)}
                    placeholder="blurry, low quality, distorted, extra limbs, artifacts..."
                  />
                </div>
              )}
            </div>
          )}

          {/* Reference Images Section */}
          <div className="reference-section">
            <div className="section-title">
              <span>תמונות רפרנס (אופציונלי - עד 3 תמונות)</span>
              <small>לשמירה על זהות, סגנון או עריכת תמונה קיימת</small>
            </div>

            <div className="ref-thumbnails-container">
              {refPreviews.map((url, idx) => (
                <div key={idx} className="ref-thumbnail-card">
                  <img src={url} alt={`Reference ${idx + 1}`} />
                  <button
                    type="button"
                    className="ref-remove-btn"
                    onClick={() => handleRemoveRef(idx)}
                    title="הסר תמונה"
                  >
                    <X size={12} />
                  </button>
                  <span className="ref-number">#{idx + 1}</span>
                </div>
              ))}

              {referenceImages.length < 3 && (
                <label className="ref-upload-button">
                  <input
                    type="file"
                    ref={fileInputRef}
                    accept="image/jpeg,image/png,image/webp"
                    onChange={e => {
                      handleAddFiles(e.target.files)
                      if (fileInputRef.current) fileInputRef.current.value = ''
                    }}
                    style={{ display: 'none' }}
                  />
                  <Plus size={20} />
                  <span>הוסף רפרנס</span>
                </label>
              )}
            </div>
          </div>

          {/* Aspect Ratio Selector */}
          <div className="aspect-ratio-section">
            <div className="section-title">
              <span>יחס ממדים ורזולוציה</span>
              <small>Native Qwen Latent Resolution</small>
            </div>
            <div className="aspect-ratio-grid">
              {ASPECT_RATIO_PRESETS.map(preset => (
                <button
                  key={preset.id}
                  type="button"
                  className={`aspect-card ${aspectRatio === preset.id ? 'active' : ''}`}
                  onClick={() => setAspectRatio(preset.id)}
                >
                  <span className="aspect-ratio-preview" data-ratio={preset.ratio} />
                  <strong>{preset.label}</strong>
                  <span className="aspect-dims">{preset.dims}</span>
                  <small className="aspect-ratio-tag">{preset.ratio}</small>
                </button>
              ))}
            </div>
          </div>

          {/* Advanced Settings Accordion */}
          <div className="collapsible-section" style={{ marginTop: '12px' }}>
            <button
              type="button"
              className="section-toggle-button"
              onClick={() => setShowAdvanced(prev => !prev)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <SlidersHorizontal size={14} />
                <span>הגדרות מתקדמות (Steps, CFG, Seed)</span>
              </div>
              {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showAdvanced && (
              <div className="advanced-controls-grid">
                <div className="control-field">
                  <div className="field-header">
                    <span>צעדי דגימה (Steps)</span>
                    <strong className="field-value">{isViggleTurbo ? 4 : steps}</strong>
                  </div>
                  <input
                    type="range"
                    min={isViggleTurbo ? 4 : 10}
                    max={isViggleTurbo ? 4 : 50}
                    step={1}
                    value={isViggleTurbo ? 4 : steps}
                    onChange={e => setSteps(Number(e.target.value))}
                    disabled={isViggleTurbo}
                    className="styled-range"
                  />
                  <div className="range-hints">
                    {isViggleTurbo ? (
                      <span>Viggle Turbo דורש בדיוק 4 צעדים</span>
                    ) : (
                      <><span>10 (מהיר)</span><span>25 (מומלץ)</span><span>50 (מדויק)</span></>
                    )}
                  </div>
                </div>

                <div className="control-field">
                  <div className="field-header">
                    <span>עוצמת הנחיה (CFG Scale)</span>
                    <strong className="field-value">{(isViggleTurbo ? 1.0 : cfg).toFixed(1)}</strong>
                  </div>
                  <input
                    type="range"
                    min={1.0}
                    max={10.0}
                    step={0.5}
                    value={isViggleTurbo ? 1.0 : cfg}
                    onChange={e => setCfg(Number(e.target.value))}
                    disabled={isViggleTurbo}
                    className="styled-range"
                  />
                  <div className="range-hints">
                    {isViggleTurbo ? (
                      <span>Viggle Turbo דורש CFG 1.0</span>
                    ) : (
                      <><span>2.0 (חופשי)</span><span>4.0 (ברירת מחדל)</span><span>8.0 (קפדני)</span></>
                    )}
                  </div>
                </div>

                <div className="control-field full-width">
                  <div className="field-header">
                    <span>סיד (Seed)</span>
                    <small>השאר ריק לבחירה אקראית</small>
                  </div>
                  <input
                    type="number"
                    className="styled-input"
                    value={seed}
                    onChange={e => setSeed(e.target.value)}
                    placeholder="Random"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Submit Button */}
          <div className="action-row" style={{ marginTop: '16px' }}>
            <button
              type="submit"
              className="create-button"
              disabled={submitting || !prompt.trim() || !selectedModelReady}
            >
              {submitting ? (
                <>
                  <LoaderCircle size={18} className="spinner" />
                  <span>שולח למנוע היצירה…</span>
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  <span>{isViggleTurbo ? 'צור תמונה עם Viggle Turbo' : 'צור תמונה עם Qwen-Image-2.1'}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </section>

      {/* Live Active Job Card */}
      {activeJob && (
        <section className="active-image-job-card">
          <div className="active-job-header">
            <div className="active-job-info">
              <span className={`status-dot ${activeJob.status}`} />
              <strong>
                {activeJob.status === 'queued' && 'ממתין בתור (Queued)…'}
                {activeJob.status === 'starting' && 'מאתחל מודל בזיכרון…'}
                {activeJob.status === 'running' && 'מייצר תמונה (Generating)…'}
              </strong>
            </div>
            <button
              type="button"
              className="cancel-btn"
              onClick={() => handleCancel(activeJob.id)}
            >
              ביטול
            </button>
          </div>

          <p className="active-job-prompt">{activeJob.prompt}</p>

          <div className="progress-bar-container">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.round((activeJob.progress || 0) * 100)}%` }}
            />
          </div>

          <div className="active-job-meta">
            <span>
              {activeJob.step > 0 && activeJob.total_steps > 0
                ? `שלב ${activeJob.step} מתוך ${activeJob.total_steps} (${Math.round((activeJob.progress || 0) * 100)}%)`
                : `${Math.round((activeJob.progress || 0) * 100)}%`}
            </span>
            <span className="active-job-timing">
              <Clock size={12} />
              <span>
                {activeElapsedSeconds !== undefined ? `עבר ${formatDuration(activeElapsedSeconds)}` : ''}
                {activeJob.eta_seconds !== null && activeJob.eta_seconds !== undefined ? ` · נשאר ~${formatDuration(activeJob.eta_seconds)}` : ''}
              </span>
            </span>
            <span>{activeJob.aspect_ratio} ({activeJob.width}×{activeJob.height})</span>
          </div>
        </section>
      )}

      {/* Results Gallery Section */}
      <section className="image-results-section">
        <div className="section-heading-row">
          <div>
            <span className="eyebrow">גלריית תמונות</span>
            <h2>תוצאות מחולל התמונות ({imageJobs.length})</h2>
          </div>
        </div>

        {imageJobs.length === 0 ? (
          <div className="empty-state-box">
            <ImageIcon size={36} />
            <p>אין עדיין תמונות שנוצרו. הזן פרומפט למעלה ולחץ על "צור תמונה"!</p>
          </div>
        ) : (
          <div className="image-jobs-grid">
            {imageJobs.map(job => (
              <div key={job.id} className={`image-card ${job.status}`}>
                {job.status === 'completed' && job.image_url ? (
                  <div
                    className="image-preview-wrapper"
                    onClick={() => setLightboxJob(job)}
                  >
                    <img src={job.image_url} alt={job.prompt} loading="lazy" />
                    <div className="image-zoom-overlay">
                      <ZoomIn size={24} />
                    </div>
                  </div>
                ) : (
                  <div className="image-placeholder-wrapper">
                    {job.status === 'failed' ? (
                      <div className="job-status-msg failed">
                        <AlertCircle size={28} />
                        <strong>נכשל</strong>
                        <p>{job.error || 'שגיאה בלתי צפויה'}</p>
                      </div>
                    ) : job.status === 'canceled' ? (
                      <div className="job-status-msg canceled">
                        <X size={28} />
                        <strong>בוטל</strong>
                      </div>
                    ) : (
                      <div className="job-status-msg running">
                        <LoaderCircle size={28} className="spinner" />
                        <strong>מעבד…</strong>
                        <small>{Math.round((job.progress || 0) * 100)}% {job.step > 0 ? `(${job.step}/${job.total_steps})` : ''}</small>
                        {job.started_at && (
                          <small className="running-timer">
                            עבר {formatDuration(Math.max(0, Math.round((now - Date.parse(job.started_at)) / 1000)))}
                            {job.eta_seconds !== null && job.eta_seconds !== undefined && ` · נשאר ~${formatDuration(job.eta_seconds)}`}
                          </small>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="image-card-body">
                  <p className="image-card-prompt" title={job.prompt}>
                    {job.prompt}
                  </p>

                  <div className="image-card-tags">
                    <span className="tag-pill">{job.aspect_ratio}</span>
                    <span className="tag-pill">{job.width}×{job.height}</span>
                    <span className="tag-pill">{job.model_profile === 'viggle_turbo' ? 'Viggle Turbo' : 'Qwen רגיל'}</span>
                    <span className="tag-pill">{job.steps} צעדים</span>
                    <span className="tag-pill">CFG {job.cfg}</span>
                    {getJobDuration(job) !== undefined && (
                      <span className="tag-pill duration-pill" title={`זמן ג'ינרוט כולל: ${formatDuration(getJobDuration(job)!)}`}>
                        <Clock size={10} /> {formatDuration(getJobDuration(job)!)}
                      </span>
                    )}
                  </div>

                  <div className="image-card-actions">
                    {job.status === 'completed' && job.image_url && (
                      <>
                        <button
                          type="button"
                          className="studio-handoff-btn"
                          disabled={transferringId === job.id}
                          onClick={() => handleUseInStudio(job)}
                          title="העבר תמונה זו ל-Studio כדי ליצור ממנה סרטון (Image-to-Video)"
                        >
                          {transferringId === job.id ? (
                            <LoaderCircle size={14} className="spinner" />
                          ) : (
                            <Clapperboard size={14} />
                          )}
                          <span>השתמש ב-Studio (I2V)</span>
                        </button>

                        <a
                          href={job.image_url}
                          download={`qwen_${job.id}.png`}
                          className="card-action-icon-btn"
                          title="הורד תמונה למחשב"
                        >
                          <Download size={14} />
                        </a>
                      </>
                    )}

                    <button
                      type="button"
                      className="card-action-icon-btn"
                      onClick={() => copyPrompt(job.id, job.prompt)}
                      title="העתק פרומפט"
                    >
                      {copiedId === job.id ? <Check size={14} color="#8ec59a" /> : <Copy size={14} />}
                    </button>

                    <button
                      type="button"
                      className="card-action-icon-btn danger"
                      onClick={() => handleDelete(job.id)}
                      title="מחק"
                    >
                      <Trash2 size={14} />
                    </button>

                    {getJobDuration(job) !== undefined && (
                      <span className="elapsed" title="זמן ג'ינרוט כולל">
                        נוצר תוך {formatDuration(getJobDuration(job)!)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Fullscreen Lightbox Modal */}
      {lightboxJob && (
        <div className="lightbox-backdrop" onClick={() => setLightboxJob(null)}>
          <div className="lightbox-modal" onClick={e => e.stopPropagation()}>
            <button
              type="button"
              className="lightbox-close-btn"
              onClick={() => setLightboxJob(null)}
              aria-label="Close"
            >
              <X size={20} />
            </button>

            <div className="lightbox-image-container">
              <img src={lightboxJob.image_url} alt={lightboxJob.prompt} />
            </div>

            <div className="lightbox-footer">
              <p className="lightbox-prompt">{lightboxJob.prompt}</p>
              <div className="lightbox-meta-row">
                <span className="tag-pill">{lightboxJob.aspect_ratio} ({lightboxJob.width}×{lightboxJob.height})</span>
                <span className="tag-pill">{lightboxJob.model_profile === 'viggle_turbo' ? 'Viggle Turbo' : 'Qwen רגיל'}</span>
                <span className="tag-pill">{lightboxJob.steps} צעדים</span>
                <span className="tag-pill">CFG {lightboxJob.cfg}</span>
                {getJobDuration(lightboxJob) !== undefined && (
                  <span className="tag-pill duration-pill">
                    <Clock size={11} /> נוצר תוך {formatDuration(getJobDuration(lightboxJob)!)}
                  </span>
                )}
              </div>
              <div className="lightbox-actions">
                <button
                  type="button"
                  className="studio-handoff-btn"
                  onClick={() => {
                    handleUseInStudio(lightboxJob)
                    setLightboxJob(null)
                  }}
                >
                  <Clapperboard size={15} />
                  <span>השתמש ב-Studio עבור וידאו (I2V)</span>
                </button>

                <a
                  href={lightboxJob.image_url}
                  download={`qwen_${lightboxJob.id}.png`}
                  className="create-button"
                  style={{ height: '38px', padding: '0 14px', textDecoration: 'none', fontSize: '13px' }}
                >
                  <Download size={15} />
                  <span>הורד תמונה מקורית</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
