import { ImageResponse } from 'next/og'
import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { rtos, getRTO } from '@/data/rtos'

export const alt = 'RTO code details'
export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export async function generateStaticParams() {
  return rtos.map(r => ({ code: r.code.toLowerCase() }))
}

export default async function Image({ params }) {
  const { code } = await params
  const rto = getRTO(code) || { code: code.toUpperCase(), city: '', state: '', district: '' }
  const display = await readFile(join(process.cwd(), 'public/fonts/ChakraPetch-700.ttf'))
  const plateText = rto.code.replace('-', ' ')

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '70px',
          background: '#0E1117',
          backgroundImage: 'radial-gradient(ellipse 80% 70% at 50% 0%, rgba(26,60,138,0.22) 0%, transparent 70%)',
          fontFamily: 'Chakra',
        }}
      >
        <div style={{ display: 'flex', fontSize: '30px', color: '#F0A000', letterSpacing: '4px', marginBottom: '40px' }}>
          RTOLOOKUP
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            background: '#F2F2EE',
            border: '7px solid #9AA3B0',
            borderRadius: '16px',
            padding: '18px 40px 18px 18px',
            gap: '28px',
            marginBottom: '44px',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', background: '#1A3C8A', padding: '16px 20px', borderRadius: '8px', alignItems: 'center', gap: '8px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', width: '48px' }}>
              <div style={{ height: '7px', background: '#FF9933' }} />
              <div style={{ height: '7px', background: '#FFFFFF' }} />
              <div style={{ height: '7px', background: '#138808' }} />
            </div>
            <div style={{ color: 'white', fontSize: '24px', letterSpacing: '4px' }}>IND</div>
          </div>
          <div style={{ fontSize: '120px', color: '#0C0C0C', letterSpacing: '10px' }}>{plateText}</div>
        </div>

        <div style={{ display: 'flex', fontSize: '52px', color: '#E4E8F0' }}>
          {rto.city}
        </div>
        <div style={{ display: 'flex', fontSize: '32px', color: '#8A96A8', marginTop: '14px' }}>
          {rto.district ? `${rto.district}, ${rto.state}` : rto.state}
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [{ name: 'Chakra', data: display, weight: 700, style: 'normal' }],
    }
  )
}
