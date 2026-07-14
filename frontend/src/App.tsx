import { useEffect, useState } from 'react'

interface HealthResponse {
  status: string
  version: string
  environment: string
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) throw new Error(`Backend returned ${res.status}`)
        return res.json() as Promise<HealthResponse>
      })
      .then(setHealth)
      .catch((err: Error) => setError(err.message))
  }, [])

  return (
    <main className="landing">
      <h1>DocuMind</h1>
      <p>Chat with your own documents.</p>
      <p className="status">
        {health && (
          <span className="ok">
            Backend connected — v{health.version} ({health.environment})
          </span>
        )}
        {error && <span className="err">Backend unreachable: {error}</span>}
        {!health && !error && <span>Checking backend…</span>}
      </p>
    </main>
  )
}
