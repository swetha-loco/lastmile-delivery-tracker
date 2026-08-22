import { Link } from 'react-router'

function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 text-slate-950">
      <section className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm">
        <p className="text-sm font-medium text-slate-500">404</p>
        <h1 className="mt-3 text-2xl font-semibold">Page not found</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          This frontend foundation only defines the home route for now.
        </p>
        <Link
          className="mt-6 inline-flex rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          to="/"
        >
          Back to home
        </Link>
      </section>
    </main>
  )
}

export default NotFoundPage
