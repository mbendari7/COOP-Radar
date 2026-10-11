/**
 * RichText — renders the small subset of Markdown the AI assistant uses:
 * "## Heading" lines, "- " / "* " / "• " bullets, **bold**, and the "Resume: " / "Posting: "
 * citation prefixes (bolded). Everything is rendered as text — never as HTML.
 */

import type { ReactNode } from 'react'

/** Bold "**x**" spans and the "Resume: " / "Posting: " citation prefixes. */
function inline(text: string, key: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|(?:Resume|Posting):\s)/g).map((part, i) => {
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={`${key}-${i}`}>{part.slice(2, -2)}</strong>
    if (/^(?:Resume|Posting):\s$/.test(part)) return <strong key={`${key}-${i}`}>{part}</strong>
    return <span key={`${key}-${i}`}>{part}</span>
  })
}

export default function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []

  const flushBullets = () => {
    if (bullets.length === 0) return
    const items = bullets
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="list-disc pl-5 space-y-1">
        {items.map((b, i) => <li key={i}>{inline(b, `li-${blocks.length}-${i}`)}</li>)}
      </ul>,
    )
    bullets = []
  }

  text.split('\n').forEach((raw, i) => {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)$/)
    if (bullet) {
      bullets.push(bullet[1])
      return
    }
    flushBullets()
    const heading = line.match(/^#{1,4}\s+(.*)$/)
    if (heading) {
      blocks.push(
        <p key={`h-${i}`} className="font-semibold text-gray-900 pt-1">{inline(heading[1], `h-${i}`)}</p>,
      )
    } else if (line.trim()) {
      blocks.push(<p key={`p-${i}`}>{inline(line, `p-${i}`)}</p>)
    }
  })
  flushBullets()

  return <div className="space-y-2">{blocks}</div>
}
