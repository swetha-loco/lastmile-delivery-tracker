import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'

export function FormField({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <label className="grid gap-2 text-sm font-bold text-[#142033]">
      <span>{label}</span>
      {children}
    </label>
  )
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="h-12 rounded-lg border border-[#DDE5E1] bg-white px-3 text-sm font-medium text-[#142033] outline-none transition placeholder:text-[#98A2B3] focus:border-[#128C7E] focus:ring-4 focus:ring-[#DDF5EF]"
      {...props}
    />
  )
}

export function TextArea(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="h-12 rounded-lg border border-[#DDE5E1] bg-white px-3 text-sm font-medium text-[#142033] outline-none transition placeholder:text-[#98A2B3] focus:border-[#128C7E] focus:ring-4 focus:ring-[#DDF5EF]"
      {...props}
    />
  )
}

export function SelectInput(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className="h-12 rounded-lg border border-[#DDE5E1] bg-white px-3 text-sm font-bold text-[#142033] outline-none transition focus:border-[#128C7E] focus:ring-4 focus:ring-[#DDF5EF]"
      {...props}
    />
  )
}
