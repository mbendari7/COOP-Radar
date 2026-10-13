/**
 * Small line icons on a 24px grid with a 1.75 stroke, so the site looks the same on every
 * device. Each one takes a className for size and colour and is hidden from screen readers.
 */

import type { ReactNode } from 'react'

function Icon({ className = 'h-5 w-5', children }: { className?: string; children: ReactNode }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="square"
      strokeLinejoin="miter"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

type P = { className?: string }

/** The CoopRadar mark. A postmark ring with a radar sweep, white on the red bar */
export const LogoMark = ({ className = 'h-8 w-8' }: P) => (
  <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
    <circle cx="16" cy="16" r="14" fill="none" stroke="currentColor" strokeWidth="2.2" />
    <circle cx="16" cy="16" r="9.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
    <path d="M16 16 L24 8" stroke="currentColor" strokeWidth="2.6" strokeLinecap="square" />
    <circle cx="16" cy="16" r="2.4" fill="currentColor" />
  </svg>
)

export const UploadIcon = (p: P) => (
  <Icon {...p}><path d="M12 15V4m0 0L8 8m4-4 4 4" /><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" /></Icon>
)
export const FileIcon = (p: P) => (
  <Icon {...p}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h4" /></Icon>
)
export const CheckIcon = (p: P) => (
  <Icon {...p}><path d="m5 12.5 4.5 4.5L19 7.5" /></Icon>
)
export const PinIcon = (p: P) => (
  <Icon {...p}><path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z" /><circle cx="12" cy="10" r="2.3" /></Icon>
)
export const BriefcaseIcon = (p: P) => (
  <Icon {...p}><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M3 12.5h18" /></Icon>
)
export const SearchIcon = (p: P) => (
  <Icon {...p}><circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.2-4.2" /></Icon>
)
export const FilterIcon = (p: P) => (
  <Icon {...p}><path d="M4 6h16M7 12h10M10 18h4" /></Icon>
)
export const XIcon = (p: P) => (
  <Icon {...p}><path d="M6 6l12 12M18 6 6 18" /></Icon>
)
export const ArrowRightIcon = (p: P) => (
  <Icon {...p}><path d="M5 12h14m-5-5 5 5-5 5" /></Icon>
)
export const ClockIcon = (p: P) => (
  <Icon {...p}><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></Icon>
)
export const BuildingIcon = (p: P) => (
  <Icon {...p}><path d="M4 20V5a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v15M15 9h4a1 1 0 0 1 1 1v10M3 20h18" /><path d="M8 8h3M8 12h3M8 16h3" /></Icon>
)
export const ListIcon = (p: P) => (
  <Icon {...p}><path d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01" /></Icon>
)
export const GridIcon = (p: P) => (
  <Icon {...p}><rect x="4" y="4" width="7" height="7" rx="1.5" /><rect x="13" y="4" width="7" height="7" rx="1.5" /><rect x="4" y="13" width="7" height="7" rx="1.5" /><rect x="13" y="13" width="7" height="7" rx="1.5" /></Icon>
)
export const ExternalIcon = (p: P) => (
  <Icon {...p}><path d="M14 4h6v6M20 4l-9 9" /><path d="M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4" /></Icon>
)
export const TrendIcon = (p: P) => (
  <Icon {...p}><path d="m4 16 5-5 4 4 7-7" /><path d="M15 8h5v5" /></Icon>
)
export const PenIcon = (p: P) => (
  <Icon {...p}><path d="M4 20h4L19 9a2.8 2.8 0 0 0-4-4L4 16z" /><path d="m13.5 6.5 4 4" /></Icon>
)
export const ChevronDownIcon = (p: P) => (
  <Icon {...p}><path d="m6 9 6 6 6-6" /></Icon>
)
export const ArrowUpIcon = (p: P) => (
  <Icon {...p}><path d="M12 19V5m-6 6 6-6 6 6" /></Icon>
)
export const ArrowDownIcon = (p: P) => (
  <Icon {...p}><path d="M12 5v14m-6-6 6 6 6-6" /></Icon>
)
export const TableIcon = (p: P) => (
  <Icon {...p}><rect x="3.5" y="5" width="17" height="14" /><path d="M3.5 10h17M3.5 14.5h17M9.5 5v14" /></Icon>
)
