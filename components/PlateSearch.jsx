'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'

const STATE_PREFIXES = [
  'AN','AP','AR','AS','BR','CH','CG','DD','DL','DN','GA','GJ','HP','HR',
  'JH','JK','KA','KL','LA','LD','MH','ML','MN','MP','MZ','NL','OD','PB',
  'PY','RJ','SK','TG','TN','TR','TS','UK','UP','WB',
]

export default function PlateSearch() {
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const router = useRouter()
  const inputRef = useRef(null)

  const normalized = input.trim().toUpperCase().replace(/\s+/g, '-')

  const isValidRTO = (val) => {
    return /^[A-Z]{2}-?\d{1,2}$/i.test(val.trim())
  }

  const handleSearch = (e) => {
    e.preventDefault()
    setError('')
    if (!input.trim()) return

    const code = normalized
    if (isValidRTO(code)) {
      const [st, num] = code.split('-')
      const padded = `${st}-${num.padStart(2, '0')}`
      router.push(`/rto/${padded.toLowerCase()}`)
    } else {
      setError('Enter a valid RTO code like MH-01 or KA-03')
      inputRef.current?.focus()
    }
  }

  const stateCode = normalized.split('-')[0] || ''
  const distCode  = normalized.split('-')[1] || ''
  const isKnownState = STATE_PREFIXES.includes(stateCode)

  return (
    <div className="plate-search-wrap">
      <form onSubmit={handleSearch} className="plate-search-form" noValidate>

        {/* The plate IS the input */}
        <div className={`plate plate-interactive ${input ? 'plate-active' : ''}`}>
          <div className="plate-hologram" aria-hidden="true" />

          <div className="plate-ind" aria-hidden="true">
            <div className="plate-flag" style={{ width: '18px' }}>
              <span style={{ background: '#FF9933', height: '3px', display: 'block' }} />
              <span style={{ background: '#FFFFFF', height: '3px', display: 'block' }} />
              <span style={{ background: '#138808', height: '3px', display: 'block' }} />
            </div>
            <span className="plate-ind-text">IND</span>
          </div>

          <div className="plate-input-zone">
            {input ? (
              <div className="plate-preview" aria-hidden="true">
                <span className={`plate-state ${isKnownState ? 'known' : ''}`}>{stateCode || 'ST'}</span>
                <span className="plate-sep"> – </span>
                <span className="plate-dist">{distCode || '00'}</span>
              </div>
            ) : (
              <div className="plate-placeholder" aria-hidden="true">
                <span>MH</span><span className="plate-sep"> – </span><span>01</span>
              </div>
            )}
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => { setInput(e.target.value); setError('') }}
              placeholder="e.g. MH-01"
              className="plate-real-input"
              aria-label="Enter RTO code"
              maxLength={8}
              autoComplete="off"
              autoCorrect="off"
              autoCapitalize="characters"
              spellCheck="false"
            />
          </div>

          <button type="submit" className="plate-go-btn" aria-label="Look up RTO">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </button>
        </div>

        {error && <p className="plate-error" role="alert">{error}</p>}
      </form>

      <p className="plate-hint">Enter a state code + district number — like <strong>MH-01</strong>, <strong>DL-4</strong>, or <strong>KA-03</strong></p>

      <style>{`
        .plate-search-wrap {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 12px;
        }

        .plate-search-form {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .plate-interactive {
          cursor: text;
          transition: box-shadow 0.2s var(--ease), border-color 0.2s var(--ease);
          padding-right: 8px;
        }

        .plate-interactive:focus-within {
          border-color: var(--amber);
          box-shadow: var(--shadow-plate), 0 0 0 3px rgba(240,160,0,0.2);
        }

        .plate-input-zone {
          position: relative;
          flex: 1;
          min-width: 180px;
        }

        .plate-preview,
        .plate-placeholder {
          font-family: var(--font-display);
          font-size: clamp(24px, 5vw, 32px);
          font-weight: 700;
          color: var(--plate-black);
          letter-spacing: 4px;
          line-height: 1;
          pointer-events: none;
          user-select: none;
          white-space: nowrap;
        }

        .plate-placeholder {
          color: #AAAAAA;
        }

        .plate-state.known {
          color: var(--ind-blue);
        }

        .plate-sep {
          color: #888;
          letter-spacing: 0;
        }

        .plate-real-input {
          position: absolute;
          inset: 0;
          opacity: 0;
          width: 100%;
          height: 100%;
          cursor: text;
          font-size: 16px; /* prevents iOS zoom */
        }

        .plate-go-btn {
          background: var(--amber);
          color: var(--plate-black);
          border-radius: var(--r-sm);
          padding: 8px 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          font-weight: 700;
          transition: background 0.15s, transform 0.1s;
          z-index: 1;
        }

        .plate-go-btn:hover { background: var(--amber-bright); }
        .plate-go-btn:active { transform: scale(0.95); }

        .plate-error {
          font-size: var(--text-sm);
          color: var(--red-alert);
          padding-left: 2px;
        }

        .plate-hint {
          font-size: var(--text-sm);
          color: var(--text-muted);
        }

        .plate-hint strong {
          color: var(--text-secondary);
          font-family: var(--font-mono);
        }
      `}</style>
    </div>
  )
}
