'use client';

import Link from 'next/link';

export default function NotFound() {
  return (
    <div
      className="h-screen w-screen flex flex-col items-center justify-center p-8"
      style={{
        backgroundColor: 'var(--terminal-bg)',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-primary)',
      }}
    >
      <div
        className="rounded px-4 py-2 text-xs flex items-center gap-2"
        style={{
          backgroundColor: 'var(--terminal-bg-elevated)',
          border: '1px solid var(--terminal-border)',
          borderBottom: 'none',
          width: '100%',
          maxWidth: '480px',
        }}
      >
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--starship-red)' }} />
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--starship-yellow)' }} />
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--starship-green)' }} />
        <span className="ml-2" style={{ color: 'var(--text-muted)' }}>404.sh</span>
      </div>

      <div
        className="rounded-b p-6 text-sm leading-relaxed terminal-glitch-in"
        style={{
          backgroundColor: 'var(--terminal-bg-secondary)',
          border: '1px solid var(--terminal-border)',
          width: '100%',
          maxWidth: '480px',
        }}
      >
        <pre
          className="text-xs mb-4"
          style={{ color: 'var(--starship-yellow)' }}
        >
╭──────────────────────────────────────╮
│  COMMAND NOT FOUND                   │
╰──────────────────────────────────────╯
        </pre>

        <p className="mb-1" style={{ color: 'var(--text-secondary)' }}>
          <span style={{ color: 'var(--starship-red)' }}>$</span>{' '}
          <span style={{ color: 'var(--text-muted)' }}>visit</span>{' '}
          <span style={{ color: 'var(--text-primary)' }}>this/page</span>
        </p>
        <p className="text-xs mb-4" style={{ color: 'var(--starship-red)' }}>
          bash: this/page: No such file or directory
        </p>

        <pre className="text-xs mb-4 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
  Did you mean?
    <Link href="/" style={{ color: 'var(--starship-cyan)' }} className="hover:underline ml-4">
      ~/
    </Link>
    <span className="ml-4" style={{ color: 'var(--text-secondary)' }}>help</span>
    <span className="ml-4" style={{ color: 'var(--text-secondary)' }}>menu</span>
        </pre>

        <Link
          href="/"
          className="inline-block px-4 py-2 text-xs rounded no-underline mt-2"
          style={{
            backgroundColor: 'var(--terminal-bg-elevated)',
            color: 'var(--starship-green)',
            border: '1px solid var(--terminal-border)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--starship-green)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--terminal-border)';
          }}
        >
          $ cd ~
        </Link>
      </div>
    </div>
  );
}