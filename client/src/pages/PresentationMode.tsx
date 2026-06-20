import { useCallback, useState } from 'react'

interface Props {
  emit: (e: string, d?: any) => void
}

export default function PresentationMode({ emit }: Props) {
  const [pointerActive, setPointerActive] = useState(false)

  const action = useCallback((a: string) => {
    emit('presentation:action', { action: a })
    window.navigator.vibrate?.(10)
  }, [emit])

  return (
    <div className="flex-1 flex flex-col p-4 gap-4 bg-slate-950">
      <div className="flex-1 grid grid-cols-3 gap-3 content-center max-h-[300px]">
        <div />
        <button onClick={() => action('prev')}
          className="py-6 bg-slate-800 rounded-2xl text-2xl active:bg-slate-700 active:scale-95 transition-transform">
          ⬆
        </button>
        <div />

        <button onClick={() => action('prev')}
          className="py-6 bg-slate-800 rounded-2xl text-2xl active:bg-slate-700 active:scale-95 transition-transform">
          ⬅
        </button>
        <button onClick={() => action('pointer')}
          className={`py-6 rounded-2xl text-2xl active:scale-95 transition-all ${pointerActive ? 'bg-red-600 text-white shadow-lg shadow-red-600/30' : 'bg-slate-800'}`}
          onPointerDown={() => { setPointerActive(true); action('pointer') }}
          onPointerUp={() => { setPointerActive(false); action('pointer_stop') }}
          onPointerLeave={() => { if (pointerActive) { setPointerActive(false); action('pointer_stop') } }}>
          🔴
        </button>
        <button onClick={() => action('next')}
          className="py-6 bg-slate-800 rounded-2xl text-2xl active:bg-slate-700 active:scale-95 transition-transform">
          ➡
        </button>

        <div />
        <button onClick={() => action('next')}
          className="py-6 bg-slate-800 rounded-2xl text-2xl active:bg-slate-700 active:scale-95 transition-transform">
          ⬇
        </button>
        <div />
      </div>

      <div className="grid grid-cols-4 gap-2">
        <button onClick={() => action('start')}
          className="py-3 bg-slate-800 rounded-xl text-white text-xs font-medium active:bg-slate-700">
          ▶ Start
        </button>
        <button onClick={() => action('escape')}
          className="py-3 bg-slate-800 rounded-xl text-white text-xs font-medium active:bg-slate-700">
          ⏹ Exit
        </button>
        <button onClick={() => action('black')}
          className="py-3 bg-slate-800 rounded-xl text-white text-xs font-medium active:bg-slate-700">
          ⬛ Black
        </button>
        <button onClick={() => action('white')}
          className="py-3 bg-slate-800 rounded-xl text-white text-xs font-medium active:bg-slate-700">
          ⬜ White
        </button>
      </div>

      <div className="flex gap-2">
        <button onClick={() => action('first')}
          className="flex-1 py-3 bg-slate-800 rounded-xl text-white text-xs font-medium active:bg-slate-700">
          ⏮ First
        </button>
      </div>

      <div className="text-center text-slate-600 text-xs mt-auto pb-2">
        Swipe left/right with 2 fingers for next/prev
      </div>
    </div>
  )
}
