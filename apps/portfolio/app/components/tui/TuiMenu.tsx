'use client';

import React, { useRef, useEffect, useCallback, useState, useMemo } from 'react';
import TuiSidebar from './TuiSidebar';
import TuiContent from './TuiContent';
import TuiStatusBar from './TuiStatusBar';
import TuiShortcuts from './TuiShortcuts';
import TuiMobileNav from './TuiMobileNav';
import type { Project } from '../../hooks/use-github-projects';
import { SECTIONS, isUnmanagedInteractiveTarget, isInsideTablist } from './keymap';
import { filterProjects } from '../../lib/projects-filter';
import { searchAll, type SearchResult } from '../../lib/search';
import { downloadCv } from '../../lib/download';

interface TuiMenuProps {
  projects: Project[];
  loading: boolean;
  aboutData: any;
  skillsData: any;
  socialData: any;
  activeSection: string;
  onSectionChange: (section: string) => void;
  onExit: () => void;
}

type Pane = 'sections' | 'content';
type SearchFocus = 'input' | 'results';

/** Sections where the content pane is meaningful (list or primary action). */
const CONTENT_PANE_SECTIONS = ['projects', 'cv', 'social', 'contact'];

export default function TuiMenu({
  projects,
  loading,
  aboutData,
  skillsData,
  socialData,
  activeSection,
  onSectionChange,
  onExit,
}: TuiMenuProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // Two-pane focus model (REQ-A1) + search state (D15) + transient E3 banner.
  const [pane, setPane] = useState<Pane>('sections');
  const [selectedIndex, setSelectedIndex] = useState(-1); // -1 = none (fix 1)
  const [resultIndex, setResultIndex] = useState(0);
  const [searchFocus, setSearchFocus] = useState<SearchFocus>('input');
  const [searchActive, setSearchActive] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showTransitionBanner, setShowTransitionBanner] = useState(true); // D14, ~900ms

  const currentIndex = Math.max(0, SECTIONS.findIndex(s => s.id === activeSection));
  const activeLabel = SECTIONS.find(s => s.id === activeSection)?.label || '';

  // Keyboard live on mount (existing behavior).
  useEffect(() => {
    containerRef.current?.focus();
  }, []);

  // Transient "Switching to TUI mode..." banner (REQ-E3 via D14).
  useEffect(() => {
    const timer = window.setTimeout(() => setShowTransitionBanner(false), 900);
    return () => window.clearTimeout(timer);
  }, []);

  // Filtered projects (REQ-B3) — drives selection clamping + primary actions.
  const filtered = useMemo(() => filterProjects(projects, searchQuery), [projects, searchQuery]);

  // Global search corpus (REQ-C1) — single computation shared by the rendered
  // results list and the keyboard flat navigation.
  const searchResults = useMemo(
    () =>
      searchAll(
        {
          projects: loading ? undefined : projects,
          about: aboutData,
          skills: skillsData,
          social: socialData,
        },
        searchQuery
      ),
    [projects, loading, aboutData, skillsData, socialData, searchQuery]
  );
  const flatResults = useMemo(() => searchResults.groups.flatMap(g => g.items), [searchResults]);

  // Clamp selection when the filtered list shrinks; clear on empty (REQ-B4).
  useEffect(() => {
    if (filtered.length === 0) {
      setSelectedIndex(-1);
    } else {
      setSelectedIndex(prev => Math.min(prev, filtered.length - 1));
    }
  }, [filtered.length]);

  // Clamp resultIndex when the search-result set shrinks on query change
  // (mirrors the selectedIndex clamp above). Resets to -1 when empty so no
  // stale highlight lingers; Math.max(0, …) guarantees a valid first-selection
  // on the empty→non-empty transition. (REQ-C2/C4 reviewer fix.)
  useEffect(() => {
    if (flatResults.length === 0) {
      setResultIndex(-1);
    } else {
      setResultIndex(prev => Math.min(Math.max(0, prev), flatResults.length - 1));
    }
  }, [flatResults.length]);

  const restoreFocus = useCallback(() => {
    containerRef.current?.focus();
  }, []);

  // Esc close — clears the query, resets sub-focus, restores container focus (X3, X5, D6').
  const closeSearch = useCallback(() => {
    setSearchActive(false);
    setSearchQuery('');
    setSearchFocus('input');
    setResultIndex(0);
    restoreFocus();
  }, [restoreFocus]);

  // Fresh `/` always starts with an empty query (hard gate 1).
  const openSearch = useCallback(() => {
    setSearchActive(true);
    setSearchQuery('');
    setSearchFocus('input');
    setResultIndex(0);
  }, []);

  const closeShortcuts = useCallback(() => {
    setShowShortcuts(false);
    restoreFocus();
  }, [restoreFocus]);

  /**
   * Single funnel for every section change (sidebar click, tab tap, Enter,
   * 1-6, ↑/↓). Resets pane/selection; clears the query per the hard gate-1
   * rule: closing search clears it, and navigating to any NON-projects
   * section clears a query retained from a project-result jump.
   */
  const changeSection = useCallback(
    (next: string) => {
      setPane('sections');
      setSelectedIndex(-1);
      setSearchFocus('input');
      setResultIndex(0);
      if (searchActive) {
        setSearchActive(false);
        setSearchQuery('');
        restoreFocus();
      } else if (next !== 'projects') {
        setSearchQuery('');
      }
      onSectionChange(next);
    },
    [searchActive, onSectionChange, restoreFocus]
  );

  const jumpSection = useCallback(
    (index: number) => {
      const section = SECTIONS[index];
      if (section) changeSection(section.id);
    },
    [changeSection]
  );

  // Auto-select the first card when entering the content pane (D12).
  const autoSelectFirst = useCallback(() => {
    if (activeSection === 'projects' && filtered.length > 0) {
      setSelectedIndex(0);
    }
  }, [activeSection, filtered.length]);

  const moveSelected = useCallback(
    (direction: 1 | -1) => {
      if (filtered.length === 0) return;
      setSelectedIndex(prev => {
        if (prev < 0) return direction === 1 ? 0 : filtered.length - 1;
        return (prev + direction + filtered.length) % filtered.length;
      });
    },
    [filtered.length]
  );

  const moveResult = useCallback(
    (direction: 1 | -1) => {
      if (flatResults.length === 0) return;
      setResultIndex(prev => (prev + direction + flatResults.length) % flatResults.length);
    },
    [flatResults.length]
  );

  // REQ-C3: project results keep the query as a Projects filter; all others clear it.
  const activateSearchResult = useCallback(
    (result?: SearchResult) => {
      const target = result ?? flatResults[resultIndex];
      if (!target) return;
      setPane('sections');
      setSelectedIndex(-1);
      setSearchFocus('input');
      setResultIndex(0);
      if (target.section === 'projects') {
        setSearchActive(false);
        // KEEP searchQuery — it applies as the Projects filter (REQ-C3, gate 1).
        onSectionChange('projects');
      } else {
        setSearchActive(false);
        setSearchQuery('');
        onSectionChange(target.section);
      }
      restoreFocus();
    },
    [flatResults, resultIndex, onSectionChange, restoreFocus]
  );

  // REQ-A6 content-pane primary actions — always programmatic (fix 3, gate 3).
  const primaryActions = useMemo<Record<string, () => void>>(
    () => ({
      projects: () => {
        const project = filtered[selectedIndex];
        if (!project) return;
        window.open(project.url, '_blank', 'noopener');
      },
      cv: () => {
        if (socialData?.cvUrl) void downloadCv(socialData.cvUrl);
      },
      social: () => {
        if (socialData?.github) window.open(socialData.github, '_blank', 'noopener');
      },
      contact: () => {
        if (socialData?.email) window.location.href = `mailto:${socialData.email}`;
      },
      about: () => {},
      skills: () => {},
    }),
    [filtered, selectedIndex, socialData]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Overlay owns the keyboard (X5).
      if (showShortcuts) return;
      // Mobile tablist handles ←/→ scoped (A4).
      if (isInsideTablist(e.target)) return;

      // Search owns the keyboard — searchActive-first guard (X1, S8).
      if (searchActive) {
        switch (e.key) {
          case 'ArrowDown':
          case 'ArrowUp': {
            e.preventDefault();
            moveResult(e.key === 'ArrowDown' ? 1 : -1);
            // Palette UX: first ↑/↓ from the input moves focus into results (D15, gate 2).
            if (searchFocus === 'input' && flatResults.length > 0) {
              setSearchFocus('results');
              resultsRef.current?.focus();
            }
            break;
          }
          case 'j':
          case 'k':
            // j/k navigate only when the results list is focused — typable in the input (fix 4).
            if (searchFocus === 'results') {
              e.preventDefault();
              moveResult(e.key === 'j' ? 1 : -1);
            }
            break;
          case 'Enter':
            e.preventDefault();
            activateSearchResult();
            break;
          case 'Escape':
            e.preventDefault();
            closeSearch();
            break;
          case 'Tab':
            if (e.shiftKey && searchFocus === 'results') {
              // Leave results back into the input (gate 2).
              e.preventDefault();
              setSearchFocus('input');
              searchInputRef.current?.focus();
            }
            // Plain Tab / Shift+Tab from input: fall through natively (gate 2 — no toggle).
            break;
          default:
            break; // letters/digits/space type in the input
        }
        return;
      }

      // Base TUI keys (not search/overlay).
      switch (e.key) {
        case 'ArrowDown':
        case 'j':
          e.preventDefault();
          if (pane === 'content') moveSelected(1);
          else jumpSection((currentIndex + 1) % SECTIONS.length);
          break;
        case 'ArrowUp':
        case 'k':
          e.preventDefault();
          if (pane === 'content') moveSelected(-1);
          else jumpSection((currentIndex - 1 + SECTIONS.length) % SECTIONS.length);
          break;
        case 'ArrowLeft':
          e.preventDefault();
          setPane('sections');
          setSelectedIndex(-1); // drop stale content-pane card highlight (reviewer fix)
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (CONTENT_PANE_SECTIONS.includes(activeSection)) {
            setPane('content');
            autoSelectFirst();
          }
          break;
        case 'Tab':
          // REQ-A4: Tab → content, Shift+Tab → sections (same as ←/→).
          e.preventDefault();
          if (e.shiftKey) {
            setPane('sections');
            setSelectedIndex(-1); // mirror ← — drop stale card highlight (reviewer fix)
          } else if (CONTENT_PANE_SECTIONS.includes(activeSection)) {
            setPane('content');
            autoSelectFirst();
          }
          break;
        case 'Enter': {
          // Hard gate 3: always intercept for managed items — the pane-highlighted
          // item activates programmatically. Only truly unmanaged interactive
          // elements (e.g. CV download button, social links) keep native activation.
          if (isUnmanagedInteractiveTarget(e.target)) return;
          e.preventDefault();
          if (pane === 'content') {
            // Fix-1 guard: Enter with no/empty selection is a silent no-op (REQ-B4).
            if (activeSection === 'projects' && (selectedIndex < 0 || filtered.length === 0)) return;
            primaryActions[activeSection]?.();
          } else {
            // REQ-A2: Enter in the sections pane activates the highlighted section.
            jumpSection(currentIndex);
          }
          break;
        }
        case 'Escape':
          e.preventDefault();
          onExit();
          break;
        case '/':
          e.preventDefault();
          openSearch();
          break;
        case '?':
          e.preventDefault();
          setShowShortcuts(true);
          break;
        case 'g':
        case 'G': {
          // Hard gate 4: only meaningful in the Projects list; elsewhere (sections
          // pane, non-list content, search input) it falls through — no preventDefault.
          const inProjectsList =
            pane === 'content' && activeSection === 'projects' && filtered.length > 0;
          if (!inProjectsList) return;
          e.preventDefault();
          setSelectedIndex(e.key === 'g' ? 0 : filtered.length - 1);
          break;
        }
        default: {
          // REQ-A3: digits stay reserved for section jumps — filters never use numbers.
          if (e.key >= '1' && e.key <= '6') {
            e.preventDefault();
            jumpSection(Number(e.key) - 1);
          }
          break;
        }
      }
    },
    [
      showShortcuts,
      searchActive,
      searchFocus,
      flatResults.length,
      moveResult,
      activateSearchResult,
      closeSearch,
      pane,
      currentIndex,
      jumpSection,
      moveSelected,
      activeSection,
      autoSelectFirst,
      filtered.length,
      selectedIndex,
      primaryActions,
      onExit,
      openSearch,
    ]
  );

  return (
    <div
      ref={containerRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      className="tui-focus flex flex-row h-full relative"
      style={{ minHeight: '300px' }}
      aria-label="Terminal menu"
    >
      <TuiSidebar sections={SECTIONS} activeSection={activeSection} onSectionChange={changeSection} />

      <div className="flex flex-col flex-1 min-w-0">
        <TuiMobileNav sections={SECTIONS} activeSection={activeSection} onSectionChange={changeSection} />

        {showTransitionBanner && (
          <div className="tui-banner" role="status">
            Switching to TUI mode...
          </div>
        )}

        <TuiContent
          activeSection={activeSection}
          projects={projects}
          loading={loading}
          aboutData={aboutData}
          skillsData={skillsData}
          socialData={socialData}
          searchActive={searchActive}
          searchQuery={searchQuery}
          selectedIndex={selectedIndex}
          searchGroups={searchResults.groups}
          searchTotal={searchResults.total}
          resultIndex={resultIndex}
          searchFocus={searchFocus}
          searchInputRef={searchInputRef}
          resultsRef={resultsRef}
          onSearchQueryChange={setSearchQuery}
          onSearchClose={closeSearch}
          onActivateResult={activateSearchResult}
        />

        <TuiStatusBar
          activeSection={activeLabel}
          currentIndex={currentIndex + 1}
          totalSections={SECTIONS.length}
          hasSearch={searchActive}
        />
      </div>

      {showShortcuts && <TuiShortcuts onClose={closeShortcuts} />}
    </div>
  );
}
