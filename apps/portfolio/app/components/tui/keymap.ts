/**
 * Shared TUI keyboard map + section registry (plain TS — no React).
 *
 * Single source of truth for the three documentation surfaces — TuiShortcuts,
 * TuiStatusBar and the terminal `shortcuts`/`help` commands (REQ-X4) — so key
 * strings never drift. The TUI bindings below encode exploration §6 verbatim,
 * with the search-annotation refinement and the Terminal group (the terminal
 * session bindings, not part of §6, but shared here so `help`/`shortcuts` never
 * duplicate them — REQ-X4).
 */

export interface Section {
  id: string;
  label: string;
  /** Glyph rendered in the desktop sidebar (mobile renders labels only). */
  icon: string;
}

export interface KeyBinding {
  id: string;
  keys: string;
  context: string;
  description: string;
  /** Display group used by the shortcuts overlay / `shortcuts` command. */
  group: string;
  /** Short label shown in the desktop status bar when present (REQ-D3). */
  statusHint?: string;
}

export interface KeymapGroup {
  title: string;
  items: KeyBinding[];
}

/** The six TUI sections, in navigation order. */
export const SECTIONS: Section[] = [
  { id: 'about', label: 'About', icon: '👤' },
  { id: 'projects', label: 'Projects', icon: '📦' },
  { id: 'skills', label: 'Skills', icon: '🛠' },
  { id: 'social', label: 'Social', icon: '🌐' },
  { id: 'contact', label: 'Contact', icon: '📧' },
  { id: 'cv', label: 'CV', icon: '📄' },
];

export const SECTION_IDS: string[] = SECTIONS.map(s => s.id);

export const KEYMAP: KeyBinding[] = [
  // Terminal session (shared by help/shortcuts commands so nothing drifts — REQ-X4)
  {
    id: 'term-history',
    group: 'Terminal',
    keys: '↑ / ↓',
    context: 'terminal',
    description: 'Command history',
  },
  {
    id: 'term-autocomplete',
    group: 'Terminal',
    keys: 'Tab',
    context: 'terminal',
    description: 'Autocomplete command',
  },
  {
    id: 'term-cancel',
    group: 'Terminal',
    keys: 'Ctrl+C',
    context: 'terminal',
    description: 'Cancel current input',
  },
  {
    id: 'term-clear',
    group: 'Terminal',
    keys: 'Ctrl+L',
    context: 'terminal',
    description: 'Clear terminal',
  },

  // Sections pane
  {
    id: 'section-prev',
    group: 'Sections',
    keys: '↑ / ↓',
    context: 'sections pane',
    description: 'Previous / next section (wraps)',
    statusHint: '↑↓ Navigate',
  },
  {
    id: 'section-vim',
    group: 'Sections',
    keys: 'j / k',
    context: 'sections pane',
    description: 'Same as ↑ / ↓ (vim-style)',
  },
  {
    id: 'jump-section',
    group: 'Sections',
    keys: '1-6',
    context: 'any (not search/overlay)',
    description: 'Jump to section 1-6',
  },
  {
    id: 'enter-section',
    group: 'Sections',
    keys: 'Enter',
    context: 'sections pane',
    description: 'Activate (render) the highlighted section',
    statusHint: 'Enter Select',
  },

  // Pane switching
  {
    id: 'pane-switch-arrows',
    group: 'Panels',
    keys: '← / →',
    context: 'anywhere (not inside tablist)',
    description: 'Switch pane: sections ↔ content',
  },
  {
    id: 'pane-switch-tab',
    group: 'Panels',
    keys: 'Tab / Shift+Tab',
    context: 'anywhere',
    description: 'Switch pane (same as ← / →)',
  },

  // Content pane
  {
    id: 'content-project',
    group: 'Content',
    keys: 'Enter',
    context: 'content pane (Projects)',
    description: 'Open selected repo (window.open)',
  },
  {
    id: 'content-cv',
    group: 'Content',
    keys: 'Enter',
    context: 'content pane (CV)',
    description: 'Trigger CV download',
  },
  {
    id: 'content-links',
    group: 'Content',
    keys: 'Enter',
    context: 'content pane (Social/Contact)',
    description: 'Open first link (github/email)',
  },
  {
    id: 'content-nav',
    group: 'Content',
    keys: '↑ / ↓ / j / k',
    context: 'content pane (Projects)',
    description: 'Move between projects (wraps, scroll-into-view)',
  },
  {
    id: 'jump-first-last',
    group: 'Content',
    keys: 'g / G',
    context: 'list panes',
    description: 'Jump to first / last item',
  },

  // Search
  {
    id: 'search-open',
    group: 'Search',
    keys: '/',
    context: 'not search',
    description: 'Open global search',
  },
  {
    id: 'search-nav',
    group: 'Search',
    keys: '↑ / ↓',
    context: 'search active',
    description:
      'Move between results — ↑/↓ from input (palette); j/k only when results list focused (typable in input)',
  },
  {
    id: 'search-vim',
    group: 'Search',
    keys: 'j / k',
    context: 'results list focused',
    description: 'Move between results',
  },
  {
    id: 'search-select',
    group: 'Search',
    keys: 'Enter',
    context: 'search active',
    description: 'Select highlighted result',
  },
  {
    id: 'search-close',
    group: 'Search',
    keys: 'Esc',
    context: 'search active',
    description: 'Close search',
  },

  // General
  {
    id: 'shortcuts-open',
    group: 'General',
    keys: '?',
    context: 'not search/overlay',
    description: 'Open shortcuts overlay',
    statusHint: '? Shortcuts',
  },
  {
    id: 'tui-exit',
    group: 'General',
    keys: 'Esc',
    context: 'base',
    description: 'Exit TUI → terminal',
    statusHint: 'Esc Back',
  },

  // Mobile
  {
    id: 'tablist-arrows',
    group: 'Mobile',
    keys: '← / →',
    context: 'tablist (mobile keyboard)',
    description: 'Move tab focus (scoped, stopPropagation)',
  },
];

/** Derived groups (in first-appearance order) for the shortcuts overlay. */
export const KEYMAP_GROUPS: KeymapGroup[] = [...new Set(KEYMAP.map(k => k.group))].map(
  title => ({ title, items: KEYMAP.filter(k => k.group === title) })
);

/** Entries surfaced as desktop status-bar hints (REQ-D3, REQ-X4). */
export const HINT_IDS: string[] = ['section-prev', 'enter-section', 'shortcuts-open', 'tui-exit'];

export function hintForId(id: string): KeyBinding | undefined {
  return KEYMAP.find(k => k.id === id);
}

/**
 * Managed interactive regions. Enter is ALWAYS intercepted inside these and
 * activates the pane-highlighted item programmatically (hard gate 3) — never
 * the native control activation. Covers the sidebar buttons and project cards.
 */
export const MANAGED_REGION_SELECTOR = '[data-tui-sidebar], [data-tui-projects-list]';

/**
 * True when the event target is an interactive element the TUI does NOT manage
 * (e.g. the CV download button or social/contact links). Only such elements may
 * keep native activation — managed items (sidebar buttons, project cards)
 * never bypass the container handler (REQ-X2, hard gate 3).
 */
export function isUnmanagedInteractiveTarget(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  const interactive = target.closest('a[href], button, input, textarea, select');
  if (!interactive) return false;
  return !interactive.closest(MANAGED_REGION_SELECTOR);
}

/**
 * True when the key event originates inside the mobile tablist. The tablist
 * handles ←/→ scoped (stopPropagation); the container ignores these events
 * entirely so pane-switching never fights tab focus (REQ-A4).
 */
export function isInsideTablist(target: EventTarget | null): boolean {
  return target instanceof Element && target.closest('[role="tablist"]') !== null;
}
