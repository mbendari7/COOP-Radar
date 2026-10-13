/** A small mark for jobs that come live from an employer's own career board. */
export default function LiveBadge() {
  return (
    <span
      className="label-form ml-2 inline-block rounded-sm border border-air-700 px-1.5 py-px align-middle !text-[10px] !text-air-700"
      title="Imported from the employer's own careers page. You apply there."
    >
      Live
    </span>
  )
}
