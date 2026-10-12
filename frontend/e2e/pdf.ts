/** A tiny valid one-page PDF with the given lines of text, so tests need no binary fixtures. */

export function resumePdf(lines: string[]): Buffer {
  const esc = (s: string) => s.replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)')
  const stream = lines.map((line, i) => `BT /F1 12 Tf 50 ${750 - i * 20} Td (${esc(line)}) Tj ET`).join('\n')
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${Buffer.byteLength(stream, 'latin1')} >>\nstream\n${stream}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ].map((body, i) => `${i + 1} 0 obj\n${body}\nendobj\n`)

  const header = '%PDF-1.4\n'
  let offset = header.length
  let xref = `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  for (const o of objects) {
    xref += `${String(offset).padStart(10, '0')} 00000 n \n`
    offset += Buffer.byteLength(o, 'latin1')
  }
  const trailer = `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${offset}\n%%EOF\n`
  return Buffer.from(header + objects.join('') + xref + trailer, 'latin1')
}
