'use client';

import React from 'react';
import type { Section } from './keymap';

interface TuiSidebarProps {
  sections: Section[];
  activeSection: string;
  onSectionChange: (id: string) => void;
}

/**
 * Desktop section list (Area A). Uses the shared `Section` type from `keymap.ts`
 * so ids/labels/icons never drift, and marks the active section with
 * `aria-current` (REQ-A2/A6, REQ-X2). The nav element carries
 * `data-tui-sidebar` so the container Enter guard treats sidebar buttons as
 * MANAGED items — Enter is always intercepted there (hard gate 3).
 */
export default function TuiSidebar({ sections, activeSection, onSectionChange }: TuiSidebarProps) {
  return (
    <nav
      data-tui-sidebar
      className="flex-shrink-0 border-r overflow-y-auto hidden sm:flex flex-col"
      style={{
        width: '192px',
        borderColor: 'var(--terminal-border)',
        backgroundColor: 'var(--terminal-bg-secondary)',
      }}
      aria-label="Sections"
    >
      {/* Section list */}
      <div className="flex-1 py-4">
        {sections.map(section => {
          const isActive = section.id === activeSection;
          return (
            <button
              key={section.id}
              onClick={() => onSectionChange(section.id)}
              aria-current={isActive ? 'page' : undefined}
              className="w-full text-left px-4 py-3 flex items-center gap-1 transition-all duration-150 cursor-pointer group"
              style={{
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'rgba(54, 209, 234, 0.08)' : 'transparent',
              }}
              onMouseEnter={e => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.03)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }
              }}
              onMouseLeave={e => {
                if (!isActive) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              {/* Active indicator */}
              <span
                className="flex-shrink-0 transition-all duration-150"
                style={{
                  width: '16px',
                  textAlign: 'center',
                  opacity: isActive ? 1 : 0,
                  transform: isActive ? 'translateX(0)' : 'translateX(-4px)',
                  color: 'var(--starship-cyan)',
                  fontSize: '12px',
                }}
              >
                ▸
              </span>

              {/* Icon */}
              <span
                className="transition-all duration-150"
                style={{
                  fontSize: '16px',
                  opacity: isActive ? 1 : 0.6,
                }}
              >
                {section.icon}
              </span>

              {/* Label */}
              <span className="text-sm font-mono transition-all duration-150">
                {section.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Footer metadata */}
      <div
        className="px-4 py-3 text-xs border-t"
        style={{
          borderColor: 'var(--terminal-border)',
          color: 'var(--text-muted)',
        }}
      >
        <div className="flex items-center gap-1.5">
          <span style={{ color: 'var(--starship-purple)' }}>⬡</span>
          <span>terminal-portfolio v1</span>
        </div>
        <div className="flex items-center gap-1.5 mt-1">
          <span style={{ color: 'var(--starship-green)' }}>●</span>
          <span>{sections.length} sections</span>
        </div>
      </div>
    </nav>
  );
}
