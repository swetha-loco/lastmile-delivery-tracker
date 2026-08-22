const apiBaseUrl = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

export type HealthResponse = {
  status: string
  database: string
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`)

  if (!response.ok) {
    throw new Error('Health check failed')
  }

  return response.json() as Promise<HealthResponse>
}
