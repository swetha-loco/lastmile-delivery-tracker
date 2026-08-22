import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

const variants: Record<ButtonVariant, string> = {
  primary:
    'bg-[#F25F3A] text-white shadow-[0_10px_24px_rgba(242,95,58,0.20)] hover:bg-[#E24E2E]',
  secondary:
    'border border-[#DDE5E1] bg-white text-[#142033] hover:border-[#C9D6D1] hover:bg-[#F7F8F6]',
  ghost: 'text-[#667085] hover:bg-[#F1F5F2] hover:text-[#142033]',
  danger:
    'border border-[#F1B5B5] bg-[#FDE7E7] text-[#B42318] hover:bg-[#FADCDC]',
}

export function Button({
  children,
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  children: ReactNode
}) {
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 text-sm font-bold transition active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
