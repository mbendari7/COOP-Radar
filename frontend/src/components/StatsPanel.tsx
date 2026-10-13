/**
 * How the applications are going, in one ruled line. Applied, how many got an interview and offers.
 * It sits at the top of the tracker.
 */

interface Props {
  totalApplied: number
  totalInterview: number
  totalOffer: number
}

export default function StatsPanel({ totalApplied, totalInterview, totalOffer }: Props) {
  const interviewRate = totalApplied > 0
    ? Math.round((totalInterview / totalApplied) * 100)
    : 0

  const stats = [
    { label: 'Applied', value: String(totalApplied), sub: '' },
    { label: 'Interview rate', value: `${interviewRate}%`, sub: `${totalInterview} of ${totalApplied}` },
    { label: 'Offers', value: String(totalOffer), sub: '' },
  ]

  return (
    <dl className="mb-6 flex flex-wrap divide-x divide-gray-300 border-y-[1.5px] border-gray-900">
      {stats.map((s) => (
        <div key={s.label} className="flex items-baseline gap-2 px-5 py-3 first:pl-0">
          <dt className="label-form">{s.label}</dt>
          <dd className="stretch-semi text-2xl font-extrabold tabular-nums text-gray-900">
            {s.value}
            {s.sub && <span className="ml-1.5 text-sm font-semibold text-gray-600">{s.sub}</span>}
          </dd>
        </div>
      ))}
    </dl>
  )
}
