import { useCallback } from 'react'

interface Props {
  emit: (e: string, d?: any) => void
}

export default function MediaController({ emit }: Props) {
  const action = useCallback((a: string) => {
    emit('media:action', { action: a })
    window.navigator.vibrate?.(10)
  }, [emit])

  return (
    <div className="flex-1 flex flex-col p-6 gap-6 bg-slate-950">
      {/* Playback controls */}
      <div className="flex items-center justify-center gap-6">
        <button onClick={() => action('prev')}
          className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center text-2xl active:bg-slate-700 active:scale-90 transition-transform">
          ⏮
        </button>
        <button onClick={() => action('play_pause')}
          className="w-20 h-20 rounded-full bg-morph-600 flex items-center justify-center text-3xl active:bg-morph-700 active:scale-90 transition-transform shadow-lg shadow-morph-600/30">
          ▶
        </button>
        <button onClick={() => action('next')}
          className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center text-2xl active:bg-slate-700 active:scale-90 transition-transform">
          ⏭
        </button>
      </div>

      {/* Volume controls */}
      <div className="bg-slate-900 rounded-2xl p-4 border border-slate-800">
        <p className="text-slate-500 text-xs mb-3 text-center font-medium uppercase tracking-wider">Volume</p>
        <div className="flex items-center justify-center gap-4">
          <button onClick={() => action('mute')}
            className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center text-xl active:bg-slate-700 active:scale-90 transition-transform">
            🔇
          </button>
          <button onClick={() => action('vol_down')}
            className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center text-xl active:bg-slate-700 active:scale-90 transition-transform">
            ➖
          </button>
          <button onClick={() => action('vol_up')}
            className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center text-xl active:bg-slate-700 active:scale-90 transition-transform">
            ➕
          </button>
        </div>
      </div>

      {/* Now playing placeholder */}
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4 opacity-30">🎵</div>
          <p className="text-slate-600 text-sm">Media controls</p>
          <p className="text-slate-700 text-xs mt-1">Controls your system media player</p>
        </div>
      </div>
    </div>
  )
}
