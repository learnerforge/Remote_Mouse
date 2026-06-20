import clsx from 'clsx';

type Mode = 'mouse' | 'touchpad';

export default function Navbar({ mode, onSwitch }: { mode: Mode; onSwitch: (m: Mode) => void }) {
  return (
    <header className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
      <span className="font-bold text-white">TouchMorph</span>
      <div className="flex bg-slate-800 rounded-xl p-1">
        {(['mouse', 'touchpad'] as Mode[]).map(m => (
          <button key={m} onClick={() => onSwitch(m)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors',
              mode === m ? 'bg-morph-600 text-white' : 'text-slate-400'
            )}>
            {m}
          </button>
        ))}
      </div>
      <div className={clsx('w-2 h-2 rounded-full', 'bg-green-500')} />
    </header>
  );
}
