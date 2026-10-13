/**
 * The round postmark every job wears. It shows where the job is and the day it was posted,
 * the same way a real postmark shows the town and the day a letter was mailed.
 * Each one sits at its own small tilt so the list looks hand stamped and not printed.
 */

interface Props {
  /** Top line, usually the city */
  place: string
  /** Bottom line, usually the province or REMOTE */
  region: string
  /** The date in the middle */
  date: Date
  /** Something to pick the tilt from so the same job always tilts the same way */
  seed: string
  tone?: 'air' | 'post'
  size?: 'sm' | 'md'
  /** Plays the little stamp landing when it changes */
  stamp?: boolean
}

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

function tiltFor(seed: string): number {
  const hash = [...seed].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 11)
  return (hash % 15) - 10
}

export default function Postmark({ place, region, date, seed, tone = 'air', size = 'md', stamp = false }: Props) {
  const color = tone === 'post' ? 'text-post-600' : 'text-air-700'
  const dims = size === 'sm' ? 'h-[68px] w-[68px]' : 'h-[78px] w-[78px]'
  const day = String(date.getDate()).padStart(2, '0')
  const label = `Posted ${date.toLocaleDateString('en-CA', { month: 'long', day: 'numeric' })} in ${place}`
  // Long city names get squeezed so they still fit the ring
  const top = place.length > 10 ? `${place.slice(0, 9)}.` : place

  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      style={{ ['--tilt' as string]: `${tiltFor(seed)}deg`, transform: `rotate(${tiltFor(seed)}deg)` }}
      className={`relative inline-flex shrink-0 select-none flex-col items-center justify-center rounded-full border-2 border-current text-center uppercase leading-none ${color} ${dims} ${stamp ? 'postmark-stamp' : ''}`}
    >
      <span className="absolute inset-[4px] rounded-full border border-current opacity-70" aria-hidden="true" />
      <span className="stretch-condensed text-[9px] font-bold tracking-[0.06em]" aria-hidden="true">{top}</span>
      <span className="stretch-condensed my-[3px] text-[17px] font-extrabold tracking-tight" aria-hidden="true">
        {day} {MONTHS[date.getMonth()]}
      </span>
      <span className="stretch-condensed text-[9px] font-bold tracking-[0.06em]" aria-hidden="true">{region}</span>
    </span>
  )
}
