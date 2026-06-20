import { useCallback } from 'react';

export default function MouseMode({ emit }: { emit: (e: string, d?: any) => void }) {
  const move = useCallback((e: React.PointerEvent) => {
    if (e.buttons === 1) emit('mouse:event', { type: 'move', x: e.clientX, y: e.clientY });
  }, [emit]);

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 m-3 rounded-2xl border-2 border-dashed border-slate-700 bg-slate-900/50"
        onPointerMove={move}>
        <div className="h-full flex items-center justify-center text-slate-600 text-sm select-none">
          Touch & drag to move cursor
        </div>
      </div>
      <div className="flex gap-3 px-3 pb-3">
        <button onPointerDown={() => emit('click:left')}
          className="flex-1 py-4 bg-slate-800 rounded-xl text-white font-medium active:bg-slate-700">
          Left
        </button>
        <button onPointerDown={() => emit('click:right')}
          className="flex-1 py-4 bg-slate-800 rounded-xl text-white font-medium active:bg-slate-700">
          Right
        </button>
        <button onPointerDown={() => emit('click:double')}
          className="flex-1 py-4 bg-slate-800 rounded-xl text-white font-medium active:bg-slate-700">
          Double
        </button>
      </div>
    </div>
  );
}
