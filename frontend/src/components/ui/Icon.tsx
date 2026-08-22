type IconName =
  | 'box'
  | 'route'
  | 'pin'
  | 'home'
  | 'plus'
  | 'list'
  | 'logOut'
  | 'user'
  | 'arrow'
  | 'calendar'
  | 'clock'
  | 'check'
  | 'alert'

const paths: Record<IconName, string> = {
  box: 'M5 8.5 12 4l7 4.5v7L12 20l-7-4.5v-7Zm7-4.5v7m-7-2.5 7 4.5m7-4.5-7 4.5',
  route:
    'M6 18a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm12-10a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM8 16h3a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7',
  pin: 'M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Zm0-8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  home: 'M4 11.5 12 5l8 6.5V20a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1v-8.5Z',
  plus: 'M12 5v14m-7-7h14',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  logOut: 'M10 17l5-5-5-5m5 5H3m7 8h9a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-9',
  user: 'M20 21a8 8 0 0 0-16 0m12-13a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  calendar:
    'M7 3v4m10-4v4M4 9h16M5 5h14a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Z',
  clock: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Zm0-14v5l3 2',
  check: 'm5 12 4 4L19 6',
  alert:
    'M12 9v4m0 4h.01M10.3 4.3 2.4 18a1.5 1.5 0 0 0 1.3 2.2h16.6a1.5 1.5 0 0 0 1.3-2.2L13.7 4.3a1.5 1.5 0 0 0-3.4 0Z',
}

export function Icon({
  name,
  className = 'h-5 w-5',
}: {
  name: IconName
  className?: string
}) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
      viewBox="0 0 24 24"
    >
      <path d={paths[name]} />
    </svg>
  )
}
