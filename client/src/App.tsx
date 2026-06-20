import { useState } from 'react';
import Navbar from './components/Navbar';
import MouseMode from './pages/MouseMode';
import TouchpadMode from './pages/TouchpadMode';
import { useSocket } from './hooks/useSocket';

type Mode = 'mouse' | 'touchpad';

export default function App() {
  const [mode, setMode] = useState<Mode>('mouse');
  const { connected, pairStatus, pairCode, requestPairing, verifyPairing, emit } = useSocket();

  if (!connected) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-950 text-slate-400 text-lg">
        Connecting...
      </div>
    );
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
              onKeyDown={e => { if (e.key === 'Enter') verifyPairing((e.target as HTMLInputElement).value); }}
            />
          </>
        )}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-950">
      <Navbar mode={mode} onSwitch={setMode} />
      {mode === 'mouse' ? <MouseMode emit={emit} /> : <TouchpadMode emit={emit} />}
    </div>
  );
}
