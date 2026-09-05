'use client';

import React, { useEffect, useRef } from 'react';
import { KEYMAP_GROUPS } from './keymap';

interface TuiShortcutsProps {
  onClose: () => void;
}

/**
 * Keyboard shortcuts overlay (REQ-X4). Every key string is derived from the
 * shared KEYMAP const — no hardcoded duplicates across surfaces.
 */
export default function TuiShortcuts({ onClose }: TuiShortcutsProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    overlayRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  return (
    <div
      ref={overlayRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onClick={onClose}
      className="absolute inset-0 z-10 flex items-center justify-center p-6"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.7)' }}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="font-mono max-w-lg w-full rounded p-6"
        style={{
          backgroundColor: 'var(--terminal-bg-secondary)',
          border: '1px solid var(--terminal-border)',
        }}
      >
        {/* Title */}
        <div className="text-center mb-5">
          <span className="text-sm font-bold" style={{ color: 'var(--starship-cyan)' }}>
            ╭─ Keyboard Shortcuts ───────────────────────────╮
          </span>
        </div>

        {/* Groups — all sourced from KEYMAP */}
        <div className="space-y-5">
          {KEYMAP_GROUPS.map(group => (
            <div key={group.title}>
              <h3
                className="text-xs font-semibold mb-2 uppercase tracking-wider"
                style={{ color: 'var(--starship-yellow)' }}
              >
                {group.title}
              </h3>
              <div className="space-y-1.5">
                {group.items.map(kb => (
                  <div
                    key={kb.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <kbd
                      className="px-2 py-0.5 rounded text-xs"
                      style={{
                        backgroundColor: 'var(--terminal-bg-elevated)',
                        color: 'var(--starship-green)',
                        border: '1px solid var(--terminal-border)',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {kb.keys}
                    </kbd>
                    <span style={{ color: 'var(--text-secondary)' }}>{kb.description}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-5 text-center">
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Press <kbd style={{ color: 'var(--starship-green)' }}>Esc</kbd> to close
          </span>
        </div>

        <div className="text-center mt-1">
          <span className="text-xs" style={{ color: 'var(--starship-cyan)' }}>
            ╰──────────────────────────────────────────────────╯
          </span>
        </div>
      </div>
    </div>
  );
}
