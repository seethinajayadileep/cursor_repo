'use client'

import Link from 'next/link'
import { useState, useEffect } from 'react'

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [theme, setTheme] = useState('dark')

  useEffect(() => {
    const current = document.documentElement.getAttribute('data-theme') || 'dark'
    setTheme(current)
  }, [])

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.setAttribute('data-theme', next)
    try { localStorage.setItem('theme', next) } catch {}
    setTheme(next)
  }

  const navLinks = [
    { href: '/#states', label: 'States' },
    { href: '/guides', label: 'Guides' },
    { href: '/guides/check-vehicle-owner', label: 'Check Owner' },
  ]

  return (
    <header className="site-header">
      <div className="container header-inner">
        <Link href="/" className="site-logo" aria-label="RTOLookup home" onClick={() => setMenuOpen(false)}>
          <div className="logo-plate" aria-hidden="true">
            <span className="logo-ind">IND</span>
            <span className="logo-text">RTO</span>
          </div>
          <span className="logo-name">Lookup</span>
        </Link>

        <nav className="site-nav" aria-label="Main navigation">
          {navLinks.map(l => (
            <Link key={l.href} href={l.href} className="nav-link">{l.label}</Link>
          ))}
        </nav>

        <div className="header-actions">
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
          >
            {/* Sun (shown in dark mode → click to go light) */}
            <svg className="icon-sun" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="4"/>
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
            </svg>
            {/* Moon (shown in light mode → click to go dark) */}
            <svg className="icon-moon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>

          <button
            type="button"
            className="menu-btn"
            onClick={() => setMenuOpen(o => !o)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
          >
            <span className={`menu-icon ${menuOpen ? 'open' : ''}`} aria-hidden="true">
              <span /><span /><span />
            </span>
          </button>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      <nav
        id="mobile-menu"
        className={`mobile-menu ${menuOpen ? 'open' : ''}`}
        aria-label="Mobile navigation"
        hidden={!menuOpen}
      >
        <div className="container">
          {navLinks.map(l => (
            <Link key={l.href} href={l.href} className="mobile-link" onClick={() => setMenuOpen(false)}>
              {l.label}
            </Link>
          ))}
        </div>
      </nav>

      <style>{`
        .site-header {
          position: sticky;
          top: 0;
          z-index: 100;
          background: var(--header-bg);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border-bottom: 1px solid var(--tarmac-border);
        }

        .header-inner {
          display: flex;
          align-items: center;
          justify-content: space-between;
          height: 60px;
          gap: 16px;
        }

        .site-logo {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-shrink: 0;
        }

        .logo-plate {
          display: flex;
          align-items: center;
          background: var(--plate-white);
          border: 2px solid var(--plate-chrome);
          border-radius: 4px;
          overflow: hidden;
          box-shadow: 0 2px 8px rgba(0,0,0,0.25);
          height: 28px;
        }

        .logo-ind {
          background: var(--ind-blue);
          color: white;
          font-family: var(--font-display);
          font-size: 8px;
          font-weight: 800;
          letter-spacing: 1px;
          padding: 0 5px;
          height: 100%;
          display: flex;
          align-items: center;
        }

        .logo-text {
          font-family: var(--font-display);
          font-size: 13px;
          font-weight: 700;
          color: var(--plate-black);
          letter-spacing: 2px;
          padding: 0 8px;
        }

        .logo-name {
          font-family: var(--font-display);
          font-size: 16px;
          font-weight: 700;
          color: var(--text-primary);
          letter-spacing: 1px;
        }

        .site-nav {
          display: flex;
          align-items: center;
          gap: 4px;
          margin-left: auto;
        }

        .nav-link {
          font-size: var(--text-sm);
          color: var(--text-secondary);
          padding: 6px 12px;
          border-radius: var(--r-md);
          transition: color 0.15s, background 0.15s;
        }

        .nav-link:hover {
          color: var(--text-primary);
          background: var(--tarmac-raised);
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .theme-toggle {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 38px;
          height: 38px;
          border-radius: var(--r-md);
          color: var(--text-secondary);
          transition: color 0.15s, background 0.15s;
        }

        .theme-toggle:hover {
          color: var(--text-primary);
          background: var(--tarmac-raised);
        }

        /* Show sun in dark mode, moon in light mode */
        .icon-moon { display: none; }
        :root[data-theme="light"] .icon-sun { display: none; }
        :root[data-theme="light"] .icon-moon { display: block; }

        .menu-btn {
          display: none;
          width: 38px;
          height: 38px;
          align-items: center;
          justify-content: center;
          border-radius: var(--r-md);
          color: var(--text-primary);
        }

        .menu-btn:hover { background: var(--tarmac-raised); }

        .menu-icon {
          display: flex;
          flex-direction: column;
          justify-content: center;
          gap: 4px;
          width: 20px;
          height: 20px;
        }

        .menu-icon span {
          display: block;
          height: 2px;
          width: 100%;
          background: currentColor;
          border-radius: 2px;
          transition: transform 0.2s var(--ease), opacity 0.2s var(--ease);
        }

        .menu-icon.open span:nth-child(1) { transform: translateY(6px) rotate(45deg); }
        .menu-icon.open span:nth-child(2) { opacity: 0; }
        .menu-icon.open span:nth-child(3) { transform: translateY(-6px) rotate(-45deg); }

        .mobile-menu {
          border-bottom: 1px solid var(--tarmac-border);
          background: var(--header-bg);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          animation: menu-drop 0.18s var(--ease);
        }

        @keyframes menu-drop {
          from { opacity: 0; transform: translateY(-8px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .mobile-menu .container {
          display: flex;
          flex-direction: column;
          padding-top: 8px;
          padding-bottom: 12px;
        }

        .mobile-link {
          font-size: var(--text-base);
          font-weight: 500;
          color: var(--text-primary);
          padding: 14px 4px;
          border-bottom: 1px solid var(--tarmac-border);
        }

        .mobile-link:last-child { border-bottom: none; }
        .mobile-link:hover { color: var(--accent-text); }

        @media (max-width: 640px) {
          .site-nav { display: none; }
          .menu-btn { display: flex; }
        }

        @media (min-width: 641px) {
          .mobile-menu { display: none; }
        }
      `}</style>
    </header>
  )
}
