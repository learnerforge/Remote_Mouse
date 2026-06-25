import { useRef, useCallback, useState, useEffect } from 'react'

interface Props {
  emit: (e: string, d?: any) => void
  screenW: number
  screenH: number
}

type AirMode = 'relative' | 'absolute'

export default function AirMouseMode({ emit, screenW, screenH }: Props) {
  const [active, setActive] = useState(false)
  const [denied, setDenied] = useState(false)
  const [airMode, setAirMode] = useState<AirMode>('relative')
  const [calibrated, setCalibrated] = useState(false)
  const [showGuide, setShowGuide] = useState(true)

  const lastData = useRef({ beta: 0, gamma: 0 })
  const baseline = useRef({ beta: 0, gamma: 0 })
  const calibratedRef = useRef(false)
  const smoothX = useRef(0)
  const smoothY = useRef(0)
  const sens = useRef(1.5)
  const deadZone = useRef(2)

  const calibrate = useCallback(() => {
    baseline.current = { beta: lastData.current.beta, gamma: lastData.current.gamma }
    calibratedRef.current = true
    setCalibrated(true)
    setShowGuide(false)
    smoothX.current = 0
    smoothY.current = 0
    navigator.vibrate?.(20)
  }, [])

  useEffect(() => {
    if (typeof DeviceOrientationEvent === 'undefined') {
      setDenied(true)
      return
    }

    let mounted = true
    let calTimer: number | null = null

    const handleOrientation = (e: DeviceOrientationEvent) => {
      if (!mounted) return
      const beta = e.beta ?? 0
      const gamma = e.gamma ?? 0
      lastData.current = { beta, gamma }

      if (!calibratedRef.current) return

      const dBeta = beta - baseline.current.beta
      const dGamma = gamma - baseline.current.gamma

      if (Math.abs(dGamma) < deadZone.current) {
        smoothX.current *= 0.85
      } else {
        smoothX.current = smoothX.current * 0.6 + dGamma * sens.current * 0.4
      }

      if (Math.abs(dBeta) < deadZone.current) {
        smoothY.current *= 0.85
      } else {
        smoothY.current = smoothY.current * 0.6 + (-dBeta) * sens.current * 0.4
      }

      if (airMode === 'absolute') {
        const absX = Math.max(0, Math.min(1, (gamma + 45) / 90))
        const absY = Math.max(0, Math.min(1, (beta + 45) / 90))
        emit('airmouse_move', { mode: 'absolute', x: absX, y: absY })
      } else if (Math.abs(smoothX.current) > 1 || Math.abs(smoothY.current) > 1) {
        emit('airmouse_move', {
          mode: 'relative',
          deltaX: smoothX.current,
          deltaY: smoothY.current,
          sensitivity: sens.current,
        })
      }
    }

    window.addEventListener('deviceorientation', handleOrientation)
    setActive(true)

    calTimer = window.setTimeout(calibrate, 500) as unknown as number

    return () => {
      mounted = false
      if (calTimer !== null) clearTimeout(calTimer)
      window.removeEventListener('deviceorientation', handleOrientation)
    }
  }, [emit, airMode, calibrate])

  const handleClick = useCallback((button: string) => {
    emit('airmouse_click', { button })
    navigator.vibrate(10)
  }, [emit])

  if (denied) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center gap-4 bg-slate-950">
        <span className="text-6xl">📵</span>
        <p className="text-slate-400 text-sm">Device orientation not supported</p>
        <p className="text-slate-600 text-xs">Your browser doesn't support motion sensors. Use Touchpad mode instead.</p>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col bg-slate-950">
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <div className="w-28 h-28 rounded-full bg-slate-800 flex items-center justify-center border-2 transition-colors"
          style={{ borderColor: calibrated ? '#6366f1' : '#334155' }}>
          <span className="text-5xl">{calibrated ? '🎯' : '⏳'}</span>
        </div>

        {showGuide && (
          <div className="text-center px-6">
            <p className="text-slate-400 text-sm mb-1">Hold phone flat, then tap <b className="text-morph-400">Calibrate</b></p>
            <p className="text-slate-600 text-xs">Tilt to move · Screen: {screenW}×{screenH}</p>
          </div>
        )}

        <div className="flex gap-2">
          <button onClick={calibrate}
            className="px-4 py-2 text-xs bg-slate-800 rounded-xl text-slate-300 active:bg-slate-700">
            Recalibrate
          </button>
          <button onClick={() => setAirMode(airMode === 'relative' ? 'absolute' : 'relative')}
            className="px-4 py-2 text-xs rounded-xl font-medium active:scale-95 transition-transform"
            style={{
              background: airMode === 'absolute' ? '#6366f1' : '#334155',
              color: airMode === 'absolute' ? '#fff' : '#94a3b8',
            }}>
            {airMode === 'absolute' ? 'Absolute' : 'Relative'}
          </button>
        </div>

        <div className="flex items-center gap-1 text-[10px] text-slate-600">
          <span className={`w-1.5 h-1.5 rounded-full ${calibrated ? 'bg-green-500' : 'bg-yellow-500'}`} />
          {calibrated ? 'Calibrated' : 'Not calibrated'}
        </div>
      </div>

      <div className="flex gap-3 px-3 pb-3">
        <button onPointerDown={() => handleClick('left')}
          className="flex-1 py-4 bg-slate-800 rounded-xl text-white font-medium active:bg-slate-700 active:scale-95 transition-transform">
          Left Click
        </button>
        <button onPointerDown={() => handleClick('right')}
          className="flex-1 py-4 bg-slate-800 rounded-xl text-white font-medium active:bg-slate-700 active:scale-95 transition-transform">
          Right Click
        </button>
      </div>
    </div>
  )
}
