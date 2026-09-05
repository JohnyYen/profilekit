'use client';

import React, { useState } from 'react';
import { downloadCv } from '../../../lib/download';

interface CvSectionProps {
  cvUrl?: string;
}

export default function CvSection({ cvUrl }: CvSectionProps) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    if (!cvUrl) return;
    setDownloading(true);
    try {
      // Shared util so the TUI Enter action (REQ-A6) triggers the same download.
      await downloadCv(cvUrl);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="font-mono space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--starship-cyan)' }}>
          CV / Resume
        </h2>
        <div className="h-px my-3" style={{ backgroundColor: 'var(--terminal-border)' }} />
      </div>

      <div
        className="tui-card p-4"
        style={{ borderLeft: '2px solid var(--starship-yellow)' }}
      >
        <div className="flex items-center gap-3 mb-3">
          <span style={{ fontSize: '24px' }}>📄</span>
          <div>
            <p style={{ color: 'var(--text-primary)' }}>Johny A. Pedraza Romero CV</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              PDF — 69 KB · Last release: 2026-07-30
            </p>
          </div>
        </div>

        <button
          onClick={handleDownload}
          disabled={downloading}
          className="w-full px-4 py-3 rounded text-sm text-center cursor-pointer font-mono"
          style={{
            backgroundColor: 'var(--terminal-bg-elevated)',
            color: downloading ? 'var(--text-muted)' : 'var(--starship-yellow)',
            border: '1px solid var(--terminal-border)',
            transition: 'border-color 0.15s ease',
          }}
          onMouseEnter={(e) => {
            if (!downloading) e.currentTarget.style.borderColor = 'var(--starship-yellow)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--terminal-border)';
          }}
        >
          {downloading ? '⏳ Downloading...' : '⬇ Download CV'}
        </button>

        {!cvUrl && (
          <p className="mt-3 text-xs text-center" style={{ color: 'var(--text-muted)' }}>
            CV URL not configured
          </p>
        )}
      </div>

      <div
        className="tui-card p-4"
        style={{ borderLeft: '2px solid var(--starship-yellow)' }}
      >
        <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--starship-yellow)' }}>
          Contents
        </h3>
        <ul className="space-y-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
          <li>• Professional Summary</li>
          <li>• Work Experience</li>
          <li>• Skills &amp; Technologies</li>
          <li>• Projects</li>
          <li>• Education</li>
        </ul>
      </div>
    </div>
  );
}