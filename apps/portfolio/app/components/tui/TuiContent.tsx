'use client';

import React from 'react';
import type { Project } from '../../hooks/use-github-projects';
import type { SearchGroup, SearchResult } from '../../lib/search';
import AboutSection from './sections/AboutSection';
import ProjectsSection from './sections/ProjectsSection';
import SkillsSection from './sections/SkillsSection';
import SocialSection from './sections/SocialSection';
import ContactSection from './sections/ContactSection';
import CvSection from './sections/CvSection';
import TuiSearch from './TuiSearch';
import TuiSearchResults from './TuiSearchResults';

interface TuiContentProps {
  activeSection: string;
  projects: Project[];
  loading: boolean;
  aboutData: any;
  skillsData: any;
  socialData: any;
  searchActive: boolean;
  /** Raw query — passed through so a retained project filter still applies. */
  searchQuery: string;
  selectedIndex: number;
  searchGroups: SearchGroup[];
  searchTotal: number;
  resultIndex: number;
  searchFocus: 'input' | 'results';
  searchInputRef: React.RefObject<HTMLInputElement | null>;
  resultsRef: React.RefObject<HTMLDivElement | null>;
  onSearchQueryChange: (query: string) => void;
  onSearchClose: () => void;
  onActivateResult: (result: SearchResult) => void;
}

export default function TuiContent({
  activeSection,
  projects,
  loading,
  aboutData,
  skillsData,
  socialData,
  searchActive,
  searchQuery,
  selectedIndex,
  searchGroups,
  searchTotal,
  resultIndex,
  searchFocus,
  searchInputRef,
  resultsRef,
  onSearchQueryChange,
  onSearchClose,
  onActivateResult,
}: TuiContentProps) {
  return (
    <div
      id="tui-content"
      className="flex-1 overflow-y-auto px-4 py-6"
      style={{ backgroundColor: 'var(--terminal-bg)' }}
    >
      {/* Global search (REQ-C1): bar + grouped results replace section content (D7). */}
      {searchActive ? (
        <>
          <TuiSearch
            inputRef={searchInputRef}
            query={searchQuery}
            onQueryChange={onSearchQueryChange}
            onClose={onSearchClose}
            resultCount={searchTotal}
          />

          {/* Results wrapper: programmatic focus target only — NOT tabbable (gate 2). */}
          <div
            ref={resultsRef}
            tabIndex={-1}
            role="listbox"
            aria-label="Search results"
            aria-activedescendant={
              searchFocus === 'results' && resultIndex >= 0 ? `tui-result-${resultIndex}` : undefined
            }
            className="tui-focus"
          >
            <TuiSearchResults
              groups={searchGroups}
              total={searchTotal}
              resultIndex={resultIndex}
              searchFocus={searchFocus}
              query={searchQuery}
              onActivate={onActivateResult}
            />
          </div>
        </>
      ) : (
        <div key={activeSection} className="tui-section-fade-in">
          {activeSection === 'about' && <AboutSection data={aboutData} />}
          {activeSection === 'projects' && (
            <ProjectsSection
              projects={projects}
              loading={loading}
              searchQuery={searchQuery}
              selectedIndex={selectedIndex}
            />
          )}
          {activeSection === 'skills' && <SkillsSection data={skillsData} />}
          {activeSection === 'social' && <SocialSection data={socialData} />}
          {activeSection === 'contact' && <ContactSection data={socialData} />}
          {activeSection === 'cv' && <CvSection cvUrl={socialData.cvUrl} />}
        </div>
      )}
    </div>
  );
}
