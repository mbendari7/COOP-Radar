/**
 * StatsPanel — shows application funnel stats: applied, interview, offer counts.
 * Displayed at the top of SavedPostingsPage.
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
    { label: 'Applied', value: totalApplied, color: 'text-blue-600' },
    {
      label: 'Interview Rate',
      value: `${interviewRate}%`,
      color: 'text-indigo-600',
      sub: `${totalInterview} of ${totalApplied}`,
    },
    { label: 'Offers', value: totalOffer, color: 'text-green-600' },
  ]

  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      {stats.map((s) => (
        <div
          key={s.label}
          className="bg-white rounded-lg border border-gray-200 px-4 py-3 text-center"
        >
          <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
          {s.sub && <p className="text-xs text-gray-400">{s.sub}</p>}
        </div>
      ))}
    </div>
  )
}
