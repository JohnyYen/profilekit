'use client';

import React, { useRef } from 'react';
import type { Section } from './keymap';

interface TuiMobileNavProps {
  sections: Section[];
  activeSection: string;
  onSectionChange: (id: string) => void;
}

/**
 * Touch-only section navigation for viewports below `sm` (REQ-D1/D2). The tab
 * bar is a sibling rendered above the content scroller, so it stays visible
 * while content scrolls. Tapping a tab switches the section, resets the pane
 * and closes search (handled by the changeSection funnel in TuiMenu).
 *
 * The tablist owns ←/→ for hardware-keyboard users: the keys are scoped with
 * stopPropagation so the container's pane-switch ←/→ never fights them (REQ-A4).
 */
export default function TuiMobileNav({ sections, activeSection, onSectionChange }: TuiMobileNavProps) {
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const moveTabFocus = (index: number, direction: 1 | -1) => {
    const next = (index + direction + sections.length) % sections.length;
    tabRefs.current[next]?.focus();
  };

  return (
    <div
      role="tablist"
      aria-label="Sections"
      className="flex sm:hidden overflow-x-auto flex-shrink-0 border-b"
      style={{
        backgroundColor: 'var(--terminal-bg-secondary)',
        borderColor: 'var(--terminal-border)',
      }}
    >
      {sections.map((section, index) => {
        const isActive = section.id === activeSection;
        return (
          <button
            key={section.id}
            ref={el => {
              tabRefs.current[index] = el;
            }}
            role="tab"
            id={`tui-tab-${section.id}`}
            aria-selected={isActive}
            aria-current={isActive ? 'true' : undefined}
            aria-controls="tui-content"
            className={`tui-tab ${isActive ? 'active' : ''}`}
            onClick={() => onSectionChange(section.id)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                e.preventDefault();
                e.stopPropagation();
                moveTabFocus(index, e.key === 'ArrowRight' ? 1 : -1);
              }
            }}
          >
            {section.label}
          </button>
        );
      })}
    </div>
  );
}
