import { Link } from 'react-router'

import { Icon } from '../components/ui/Icon'

function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F7F8F6] px-6 text-[#142033]">
      <section className="w-full max-w-md rounded-2xl border border-[#DDE5E1] bg-white p-8 text-center shadow-[0_18px_50px_rgba(7,29,52,0.06)]">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-[#DDF5EF] text-[#128C7E]">
          <Icon name="route" className="h-7 w-7" />
        </div>
        <p className="mt-6 text-sm font-extrabold uppercase tracking-[0.12em] text-[#667085]">
          Route not found
        </p>
        <h1 className="mt-3 text-2xl font-extrabold">This stop is outside the map</h1>
        <p className="mt-3 text-sm font-semibold leading-6 text-[#667085]">
          Head back to your customer workspace to create, track, or reschedule a
          delivery.
        </p>
        <Link
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-[#F25F3A] px-4 text-sm font-bold text-white hover:bg-[#E24E2E]"
          to="/dashboard"
        >
          Back to dashboard
        </Link>
      </section>
    </main>
  )
}

export default NotFoundPage
