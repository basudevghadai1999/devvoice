import { useState, useEffect, useRef } from 'react'
import VoiceOrb from './components/VoiceOrb'
import './App.css'

const LABELS = {
  idle:       'Say "Hi there" to activate',
  listening:  'Listening...',
  processing: 'Processing audio...',
  thinking:   'Thinking...',
  speaking:   'Speaking...',
}

export default function App() {
  const [state, setState]         = useState('idle')
  const [transcript, setTranscript] = useState('')
  const [response, setResponse]   = useState('')
  const [connected, setConnected] = useState(false)
  const wsRef    = useRef(null)
  const timerRef = useRef(null)

  const connect = () => {
    const ws = new WebSocket(`ws://${window.location.hostname}:8000/ws`)

    ws.onopen = () => {
      setConnected(true)
      clearTimeout(timerRef.current)
    }

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setState(data.state)
      if (data.transcript !== undefined) setTranscript(data.transcript)
      if (data.response  !== undefined) setResponse(data.response)
    }

    ws.onclose = () => {
      setConnected(false)
      timerRef.current = setTimeout(connect, 2000)
    }

    ws.onerror = () => ws.close()
    wsRef.current = ws
  }

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [])

  return (
    <div className="app">
      {/* Background grid */}
      <div className="grid" />

      {/* Top bar */}
      <header className="topbar">
        <span className="logo">D·E·V</span>
        <span className={`conn ${connected ? 'on' : 'off'}`}>
          {connected ? '● ONLINE' : '○ CONNECTING'}
        </span>
      </header>

      {/* Orb */}
      <main className="stage">
        <VoiceOrb state={state} />
        <p className="state-label">{LABELS[state] || 'Ready'}</p>
      </main>

      {/* Conversation log */}
      <footer className="log">
        {transcript && (
          <div className="log-row you">
            <span className="who">YOU</span>
            <span className="text">{transcript}</span>
          </div>
        )}
        {response && (
          <div className="log-row dev">
            <span className="who">DEV</span>
            <span className="text">{response}</span>
          </div>
        )}
      </footer>

      {/* Corner decorations */}
      <div className="corner tl" />
      <div className="corner tr" />
      <div className="corner bl" />
      <div className="corner br" />
    </div>
  )
}
