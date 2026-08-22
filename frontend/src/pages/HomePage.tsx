import { useEffect, useState } from 'react'

import { getHealth } from '../api/client'

type ApiStatus = 'checking' | 'connected' | 'unavailable'

function HomePage() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>('checking')

  useEffect(() => {
    let isCurrent = true

    getHealth()
      .then((health) => {
        if (!isCurrent) return
        setApiStatus(
          health.status === 'ok' && health.database === 'ok'
            ? 'connected'
            : 'unavailable',
        )
      })
      .catch(() => {
        if (isCurrent) {
          setApiStatus('unavailable')
        }
      })

    return () => {
      isCurrent = false
    }
  }, [])

  const statusLabel =
    apiStatus === 'checking'
      ? 'Checking API...'
      : apiStatus === 'connected'
        ? 'API connected'
        : 'API unavailable'

  const statusTone =
    apiStatus === 'connected'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
      : apiStatus === 'unavailable'
        ? 'border-rose-200 bg-rose-50 text-rose-800'
        : 'border-slate-200 bg-white text-slate-700'

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-10 text-slate-950">
      <section className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl items-center">
        <div className="w-full">
          <div className="mb-8 border-b border-slate-200 pb-5">
            <p className="text-sm font-medium text-slate-500">Backend foundation</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-normal text-slate-950 sm:text-5xl">
              Last-Mile Delivery Tracker
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
              A delivery operations platform foundation for orders, agents,
              tracking, and pricing workflows.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-950">
                Application shell
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                React, TypeScript, Vite, React Router, and Tailwind are wired
                for the next implementation phase.
              </p>
            </div>

            <div className={`rounded-lg border p-6 shadow-sm ${statusTone}`}>
              <p className="text-sm font-medium">Backend connection</p>
              <p className="mt-3 text-2xl font-semibold">{statusLabel}</p>
              <p className="mt-2 text-sm opacity-80">
                Single health check on page load.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

export default HomePage
