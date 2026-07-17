import { useState } from 'react'
import type { Citation } from '../types'

function sourceLabel(citation: Citation): string {
  const parts = [citation.filename]
  if (citation.page != null) parts.push(`p.${citation.page}`)
  if (citation.section) parts.push(`“${citation.section}”`)
  return parts.join(' · ')
}

export default function Citations({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState(false)
  if (citations.length === 0) return null

  return (
    <div className="citations">
      <button
        className="citations-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className={'chevron' + (open ? ' open' : '')} aria-hidden="true" />
        {citations.length} source{citations.length > 1 ? 's' : ''}
      </button>
      {open && (
        <ul className="citation-list">
          {citations.map((citation) => (
            <li key={citation.marker} className="citation-card">
              <div className="citation-head">
                <span className="citation-marker">{citation.marker}</span>
                <span className="citation-source">{sourceLabel(citation)}</span>
                <span className="citation-score" title="similarity score">
                  {(citation.score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="citation-meter" aria-hidden="true">
                <span style={{ width: `${Math.round(citation.score * 100)}%` }} />
              </div>
              <p className="citation-snippet">{citation.snippet}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
