import { useEffect, useRef, useState, useCallback } from 'react'
import { io } from 'socket.io-client'

const TOKEN_KEY = 'touchmorph_session_token'
const PING_INTERVAL = 25000

export function useSocket() {
  const ref = useRef<ReturnType<typeof io> | null>(null)
  const [connected, setConnected] = useState(false)
  const [pairStatus, setPairStatus] = useState(false)
  const [pairCode, setPairCode] = useState<string | null>(null)
  const [screenW, setScreenW] = useState(1920)
  const [screenH, setScreenH] = useState(1080)
  const pingRef = useRef<number | null>(null)

  useEffect(() => {
    const socket = io({ transports: ['websocket', 'polling'], reconnection: true })
    ref.current = socket

    socket.on('connect', () => {
      setConnected(true)
      const savedToken = localStorage.getItem(TOKEN_KEY) || ''
      socket.emit('session_restore', { token: savedToken })
    })

    socket.on('session:created', ({ token, screenWidth, screenHeight }) => {
      localStorage.setItem(TOKEN_KEY, token)
      if (screenWidth) setScreenW(screenWidth)
      if (screenHeight) setScreenH(screenHeight)
    })

    socket.on('session:restored', ({ token, paired, screenWidth, screenHeight }) => {
      localStorage.setItem(TOKEN_KEY, token)
      setPairStatus(paired)
      if (screenWidth) setScreenW(screenWidth)
      if (screenHeight) setScreenH(screenHeight)
    })

    socket.on('screen:dimensions', ({ width, height }) => {
      if (width) setScreenW(width)
      if (height) setScreenH(height)
    })

    socket.on('mode:switched', ({ screenWidth, screenHeight }) => {
      if (screenWidth) setScreenW(screenWidth)
      if (screenHeight) setScreenH(screenHeight)
    })

    socket.on('disconnect', () => setConnected(false))
    socket.on('pair:code', ({ code }) => setPairCode(code))
    socket.on('pair:success', () => { setPairStatus(true); setPairCode(null) })
    socket.on('pair:error', () => setPairCode(null))

    pingRef.current = window.setInterval(() => {
      if (socket.connected) socket.volatile.emit('ping')
    }, PING_INTERVAL)

    return () => {
      if (pingRef.current) clearInterval(pingRef.current)
      socket.disconnect()
    }
  }, [])

  const requestPairing = useCallback(() => ref.current?.emit('pair_request'), [])
  const verifyPairing = useCallback((code: string) => ref.current?.emit('pair_verify', { code }), [])
  const emit = useCallback((event: string, data?: any) => { ref.current?.emit(event, data) }, [])

  return { connected, pairStatus, pairCode, screenW, screenH, requestPairing, verifyPairing, emit }
}
