'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[Terminal Portfolio Error]', error);
  }, [error]);

  return (
    <div
      className="h-screen w-screen flex flex-col items-center justify-center p-8 terminal-glitch-in"
      style={{
        backgroundColor: 'var(--terminal-bg)',
        fontFamily: 'var(--font-mono)',
        color: 'var(--text-primary)',
      }}
    >
      {/* Terminal header */}
      <div
        className="rounded-t px-4 py-2 text-xs flex items-center gap-2"
        style={{
          backgroundColor: 'var(--terminal-bg-elevated)',
          border: '1px solid var(--terminal-border)',
          borderBottom: 'none',
          width: '100%',
          maxWidth: '520px',
        }}
      >
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--starship-red)' }} />
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--starship-yellow)' }} />
        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: 'var(--starship-green)' }} />
        <span className="ml-2" style={{ color: 'var(--text-muted)' }}>error.sh — bash</span>
      </div>

      {/* Terminal body */}
      <div
        className="rounded-b p-6 text-sm leading-relaxed"
        style={{
          backgroundColor: 'var(--terminal-bg-secondary)',
          border: '1px solid var(--terminal-border)',
          width: '100%',
          maxWidth: '520px',
        }}
      >
        <pre
          className="text-xs mb-4"
          style={{ color: 'var(--starship-red)' }}
        >
╭──────────────────────────────────────╮
│  UNEXPECTED TERMINAL ERROR           │
╰──────────────────────────────────────╯
        </pre>

        <p className="mb-1" style={{ color: 'var(--text-secondary)' }}>
          <span style={{ color: 'var(--starship-red)' }}>✗</span> Something went wrong
        </p>
        <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
          {error.message || 'An unknown error occurred.'}
        </p>

        <div className="flex gap-3 mt-4">
          <button
            onClick={reset}
            className="px-4 py-2 text-xs cursor-pointer rounded"
            style={{
              backgroundColor: 'var(--terminal-bg-elevated)',
              color: 'var(--starship-cyan)',
              border: '1px solid var(--terminal-border)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--starship-cyan)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--terminal-border)';
            }}
          >
            $ try_again
          </button>

          <Link
            href="/"
            className="px-4 py-2 text-xs rounded no-underline"
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
            $ cd ~ &amp;&amp; reset
          </Link>
        </div>

        {error.digest && (
          <p className="mt-4 text-xs" style={{ color: 'var(--text-muted)' }}>
            Error digest: <span style={{ color: 'var(--text-secondary)' }}>{error.digest}</span>
          </p>
        )}

        <div className="mt-4 pt-3 border-t" style={{ borderColor: 'var(--terminal-border)' }}>
          <p className="text-xs" style={{ color: 'var(--starship-yellow)' }}>
            ⚑ If this persists,{' '}
            <a
              href="https://github.com/JohnyYen"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--starship-cyan)' }}
              className="hover:underline"
            >
              open an issue
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}