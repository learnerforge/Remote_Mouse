import clsx from 'clsx'

export type Mode = 'mouse' | 'touchpad' | 'airmouse' | 'presentation' | 'media' | 'settings'

const tabs: { key: Mode; label: string; icon: string }[] = [
  { key: 'mouse', label: 'Mouse', icon: '🖱' },
  { key: 'touchpad', label: 'Touchpad', icon: '👆' },
  { key: 'airmouse', label: 'Air', icon: '📱' },
  { key: 'presentation', label: 'Slides', icon: '📺' },
  { key: 'media', label: 'Media', icon: '🎵' },
  { key: 'settings', label: 'Settings', icon: '⚙' },
]

export default function BottomNav({ mode, onSwitch }: { mode: Mode; onSwitch: (m: Mode) => void }) {
  return (
    <nav className="flex items-center justify-around bg-slate-900 border-t border-slate-800 safe-area-pb">
      {tabs.map(t => (
        <button key={t.key} onClick={() => onSwitch(t.key)}
          className={clsx(
            'flex flex-col items-center gap-0.5 py-2 px-3 text-[10px] font-medium transition-colors min-w-0',
            mode === t.key ? 'text-morph-400' : 'text-slate-500'
          )}>
          <span className="text-lg leading-none">{t.icon}</span>
          <span className="truncate max-w-full">{t.label}</span>
        </button>
      ))}
    </nav>
  )
}
