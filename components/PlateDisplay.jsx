export default function PlateDisplay({ code, size = 'md' }) {
  const sizes = {
    sm: { plate: '18px', gap: '6px', hologram: '16px', indH: '32px', indP: '3px 5px', indText: '7px', flag: '14px', flagH: '2px' },
    md: { plate: '26px', gap: '8px', hologram: '22px', indH: '44px', indP: '4px 7px', indText: '9px', flag: '18px', flagH: '3px' },
    lg: { plate: '36px', gap: '10px', hologram: '28px', indH: '56px', indP: '5px 9px', indText: '11px', flag: '22px', flagH: '4px' },
    xl: { plate: '48px', gap: '12px', hologram: '36px', indH: '70px', indP: '6px 10px', indText: '13px', flag: '28px', flagH: '5px' },
  }

  const s = sizes[size] || sizes.md

  return (
    <div
      className="plate"
      style={{ gap: s.gap }}
      aria-label={`Vehicle number plate for RTO code ${code}`}
    >
      <div
        className="plate-hologram"
        style={{ width: s.hologram, height: s.hologram }}
        aria-hidden="true"
      />
      <div
        className="plate-ind"
        style={{ padding: s.indP, minHeight: s.indH }}
        aria-hidden="true"
      >
        <div className="plate-flag" style={{ width: s.flag }}>
          <span style={{ background: '#FF9933', height: s.flagH }} />
          <span style={{ background: '#FFFFFF', height: s.flagH }} />
          <span style={{ background: '#138808', height: s.flagH }} />
        </div>
        <span className="plate-ind-text" style={{ fontSize: s.indText }}>IND</span>
      </div>
      <span
        className="plate-number"
        style={{ fontSize: s.plate, letterSpacing: size === 'xl' ? '5px' : '3px' }}
      >
        {code}
      </span>
    </div>
  )
}
