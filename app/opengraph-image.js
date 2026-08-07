import { ImageResponse } from 'next/og'
import { readFile } from 'node:fs/promises'
import { join } from 'node:path'

export const alt = 'RTOLookup — Decode any Indian vehicle number plate'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default async function Image() {
  const display = await readFile(join(process.cwd(), 'public/fonts/ChakraPetch-700.ttf'))

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '80px',
          background: '#0E1117',
          backgroundImage: 'radial-gradient(ellipse 70% 60% at 70% 0%, rgba(26,60,138,0.25) 0%, transparent 70%)',
          fontFamily: 'Chakra',
        }}
      >
        {/* Number plate */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            background: '#F2F2EE',
            border: '6px solid #9AA3B0',
            borderRadius: '14px',
            padding: '14px 28px 14px 14px',
            gap: '20px',
            alignSelf: 'flex-start',
            marginBottom: '48px',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', background: '#1A3C8A', padding: '12px 16px', borderRadius: '6px', alignItems: 'center', gap: '6px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', width: '40px' }}>
              <div style={{ height: '6px', background: '#FF9933' }} />
              <div style={{ height: '6px', background: '#FFFFFF' }} />
              <div style={{ height: '6px', background: '#138808' }} />
            </div>
            <div style={{ color: 'white', fontSize: '20px', letterSpacing: '3px' }}>IND</div>
          </div>
          <div style={{ fontSize: '90px', color: '#0C0C0C', letterSpacing: '8px' }}>MH 01</div>
        </div>

        <div style={{ display: 'flex', fontSize: '34px', color: '#F0A000', letterSpacing: '4px', marginBottom: '16px' }}>
          RTOLOOKUP
        </div>
        <div style={{ display: 'flex', fontSize: '64px', color: '#E4E8F0', lineHeight: 1.1, maxWidth: '900px' }}>
          Decode any Indian number plate instantly
        </div>
        <div style={{ display: 'flex', fontSize: '30px', color: '#8A96A8', marginTop: '24px' }}>
          1,400+ RTO codes · 36 states · plain-English guides
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [{ name: 'Chakra', data: display, weight: 700, style: 'normal' }],
    }
  )
}
