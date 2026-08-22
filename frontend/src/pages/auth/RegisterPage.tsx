import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'

import { ApiError, registerCustomer } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { FormField, TextInput } from '../../components/ui/FormField'
import { useAuth } from '../../lib/auth'
import { AuthFrame } from './LoginPage'

export default function RegisterPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (user?.role === 'CUSTOMER') {
    return <Navigate replace to="/dashboard" />
  }

  function updateField(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await registerCustomer(form)
      await login(form.email, form.password)
      navigate('/dashboard', { replace: true })
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to register')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthFrame
      title="Create deliveries without guesswork."
      subtitle="Register as a customer to quote shipments, confirm pricing, and follow every status change."
    >
      <form className="grid gap-5" onSubmit={handleSubmit}>
        <FormField label="Name">
          <TextInput
            autoComplete="name"
            onChange={(event) => updateField('name', event.target.value)}
            placeholder="Arun Kumar"
            required
            value={form.name}
          />
        </FormField>
        <FormField label="Email">
          <TextInput
            autoComplete="email"
            onChange={(event) => updateField('email', event.target.value)}
            placeholder="you@example.com"
            required
            type="email"
            value={form.email}
          />
        </FormField>
        <FormField label="Phone">
          <TextInput
            autoComplete="tel"
            onChange={(event) => updateField('phone', event.target.value)}
            placeholder="+91 98765 43210"
            required
            value={form.phone}
          />
        </FormField>
        <FormField label="Password">
          <TextInput
            autoComplete="new-password"
            minLength={8}
            onChange={(event) => updateField('password', event.target.value)}
            placeholder="At least 8 characters"
            required
            type="password"
            value={form.password}
          />
        </FormField>
        {error ? <p className="rounded-lg bg-[#FDE7E7] p-3 text-sm font-bold text-[#B42318]">{error}</p> : null}
        <Button disabled={isSubmitting} type="submit">
          {isSubmitting ? 'Creating account...' : 'Create customer account'}
        </Button>
        <p className="text-center text-sm font-semibold text-[#667085]">
          Already registered?{' '}
          <Link className="font-extrabold text-[#F25F3A]" to="/login">
            Sign in
          </Link>
        </p>
      </form>
    </AuthFrame>
  )
}
