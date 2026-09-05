'use client';

import React from 'react';

interface WelcomeBannerProps {
  onCommand: (cmd: string) => void;
  onDismiss: () => void;
}

const suggestions = [
  { label: 'help', cmd: 'help' },
  { label: 'about', cmd: 'about' },
  { label: 'projects', cmd: 'projects' },
  { label: 'menu', cmd: 'menu' },
];

export default function WelcomeBanner({
  onCommand,
  onDismiss,
}: WelcomeBannerProps) {
  const handlePillClick = (cmd: string) => {
    onCommand(cmd);
    onDismiss();
  };

  return (
    <div className="welcome-banner animate-fade-in">
      <pre className="welcome-banner-ascii">
{`╭──────────────────────────────────────────────╮
│                                              │
│   Welcome to Terminal Portfolio              │
│                                              │
│   Type a command or click a pill to get      │
│   started:                                   │
│                                              │
╰──────────────────────────────────────────────╯`}
      </pre>
      <div className="welcome-banner-pills">
        {suggestions.map((s) => (
          <button
            key={s.label}
            className="welcome-banner-pill"
            onClick={() => handlePillClick(s.cmd)}
            type="button"
          >
            [{s.label}]
          </button>
        ))}
      </div>
    </div>
  );
}
