import { useRef, useCallback, useState, useEffect } from 'react'

interface Props {
  emit: (e: string, d?: any) => void
}

const SWIPE_THRESHOLD = 30

function swipeDir(dx: number, dy: number): string {
  const dist = Math.sqrt(dx * dx + dy * dy)
  if (dist < SWIPE_THRESHOLD) return ''
  const angle = Math.atan2(dy, dx)
  if (Math.abs(angle) < Math.PI / 4) return 'right'
  if (Math.abs(angle) > 3 * Math.PI / 4) return 'left'
  if (angle > 0) return 'down'
  return 'up'
}

export default function TouchpadMode({ emit }: Props) {
  const [fingers, setFingers] = useState(0)
  const last = useRef({ x: 0, y: 0 })
  const scrollActive = useRef(false)
  const tapCount = useRef(0)
  const tapTimer = useRef<number | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [invertScroll, setInvertScroll] = useState(true)
  const [sensitivity, setSensitivity] = useState(1.0)
  const [momentum, setMomentum] = useState(true)
  const touchOrigins = useRef<Map<number, { x: number; y: number }>>(new Map())

  useEffect(() => {
    emit('smart_scroll_config', { invert: invertScroll, sensitivity, decay: momentum ? 0.92 : 1.0 })
  }, [invertScroll, sensitivity, momentum, emit])

  const clearTapTimer = () => {
    if (tapTimer.current !== null) {
      clearTimeout(tapTimer.current)
      tapTimer.current = null
    }
  }

  const handleDoubleTap = useCallback(() => {
    tapCount.current++
    if (tapCount.current === 1) {
      tapTimer.current = window.setTimeout(() => {
        tapCount.current = 0
      }, 400) as unknown as number
    } else if (tapCount.current >= 2) {
      clearTapTimer()
      tapCount.current = 0
      emit('touchpad_event', { type: 'double_tap' })
    }
  }, [emit])

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    last.current = { x: e.clientX, y: e.clientY }
  }, [])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (e.buttons !== 1) return
    const dx = e.clientX - last.current.x
    const dy = e.clientY - last.current.y
    last.current = { x: e.clientX, y: e.clientY }
    if (fingers >= 2) {
      if (!scrollActive.current) {
        scrollActive.current = true
        emit('smart_scroll_start')
      }
      emit('smart_scroll_move', { deltaX: dx, deltaY: dy })
    } else {
      emit('touchpad_event', { type: 'move', deltaX: dx, deltaY: dy })
    }
  }, [emit, fingers])

  const handlePointerUp = useCallback(() => {
    if (scrollActive.current) {
      if (momentum)       emit('smart_scroll_end')
      scrollActive.current = false
    }
  }, [emit, momentum])

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    const count = e.touches.length
    setFingers(count)
    touchOrigins.current.clear()
    for (let i = 0; i < count; i++) {
      const t = e.touches[i]
      touchOrigins.current.set(t.identifier, { x: t.clientX, y: t.clientY })
    }
    if (count >= 2) {
      const t = e.touches
      last.current = {
        x: (t[0].clientX + t[1].clientX) / 2,
        y: (t[0].clientY + t[1].clientY) / 2,
      }
    }
  }, [])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    const count = e.touches.length
    setFingers(count)
    if (count >= 2) {
      e.preventDefault()
      const t = e.touches
      const cx = (t[0].clientX + t[1].clientX) / 2
      const cy = (t[0].clientY + t[1].clientY) / 2
      const dx = cx - last.current.x
      const dy = cy - last.current.y
      last.current = { x: cx, y: cy }
      if (!scrollActive.current) {
        scrollActive.current = true
        emit('smart_scroll_start')
      }
      emit('smart_scroll_move', { deltaX: dx, deltaY: dy })
    }
  }, [emit])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    const prevCount = fingers
    setFingers(0)
    scrollActive.current = false

    // Detect multi-finger swipe directions from remaining changed touches
    if (prevCount >= 2) {
      const dirs: string[] = []
      for (let i = 0; i < e.changedTouches.length; i++) {
        const t = e.changedTouches[i]
        const origin = touchOrigins.current.get(t.identifier)
        if (origin) {
          const d = swipeDir(t.clientX - origin.x, t.clientY - origin.y)
          if (d) dirs.push(d)
        }
      }
      touchOrigins.current.clear()
      if (dirs.length === prevCount && dirs.every(d => d === dirs[0])) {
        const direction = dirs[0]
        emit('gesture_n_finger_swipe', { fingerCount: prevCount, direction })
        return
      }
    } else {
      touchOrigins.current.clear()
    }

    if (prevCount === 2) {
        emit('touchpad_event', { type: 'two_finger_tap' })
      window.navigator.vibrate?.(10)
    } else if (prevCount === 3) {
      emit('touchpad_event', { type: 'three_finger_tap' })
      window.navigator.vibrate?.(10)
    }
  }, [emit, fingers])

  const handleClick = useCallback(() => {
    handleDoubleTap()
  }, [handleDoubleTap])

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    emit('touchpad_event', { type: 'two_finger_tap' })
  }, [emit])

  return (
    <div className="flex-1 flex flex-col p-3">
      <div
        className="flex-1 rounded-2xl border-2 select-none touch-none transition-colors relative overflow-hidden"
        style={{
          borderColor: fingers >= 2 ? '#6366f1' : '#334155',
          background: fingers >= 2 ? 'rgba(99, 102, 241, 0.05)' : 'rgba(30, 41, 59, 0.5)',
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={() => { scrollActive.current = false }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
      >
        <div className="h-full flex flex-col items-center justify-center text-slate-600 text-sm gap-2">
          <span className="text-4xl">{fingers >= 2 ? '✌️' : fingers === 3 ? '🤚' : '👆'}</span>
          <span>1F move · 2F scroll · Tap click</span>
          <span className="text-xs text-slate-700">2F tap=right-click · 3F swipe=app switch</span>
        </div>

        <button
          onClick={(e) => { e.stopPropagation(); setShowSettings(!showSettings) }}
          className="absolute top-2 right-2 text-slate-500 text-lg p-1"
        >
          ⚙
        </button>

        {showSettings && (
          <div className="absolute top-10 right-2 bg-slate-800 rounded-xl p-3 shadow-xl border border-slate-700 z-10 w-48"
            onClick={e => e.stopPropagation()}>
            <label className="flex items-center justify-between text-xs text-slate-300 mb-2">
              Natural scroll
              <input type="checkbox" checked={invertScroll}
                onChange={e => setInvertScroll(e.target.checked)}
                className="accent-morph-500" />
            </label>
            <label className="flex items-center justify-between text-xs text-slate-300 mb-2">
              Momentum
              <input type="checkbox" checked={momentum}
                onChange={e => setMomentum(e.target.checked)}
                className="accent-morph-500" />
            </label>
            <label className="text-xs text-slate-300 mb-1 block">Sensitivity</label>
            <input type="range" min="0.25" max="3" step="0.25" value={sensitivity}
              onChange={e => setSensitivity(parseFloat(e.target.value))}
              className="w-full accent-morph-500" />
            <div className="text-xs text-slate-500 text-center mt-1">{sensitivity.toFixed(2)}x</div>
          </div>
        )}

        <div className="absolute bottom-2 left-0 right-0 text-center text-[10px] text-slate-700 select-none">
          3F←=alt+tab · 3F↑=taskview · 3F↓=desktop
        </div>
      </div>
    </div>
  )
}
