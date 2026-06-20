import { useRef, useCallback, useState } from 'react';
import clsx from 'clsx';

export default function TouchpadMode({ emit }: { emit: (e: string, d?: any) => void }) {
  const [fingers, setFingers] = useState(0);
  const last = useRef({ x: 0, y: 0 });

  const down = useCallback((e: React.PointerEvent) => {
    last.current = { x: e.clientX, y: e.clientY };
  }, []);

  const move = useCallback((e: React.PointerEvent) => {
    if (e.buttons !== 1) return;
    const dx = e.clientX - last.current.x;
    const dy = e.clientY - last.current.y;
    last.current = { x: e.clientX, y: e.clientY };
    emit('touchpad:event', { type: 'move', deltaX: dx, deltaY: dy, fingerCount: fingers || 1 });
  }, [emit, fingers]);

  const touchMove = useCallback((e: React.TouchEvent) => {
    setFingers(e.touches.length);
    if (e.touches.length === 2) {
      e.preventDefault();
      const t = e.touches;
      const dy = ((t[0].clientY - last.current.y) + (t[1].clientY - last.current.y)) / 2;
      const dx = ((t[0].clientX - last.current.x) + (t[1].clientX - last.current.x)) / 2;
      last.current = { x: (t[0].clientX + t[1].clientX) / 2, y: (t[0].clientY + t[1].clientY) / 2 };
      emit('touchpad:event', { type: 'two_finger_scroll', deltaX: dx, deltaY: dy, fingerCount: 2 });
    }
  }, [emit]);

  return (
    <div className="flex-1 flex flex-col p-3">
      <div className={clsx(
        'flex-1 rounded-2xl border-2 select-none transition-colors',
        fingers >= 2 ? 'border-morph-500 bg-morph-950/30' : 'border-slate-700 bg-slate-900/50'
      )}
        onPointerDown={down} onPointerMove={move} onPointerUp={() => setFingers(0)}
        onTouchStart={e => setFingers(e.touches.length)}
        onTouchMove={touchMove}
        onClick={() => emit('touchpad:event', { type: 'tap' })}
      >
        <div className="h-full flex flex-col items-center justify-center text-slate-600 text-sm">
          <span className="text-4xl mb-2">{fingers >= 2 ? '✌️' : '👆'}</span>
          <span>1F move · 2F scroll · Tap click</span>
        </div>
      </div>
    </div>
  );
}
