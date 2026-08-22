import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'

import { ApiError } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { FormField, TextInput } from '../../components/ui/FormField'
import { Icon } from '../../components/ui/Icon'
import { useAuth } from '../../lib/auth'

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (user?.role === 'CUSTOMER') {
    return <Navigate replace to="/dashboard" />
  }

  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to sign in')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthFrame
      title="Track every mile with confidence."
      subtitle="Sign in to create deliveries, approve quotes, and follow your shipment timeline."
    >
      <form className="grid gap-5" onSubmit={handleSubmit}>
        <FormField label="Email">
          <TextInput
            autoComplete="email"
            onChange={(event) => setEmail(event.target.value)}
            placeholder="customer@demo.local"
            required
            type="email"
            value={email}
          />
        </FormField>
        <FormField label="Password">
          <TextInput
            autoComplete="current-password"
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Your password"
            required
            type="password"
            value={password}
          />
        </FormField>
        {error ? <p className="rounded-lg bg-[#FDE7E7] p-3 text-sm font-bold text-[#B42318]">{error}</p> : null}
        <Button disabled={isSubmitting} type="submit">
          {isSubmitting ? 'Signing in...' : 'Sign in'}
        </Button>
        <p className="text-center text-sm font-semibold text-[#667085]">
          New customer?{' '}
          <Link className="font-extrabold text-[#F25F3A]" to="/register">
            Create an account
          </Link>
        </p>
      </form>
    </AuthFrame>
  )
}

export function AuthFrame({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <main className="min-h-screen bg-[#F7F8F6] px-5 py-8 text-[#142033]">
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-10 lg:grid-cols-[1fr_440px]">
        <div className="hidden lg:block">
          <div className="mb-8 flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-[#071D34] text-[#F25F3A]">
              <Icon name="box" className="h-6 w-6" />
            </span>
            <div className="font-extrabold leading-5">
              <p>Last-Mile</p>
              <p>Delivery Tracker</p>
            </div>
          </div>
          <h1 className="max-w-xl text-5xl font-extrabold leading-[1.05] tracking-[-0.02em] text-[#071D34]">
            {title}
          </h1>
          <p className="mt-5 max-w-lg text-lg font-medium leading-8 text-[#667085]">
            {subtitle}
          </p>
          <div className="mt-10 max-w-xl rounded-2xl border border-[#DDE5E1] bg-white p-6">
            <div className="grid gap-5">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#DDF5EF] text-[#128C7E]">
                  <Icon name="route" />
                </span>
                <div>
                  <p className="font-extrabold">Chennai GPO {'->'} Adyar</p>
                  <p className="text-sm font-semibold text-[#667085]">
                    Quote, confirm, track, and reschedule from one customer space.
                  </p>
                </div>
              </div>
              <div className="h-2 rounded-full bg-[#F1F5F2]">
                <div className="h-full w-3/4 rounded-full bg-[#128C7E]" />
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-[#DDE5E1] bg-white p-6 shadow-[0_24px_80px_rgba(7,29,52,0.08)] sm:p-8">
          <div className="mb-7 lg:hidden">
            <div className="mb-5 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#071D34] text-[#F25F3A]">
                <Icon name="box" className="h-5 w-5" />
              </span>
              <p className="font-extrabold">Last-Mile Delivery Tracker</p>
            </div>
            <h1 className="text-3xl font-extrabold leading-tight text-[#071D34]">{title}</h1>
          </div>
          {children}
        </div>
      </section>
    </main>
  )
}
