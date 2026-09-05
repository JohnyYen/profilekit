'use client';

import React from 'react';
import { HINT_IDS, hintForId, type KeyBinding } from './keymap';

interface TuiStatusBarProps {
  activeSection: string;
  currentIndex: number;
  totalSections: number;
  hasSearch?: boolean;
}

const SEPARATOR = '·';

/**
 * Status bar (REQ-D3/T29). Desktop renders the shared KEYMAP hints (no
 * hardcoded strings — REQ-X4); mobile renders a touch hint only, advertising
 * no dead keyboard keys.
 */
export default function TuiStatusBar({
  activeSection,
  currentIndex,
  totalSections,
  hasSearch,
}: TuiStatusBarProps) {
  const hints: KeyBinding[] = HINT_IDS.map(hintForId).filter(
    (h): h is KeyBinding => Boolean(h)
  );

  return (
    <div
      className="px-4 py-2 text-xs font-mono flex items-center gap-4 flex-shrink-0"
      style={{
        backgroundColor: 'var(--terminal-bg-secondary)',
        color: 'var(--text-muted)',
        borderTop: '1px solid var(--terminal-border)',
      }}
    >
      {/* Desktop: KEYMAP-driven hints */}
      <span className="hidden sm:flex items-center gap-4">
        {hints
          .filter(h => h.statusHint)
          .map((h, i) => (
            <React.Fragment key={h.id}>
              {i > 0 && <span>{SEPARATOR}</span>}
              <span>{h.statusHint}</span>
            </React.Fragment>
          ))}
        {hasSearch && (
          <>
            <span>{SEPARATOR}</span>
            <span style={{ color: 'var(--starship-cyan)' }}>🔍 Searching…</span>
          </>
        )}
      </span>

      {/* Mobile: touch hint only — no dead key hints (REQ-D3) */}
      <span className="flex sm:hidden" style={{ color: 'var(--text-muted)' }}>
        Tap a tab to switch
      </span>

      <span className="ml-auto">
        Section {currentIndex}/{totalSections} · {activeSection}
      </span>
    </div>
  );
}
