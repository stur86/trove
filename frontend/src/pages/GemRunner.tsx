/**
 * GemRunner — run a gem by filling its arguments and streaming the output.
 *
 * Phase 1 (form): Dynamic form built from UserTask.args. StringArg → TextInput.
 * ChoiceArg → Select. has_image → image picker button (modal: choose file / take
 * photo). has_audio → audio picker button (modal: choose file / record) — only
 * shown when the active model supports audio (capabilities.audio).
 *
 * Phase 2 (output): Form collapses to a summary bar showing arg values and any
 * media attachments. Clicking the bar re-expands the form. Spinner shown until
 * first token arrives. Output streams into a scrolling text area. "Run again"
 * re-submits.
 */
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Button, Label, Modal, ModalBody, ModalHeader, Select, Spinner, TextInput } from 'flowbite-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { gemsApi, readSSEStream, type UserTask } from '../api/tasks'
import { appApi } from '../api/app'
import GemIcon from '../components/GemIcon'
import { useLocale, useTranslation } from '../i18n'

type Phase = 'form' | 'running' | 'done'

export default function GemRunner() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation(useLocale())
  const [gem, setGem] = useState<UserTask | null>(null)
  const [loadError, setLoadError] = useState(false)

  // Form state: keyed by arg name
  const [values, setValues] = useState<Record<string, string>>({})
  const [phase, setPhase] = useState<Phase>('form')
  const [output, setOutput] = useState('')
  const outputRef = useRef<HTMLDivElement>(null)

  // Capabilities — whether the active model supports audio
  const [capabilities, setCapabilities] = useState<{ audio: boolean }>({ audio: false })

  // Image state
  const [imageBlob, setImageBlob] = useState<Blob | null>(null)
  const [imageMime, setImageMime] = useState<string>('image/jpeg')
  const [showImageModal, setShowImageModal] = useState(false)
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null)

  // Audio state
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [audioMime, setAudioMime] = useState<string>('audio/webm')
  const [showAudioModal, setShowAudioModal] = useState(false)
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null)
  // NOTE: recording state commented out — MediaRecorder requires HTTPS (secure context),
  // which Trove does not currently provide over LAN. Re-enable if HTTPS support is added.
  // const [recording, setRecording] = useState(false)
  // const [recordingSeconds, setRecordingSeconds] = useState(0)

  // Audio MIME types supported by Gemma 4 (Ollama). AAC/M4A are not supported.
  const SUPPORTED_AUDIO_TYPES = new Set(['audio/wav', 'audio/mpeg', 'audio/ogg', 'audio/webm'])

  // Refs for hidden file inputs
  // NOTE: mediaRecorderRef, chunksRef, timerRef commented out — recording disabled (see above)
  const imageFileRef = useRef<HTMLInputElement>(null)
  const imageCapRef = useRef<HTMLInputElement>(null)
  const audioFileRef = useRef<HTMLInputElement>(null)
  // const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  // const chunksRef = useRef<Blob[]>([])
  // const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Load gem on mount
  useEffect(() => {
    if (!id) return
    gemsApi.get(id)
      .then(g => {
        setGem(g)
        // Pre-fill defaults
        const defaults: Record<string, string> = {}
        for (const arg of g.args) {
          defaults[arg.name] = arg.default
        }
        setValues(defaults)
      })
      .catch(() => setLoadError(true))
  }, [id])

  // Fetch capabilities to know whether to show audio controls
  useEffect(() => {
    if (!id) return
    appApi.capabilities()
      .then(caps => setCapabilities(caps))
      .catch(() => {})  // safe default: don't show audio controls if fetch fails
  }, [id])

  // Manage image preview URL — revoke on change to avoid memory leaks
  useEffect(() => {
    if (!imageBlob) { setImagePreviewUrl(null); return }
    const url = URL.createObjectURL(imageBlob)
    setImagePreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [imageBlob])

  // Manage audio preview URL
  useEffect(() => {
    if (!audioBlob) { setAudioPreviewUrl(null); return }
    const url = URL.createObjectURL(audioBlob)
    setAudioPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [audioBlob])

  // NOTE: recording cleanup useEffect commented out — recording disabled (see above)
  // useEffect(() => {
  //   return () => {
  //     if (timerRef.current) clearInterval(timerRef.current)
  //     if (mediaRecorderRef.current?.state === 'recording') {
  //       mediaRecorderRef.current.stop()
  //     }
  //   }
  // }, [])

  // Auto-scroll output area as tokens arrive
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [output])

  async function handleRun() {
    if (!gem || !id) return
    setOutput('')
    setPhase('running')
    try {
      const imgArg = imageBlob ? { blob: imageBlob, mime: imageMime } : undefined
      const audArg = audioBlob ? { blob: audioBlob, mime: audioMime } : undefined
      const res = await gemsApi.run(id, values, imgArg, audArg)
      let firstToken = true
      for await (const token of readSSEStream(res)) {
        if (firstToken) {
          firstToken = false
          setPhase('done')
        }
        setOutput(prev => prev + token)
      }
      setPhase('done')
    } catch {
      setOutput(t('gem.error.run'))
      setPhase('done')
    }
  }

  // NOTE: startRecording and stopRecording commented out — MediaRecorder requires HTTPS.
  // Re-enable when Trove serves over HTTPS on LAN.
  //
  // async function startRecording() {
  //   setShowAudioModal(false)
  //   try {
  //     const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  //     const recorder = new MediaRecorder(stream)
  //     chunksRef.current = []
  //     recorder.ondataavailable = (e) => {
  //       if (e.data.size > 0) chunksRef.current.push(e.data)
  //     }
  //     recorder.onstop = () => {
  //       const mime = recorder.mimeType || 'audio/webm'
  //       const blob = new Blob(chunksRef.current, { type: mime })
  //       setAudioBlob(blob)
  //       setAudioMime(mime)
  //       stream.getTracks().forEach(t => t.stop())
  //       if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
  //     }
  //     recorder.start()
  //     mediaRecorderRef.current = recorder
  //     setRecordingSeconds(0)
  //     setRecording(true)
  //     timerRef.current = setInterval(() => setRecordingSeconds(s => s + 1), 1000)
  //   } catch {
  //     // Microphone permission denied or unavailable — fail silently.
  //   }
  // }
  //
  // function stopRecording() {
  //   mediaRecorderRef.current?.stop()
  //   setRecording(false)
  // }

  if (loadError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">{t('gem.error.not_found')}</p>
      </div>
    )
  }

  if (!gem) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  /** Human-readable summary of current arg values and attachments for the collapsed bar. */
  const argSummary = [
    ...gem.args.filter(a => values[a.name]).map(a => `${a.name}: ${values[a.name]}`),
    ...(imageBlob ? ['image attached'] : []),
    ...(audioBlob ? ['audio attached'] : []),
  ].join(' · ')

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-2xl mx-auto flex flex-col gap-4">

        {/* Header */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            {t('gem.back')}
          </button>
          <GemIcon hue={gem.hue} size={28} />
          <h1 className="text-xl font-bold text-gray-900">{gem.name}</h1>
        </div>

        {/* Hidden file inputs for image picking */}
        {gem.has_image && (
          <>
            <input
              type="file"
              accept="image/*"
              className="hidden"
              ref={imageFileRef}
              onChange={e => {
                const f = e.target.files?.[0]
                if (f) { setImageBlob(f); setImageMime(f.type || 'image/jpeg') }
                setShowImageModal(false)
                if (imageFileRef.current) imageFileRef.current.value = ''
              }}
            />
            <input
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              ref={imageCapRef}
              onChange={e => {
                const f = e.target.files?.[0]
                if (f) { setImageBlob(f); setImageMime(f.type || 'image/jpeg') }
                setShowImageModal(false)
                if (imageCapRef.current) imageCapRef.current.value = ''
              }}
            />
          </>
        )}

        {/* Hidden file input for audio picking — restricted to Gemma-supported formats */}
        {gem.has_audio && capabilities.audio && (
          <input
            type="file"
            accept="audio/wav,audio/mpeg,audio/ogg,audio/webm"
            className="hidden"
            ref={audioFileRef}
            onChange={e => {
              const f = e.target.files?.[0]
              if (f) {
                // Reject formats Gemma can't process (e.g. AAC/M4A from iOS Voice Memos)
                if (f.type && !SUPPORTED_AUDIO_TYPES.has(f.type)) {
                  setOutput(t('gem.error.audio_format'))
                  setPhase('done')
                  setShowAudioModal(false)
                  if (audioFileRef.current) audioFileRef.current.value = ''
                  return
                }
                setAudioBlob(f)
                setAudioMime(f.type || 'audio/webm')
              }
              setShowAudioModal(false)
              if (audioFileRef.current) audioFileRef.current.value = ''
            }}
          />
        )}

        {/* Phase 1: Form — shown when phase is 'form' */}
        {phase === 'form' && (
          <div className="bg-white border border-gray-200 rounded-lg p-5 flex flex-col gap-4">
            {gem.description && (
              <p className="text-sm text-gray-500">{gem.description}</p>
            )}

            {gem.args.map(arg => (
              <div key={arg.name}>
                <div className="mb-1">
                  <Label htmlFor={`arg-${arg.name}`}>
                    {arg.name}
                    {arg.description && (
                      <span className="text-gray-400 font-normal ml-1 text-xs">— {arg.description}</span>
                    )}
                  </Label>
                </div>
                {arg.type === 'string' ? (
                  <TextInput
                    id={`arg-${arg.name}`}
                    value={values[arg.name] ?? ''}
                    onChange={e => setValues(v => ({ ...v, [arg.name]: e.target.value }))}
                    placeholder={arg.default || arg.description}
                  />
                ) : (
                  <Select
                    id={`arg-${arg.name}`}
                    value={values[arg.name] ?? arg.default}
                    onChange={e => setValues(v => ({ ...v, [arg.name]: e.target.value }))}
                  >
                    {arg.options.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </Select>
                )}
              </div>
            ))}

            {/* Image picker */}
            {gem.has_image && (
              <div className="flex flex-col gap-2">
                {imagePreviewUrl ? (
                  <div className="flex items-center gap-3">
                    <img
                      src={imagePreviewUrl}
                      alt="Selected image"
                      className="h-16 w-16 object-cover rounded border border-gray-200"
                    />
                    <Button color="light" size="xs" onClick={() => setImageBlob(null)}>
                      {t('gem.remove')}
                    </Button>
                  </div>
                ) : (
                  <Button color="light" onClick={() => setShowImageModal(true)}>
                    {t('gem.add_image')}
                  </Button>
                )}
              </div>
            )}

            {/* Audio picker — file upload only */}
            {/* NOTE: inline recorder branch commented out — recording disabled (requires HTTPS) */}
            {gem.has_audio && capabilities.audio && (
              <div className="flex flex-col gap-2">
                {audioPreviewUrl ? (
                  // Preview + remove — shown after file pick
                  <div className="flex items-center gap-2">
                    <audio controls src={audioPreviewUrl} className="h-9 flex-1 min-w-0" />
                    <Button
                      color="light"
                      size="xs"
                      className="shrink-0"
                      onClick={() => setAudioBlob(null)}
                    >
                      {t('gem.remove')}
                    </Button>
                  </div>
                ) : (
                  <Button color="light" onClick={() => setShowAudioModal(true)}>
                    {t('gem.add_audio')}
                  </Button>
                )}
                {/* NOTE: recording branch commented out:
                {recording ? (
                  <div className="flex items-center gap-3 py-1">
                    <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shrink-0" />
                    <span className="text-sm text-gray-600 tabular-nums">{recordingSeconds}s</span>
                    <Button color="failure" size="sm" onClick={stopRecording}>{t('gem.stop_recording')}</Button>
                  </div>
                ) : ...} */}
              </div>
            )}

            <Button color="blue" onClick={handleRun}>
              {t('gem.run')}
            </Button>
          </div>
        )}

        {/* Phase 2: Collapsed summary bar — shown when running or done */}
        {(phase === 'running' || phase === 'done') && (
          <button
            onClick={() => { setPhase('form'); setOutput('') }}
            className="w-full text-left bg-white border border-gray-200 rounded-lg px-4 py-3 flex justify-between items-center hover:bg-gray-50 transition-colors"
          >
            <span className="text-sm text-gray-600 truncate">{argSummary || gem.name}</span>
            <span className="text-xs text-indigo-500 ml-3 shrink-0">{t('gem.edit_inputs')}</span>
          </button>
        )}

        {/* Spinner — shown while running before first token */}
        {phase === 'running' && (
          <div className="flex justify-center py-6">
            <Spinner size="lg" />
          </div>
        )}

        {/* Output area — shown once first token arrives */}
        {phase === 'done' && (
          <div className="flex flex-col gap-3">
            <div
              ref={outputRef}
              className="bg-white border border-gray-200 rounded-lg p-4 min-h-32 max-h-[60vh] overflow-y-auto text-sm text-gray-800 leading-relaxed prose prose-sm max-w-none"
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {output}
              </ReactMarkdown>
              <span
                className="inline-block w-0.5 h-3.5 bg-indigo-500 ml-0.5 align-middle animate-pulse"
                aria-hidden="true"
              />
            </div>
            <Button color="light" onClick={handleRun}>
              {t('gem.run_again')}
            </Button>
          </div>
        )}

      </div>

      {/* Image source picker modal */}
      <Modal show={showImageModal} onClose={() => setShowImageModal(false)} size="sm">
        <ModalHeader>{t('gem.image_source.title')}</ModalHeader>
        <ModalBody>
          <div className="flex flex-col gap-3">
            <Button
              color="light"
              className="w-full"
              onClick={() => imageFileRef.current?.click()}
            >
              {t('gem.image_source.file')}
            </Button>
            <Button
              color="light"
              className="w-full"
              onClick={() => imageCapRef.current?.click()}
            >
              {t('gem.image_source.capture')}
            </Button>
          </div>
        </ModalBody>
      </Modal>

      {/* Audio source picker modal — file upload only */}
      {/* NOTE: "Record now" option commented out — recording disabled (requires HTTPS).
          Re-enable canRecord check and startRecording button when HTTPS is available:
          {canRecord ? (
            <Button color="light" className="w-full" onClick={startRecording}>
              {t('gem.audio_source.record')}
            </Button>
          ) : (
            <p className="text-xs text-gray-400 text-center py-1">
              {t('gem.audio_source.record_unavailable')}
            </p>
          )} */}
      <Modal show={showAudioModal} onClose={() => setShowAudioModal(false)} size="sm">
        <ModalHeader>{t('gem.audio_source.title')}</ModalHeader>
        <ModalBody>
          <div className="flex flex-col gap-3">
            <Button
              color="light"
              className="w-full"
              onClick={() => audioFileRef.current?.click()}
            >
              {t('gem.audio_source.file')}
            </Button>
          </div>
        </ModalBody>
      </Modal>

    </div>
  )
}
