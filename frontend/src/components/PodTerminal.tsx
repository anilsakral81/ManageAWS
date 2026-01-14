import { useEffect, useRef, useState } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import { Box, CircularProgress, Alert } from '@mui/material'

interface PodTerminalProps {
  namespace: string
  podName: string
  container?: string
}

export default function PodTerminal({ namespace, podName, container }: PodTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string>('')
  const [connecting, setConnecting] = useState(true)

  useEffect(() => {
    if (!terminalRef.current) return

    // Create terminal instance
    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#ffffff',
        selectionBackground: '#264f78',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5',
      },
    })

    // Add addons
    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()
    
    term.loadAddon(fitAddon)
    term.loadAddon(webLinksAddon)

    // Open terminal
    term.open(terminalRef.current)
    fitAddon.fit()

    // Handle window resize
    const handleResize = () => {
      fitAddon.fit()
    }
    window.addEventListener('resize', handleResize)

    // Connect WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/tm/api/v1/terminal/ws/${namespace}/pods/${podName}/shell${
      container ? `?container=${container}` : ''
    }`

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setConnecting(false)
    }

    ws.onmessage = (event) => {
      term.write(event.data)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      setError('Failed to connect to pod')
      setConnecting(false)
    }

    ws.onclose = (event) => {
      // Only show error if connection failed (not a normal close)
      if (event.code !== 1000 && connecting) {
        setError('Failed to connect to pod')
        term.writeln('\r\n\x1b[1;31m✗ Failed to connect to pod\x1b[0m\r\n')
      } else if (!connecting) {
        term.writeln('\r\n\r\n\x1b[1;31m✗ Connection closed\x1b[0m\r\n')
      }
      setConnecting(false)
    }

    // Send terminal input to WebSocket
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    })

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      ws.close()
      term.dispose()
    }
  }, [namespace, podName, container])

  return (
    <Box sx={{ position: 'relative', width: '100%', height: '500px' }}>
      {connecting && (
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'rgba(0, 0, 0, 0.7)',
            zIndex: 10,
          }}
        >
          <CircularProgress />
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Box
        ref={terminalRef}
        sx={{
          width: '100%',
          height: '100%',
          '& .xterm': {
            height: '100%',
          },
        }}
      />
    </Box>
  )
}
