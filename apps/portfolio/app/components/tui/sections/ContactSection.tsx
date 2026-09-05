'use client';

import React from 'react';

interface ContactData {
  github: string;
  linkedin: string;
  email: string;
}

interface ContactSectionProps {
  data: ContactData;
}

export default function ContactSection({ data }: ContactSectionProps) {
  return (
    <div className="font-mono space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--starship-cyan)' }}>
          Contact
        </h2>
        <div className="h-px my-3" style={{ backgroundColor: 'var(--terminal-border)' }} />
      </div>

      <div className="space-y-3">
        <div
          className="tui-card p-3 flex items-center gap-3"
          style={{ borderLeft: '2px solid var(--starship-cyan)' }}
        >
          <span style={{ fontSize: '18px' }}>📧</span>
          <div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Email</div>
            <a
              href={`mailto:${data.email}`}
              style={{ color: 'var(--starship-cyan)' }}
              className="hover:underline"
            >
              {data.email}
            </a>
          </div>
        </div>

        <div
          className="tui-card p-3 flex items-center gap-3"
          style={{ borderLeft: '2px solid var(--starship-cyan)' }}
        >
          <span style={{ fontSize: '18px' }}>💼</span>
          <div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>LinkedIn</div>
            <a
              href={data.linkedin}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--starship-cyan)' }}
              className="hover:underline"
            >
              {data.linkedin.replace('https://', '')}
            </a>
          </div>
        </div>

        <div
          className="tui-card p-3 flex items-center gap-3"
          style={{ borderLeft: '2px solid var(--starship-cyan)' }}
        >
          <span style={{ fontSize: '18px' }}>🐙</span>
          <div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>GitHub</div>
            <a
              href={data.github}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: 'var(--starship-cyan)' }}
              className="hover:underline"
            >
              {data.github.replace('https://', '')}
            </a>
          </div>
        </div>
      </div>

      <div
        className="tui-card p-4"
        style={{ borderLeft: '2px solid var(--starship-green)' }}
      >
        <p style={{ color: 'var(--starship-green)' }}>💬 Open for:</p>
        <ul className="mt-2 space-y-1 text-sm" style={{ color: 'var(--text-secondary)' }}>
          <li>• Backend development opportunities</li>
          <li>• Software architecture discussions</li>
          <li>• AI/ML collaboration</li>
          <li>• Tech mentorship</li>
        </ul>
        <p className="mt-3 text-xs" style={{ color: 'var(--text-muted)' }}>
          Response: Usually within 48h
        </p>
      </div>
    </div>
  );
}