import { useState, useEffect } from 'react'

interface Props {
  emit: (e: string, d?: any) => void
}

export default function Settings({ emit }: Props) {
  const [globalSensitivity, setGlobalSensitivity] = useState(1.0)

  useEffect(() => {
    emit('smart_scroll_config', { sensitivity: globalSensitivity })
  }, [globalSensitivity, emit])

  return (
    <div className="flex-1 flex flex-col p-4 gap-3 bg-slate-950 overflow-y-auto">
      <h2 className="text-slate-300 font-semibold text-base">Settings</h2>

      <div className="bg-slate-900 rounded-2xl p-4 border border-slate-800">
        <label className="text-xs text-slate-400 uppercase tracking-wider font-medium">Pointer Sensitivity</label>
        <input type="range" min="0.25" max="3" step="0.25" value={globalSensitivity}
          onChange={e => setGlobalSensitivity(parseFloat(e.target.value))}
          className="w-full mt-2 accent-morph-500" />
        <div className="text-xs text-slate-500 text-center mt-1">{globalSensitivity.toFixed(2)}x</div>
      </div>

      <div className="bg-slate-900 rounded-2xl p-4 border border-slate-800">
        <h3 className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">Gesture Reference</h3>
        <div className="text-xs text-slate-500 space-y-1">
          <p><b className="text-slate-400">Mouse:</b> 1F=drag, 2F=right-click, 3F=double-click</p>
          <p><b className="text-slate-400">Touchpad:</b> 1F=move, 2F=scroll, tap=click</p>
          <p><b className="text-slate-400">Air Mouse:</b> tilt to move, shake=cursor finder</p>
          <p><b className="text-slate-400">3F Swipes:</b> ←=alt+tab, →=switch, ↑=taskview, ↓=desktop</p>
        </div>
      </div>

      <div className="bg-slate-900 rounded-2xl p-4 border border-slate-800">
        <h3 className="text-xs text-slate-400 uppercase tracking-wider font-medium mb-2">About</h3>
        <p className="text-xs text-slate-500">TouchMorph v1.0</p>
        <p className="text-xs text-slate-600 mt-1">Browser-based remote mouse &amp; touchpad. No app install needed.</p>
      </div>
    </div>
  )
}
