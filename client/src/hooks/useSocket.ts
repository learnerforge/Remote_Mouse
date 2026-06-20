import { useEffect, useRef, useState, useCallback } from 'react';
import { io } from 'socket.io-client';

const TOKEN_KEY = 'touchmorph_session_token';
const PING_INTERVAL = 25000;

export function useSocket() {
  const ref = useRef<ReturnType<typeof io> | null>(null);
  const [connected, setConnected] = useState(false);
  const [pairStatus, setPairStatus] = useState(false);
  const [pairCode, setPairCode] = useState<string | null>(null);
  const pingRef = useRef<number | null>(null);
  const wakeRef = useRef<WakeLockSentinel | null>(null);

  useEffect(() => {
    const socket = io({ transports: ['websocket', 'polling'], reconnection: true });
    ref.current = socket;

    socket.on('connect', () => {
      setConnected(true);
      const savedToken = localStorage.getItem(TOKEN_KEY) || '';
      socket.emit('session:restore', { token: savedToken });
    });

    socket.on('session:created', ({ token }) => {
      localStorage.setItem(TOKEN_KEY, token);
    });

    socket.on('session:restored', ({ token, paired }) => {
      localStorage.setItem(TOKEN_KEY, token);
      setPairStatus(paired);
    });

    socket.on('disconnect', () => setConnected(false));
    socket.on('pair:code', ({ code }) => setPairCode(code));
    socket.on('pair:success', () => { setPairStatus(true); setPairCode(null); });
    socket.on('pair:error', () => setPairCode(null));

    pingRef.current = window.setInterval(() => {
      if (socket.connected) socket.volatile.emit('ping');
    }, PING_INTERVAL);

    if ('wakeLock' in navigator) {
      navigator.wakeLock.request('screen').then(l => { wakeRef.current = l; }).catch(() => {});
      document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && !wakeRef.current) {
          navigator.wakeLock.request('screen').then(l => { wakeRef.current = l; }).catch(() => {});
        }
      });
    }

    return () => {
      if (pingRef.current) clearInterval(pingRef.current);
      if (wakeRef.current) wakeRef.current.release();
      socket.disconnect();
    };
  }, []);

  const requestPairing = useCallback(() => ref.current?.emit('pair:request'), []);
  const verifyPairing = useCallback((code: string) => ref.current?.emit('pair:verify', { code }), []);
  const emit = useCallback((event: string, data?: any) => { ref.current?.emit(event, data); }, []);

  return { connected, pairStatus, pairCode, requestPairing, verifyPairing, emit };
}
