import { useRef, useCallback, useState } from 'react'

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

export default function MouseMode({ emit }: Props) {
  const [fingers, setFingers] = useState(0)
  const pointerLast = useRef({ x: 0, y: 0 })
  const gestureTimeout = useRef<number | null>(null)
  const longPressFired = useRef(false)
  const touchOrigins = useRef<Map<number, { x: number; y: number }>>(new Map())

  const clearGestureTimeout = () => {
    if (gestureTimeout.current !== null) {
      clearTimeout(gestureTimeout.current)
      gestureTimeout.current = null
    }
  }

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    pointerLast.current = { x: e.clientX, y: e.clientY }
    longPressFired.current = false
    clearGestureTimeout()
    gestureTimeout.current = window.setTimeout(() => {
      longPressFired.current = true
      emit('mouse_hold')
      window.navigator.vibrate?.(20)
    }, 600) as unknown as number
  }, [emit])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (e.buttons !== 1) return
    if (longPressFired.current) {
      emit('mouse_drag', { x: e.clientX, y: e.clientY })
    } else {
      emit('mouse_event', { type: 'move', x: e.clientX, y: e.clientY })
    }
    pointerLast.current = { x: e.clientX, y: e.clientY }
  }, [emit])

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    clearGestureTimeout()
    if (longPressFired.current) {
      emit('mouse:release')
      return
    }
    const dx = e.clientX - pointerLast.current.x
    const dy = e.clientY - pointerLast.current.y
    if (Math.sqrt(dx * dx + dy * dy) < 15) {
      emit('click_left')
    }
  }, [emit])

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    setFingers(e.touches.length)
    touchOrigins.current.clear()
    for (let i = 0; i < e.touches.length; i++) {
      const t = e.touches[i]
      touchOrigins.current.set(t.identifier, { x: t.clientX, y: t.clientY })
    }
  }, [])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    const prevFingers = fingers
    setFingers(0)

    if (prevFingers >= 2) {
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
      if (dirs.length === prevFingers && dirs.every(d => d === dirs[0])) {
        emit('gesture_n_finger_swipe', { fingerCount: prevFingers, direction: dirs[0] })
        return
      }
    } else {
      touchOrigins.current.clear()
    }

    if (prevFingers === 2) {
      emit('click_right')
      window.navigator.vibrate?.(10)
    } else if (prevFingers === 3) {
      emit('click_double')
      window.navigator.vibrate?.(10)
    }
  }, [emit, fingers])

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    setFingers(e.touches.length)
  }, [])

  return (
    <div className="flex-1 flex flex-col">
      <div
        className="flex-1 m-3 rounded-2xl border-2 border-dashed border-slate-700 bg-slate-900/50 select-none touch-none relative"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={() => {
          clearGestureTimeout()
          if (longPressFired.current) {
      emit('mouse_release')
          }
        }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        <div className="h-full flex flex-col items-center justify-center text-slate-600 text-sm gap-2">
          <span className="text-4xl">{fingers >= 2 ? '✌️' : fingers === 3 ? '🤚' : '👆'}</span>
          <span>Touch & drag · Long press = drag</span>
          <span className="text-xs text-slate-700">2F=right-click · 3F=double-click</span>
        </div>
        <div className="absolute bottom-2 left-0 right-0 text-center text-[10px] text-slate-700 select-none">
          2F swipe=scroll · 3F←=alt+tab · 3F↑=taskview · 3F↓=desktop
        </div>
      </div>

      <div className="flex gap-3 px-3 pb-3">
        <button onPointerDown={() => emit('click:left')}
          className="flex-1 py-4 bg-slate-800 rounded-xl text-white font-medium active:bg-slate-700 active:scale-95 transition-transform">
          Left
        </button>
        <button onPointerDown={() => emit('click:right')}
          className="flex-1 py-4 bg-slate-800 rounded-xl text-white font-medium active:bg-slate-700 active:scale-95 transition-transform">
          Right
        </button>
        <button onPointerDown={() => emit('click:double')}
          className="flex-1 py-4 bg-slate-800 rounded-xl text-white font-medium active:bg-slate-700 active:scale-95 transition-transform">
          Double
        </button>
      </div>
    </div>
  )
}
