import { useState } from 'react'
import clsx from 'clsx'
import BottomNav from './components/BottomNav'
import MouseMode from './pages/MouseMode'
import TouchpadMode from './pages/TouchpadMode'
import AirMouseMode from './pages/AirMouseMode'
import PresentationMode from './pages/PresentationMode'
import MediaController from './pages/MediaController'
import Settings from './pages/Settings'
import { useSocket } from './hooks/useSocket'
import type { Mode } from './components/BottomNav'

export default function App() {
  const [mode, setMode] = useState<Mode>('mouse')
  const { connected, pairStatus, pairCode, screenW, screenH, requestPairing, verifyPairing, emit } = useSocket()

  if (!connected) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950 text-slate-400 text-lg">
        Connecting...
      </div>
    )
  }

  if (!pairStatus) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-6 bg-slate-950 p-8">
        <h2 className="text-xl text-slate-300 font-semibold">Pair Your Device</h2>
        <button onClick={requestPairing}
          className="px-8 py-3 bg-morph-600 rounded-xl text-white font-medium active:bg-morph-700">
          Generate Code
        </button>
        {pairCode && (
          <>
            <div className="text-4xl tracking-[0.3em] font-bold text-morph-300 bg-slate-900 px-8 py-4 rounded-2xl">
              {pairCode}
            </div>
            <input type="text" maxLength={6} placeholder="Enter code from laptop"
              className="px-4 py-3 bg-slate-800 rounded-xl text-center text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-morph-500"
              onKeyDown={e => { if (e.key === 'Enter') verifyPairing((e.target as HTMLInputElement).value) }}
            />
          </>
        )}
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-slate-950">
      <header className="flex items-center justify-between px-4 py-2.5 bg-slate-900 border-b border-slate-800">
        <span className="font-bold text-white text-sm">TouchMorph</span>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">{mode}</span>
          <div className={clsx('w-2 h-2 rounded-full', connected ? 'bg-green-500' : 'bg-red-500')} />
        </div>
      </header>

      <div className="flex-1 flex flex-col min-h-0">
        {mode === 'mouse' && <MouseMode emit={emit} />}
        {mode === 'touchpad' && <TouchpadMode emit={emit} />}
        {mode === 'airmouse' && <AirMouseMode emit={emit} screenW={screenW} screenH={screenH} />}
        {mode === 'presentation' && <PresentationMode emit={emit} />}
        {mode === 'media' && <MediaController emit={emit} />}
        {mode === 'settings' && <Settings emit={emit} />}
      </div>

      <BottomNav mode={mode} onSwitch={setMode} />
    </div>
  )
}
