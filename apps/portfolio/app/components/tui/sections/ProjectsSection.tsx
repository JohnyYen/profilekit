'use client';

import React, { useEffect, useRef } from 'react';
import type { Project } from '../../../hooks/use-github-projects';
import { filterProjects } from '../../../lib/projects-filter';

interface ProjectsSectionProps {
  projects: Project[];
  loading: boolean;
  searchQuery?: string;
  /** Content-pane selection index, -1 = none (driven by TuiMenu). */
  selectedIndex: number;
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const updated = new Date(dateStr).getTime();
  const diffMs = now - updated;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 30) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 12) return `${diffMonths}mo ago`;
  return `${Math.floor(diffMonths / 12)}y ago`;
}

const LANG_COLORS: Record<string, string> = {
  TypeScript: '#3178c6',
  JavaScript: '#f7df1e',
  Python: '#3572a5',
  Go: '#00add8',
  Rust: '#dea584',
  Shell: '#89e051',
  HTML: '#e34c26',
  CSS: '#563d7c',
};

function langColor(lang: string | null): string {
  if (!lang) return 'var(--text-muted)';
  return LANG_COLORS[lang] || 'var(--text-muted)';
}

/**
 * Projects listing (Area B). Renders the shared tokenized filter (REQ-B3),
 * exposes the content-pane list semantics (role=list/listitem, aria-current),
 * keeps anchor activation out of the container Enter path via tabIndex={-1}
 * (hard gate 3) and scrolls the selected card into view (REQ-B1).
 */
export default function ProjectsSection({
  projects,
  loading,
  searchQuery = '',
  selectedIndex,
}: ProjectsSectionProps) {
  const itemRefs = useRef<(HTMLDivElement | null)[]>([])
  const filtered = filterProjects(projects, searchQuery);

  // Scroll the highlighted card into view when selection changes (REQ-B1).
  useEffect(() => {
    if (selectedIndex >= 0 && selectedIndex < filtered.length) {
      itemRefs.current[selectedIndex]?.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex, filtered]);

  return (
    <div className="font-mono space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--starship-cyan)' }}>
          Projects
          {searchQuery && (
            <span className="ml-2 text-sm font-normal" style={{ color: 'var(--text-muted)' }}>
              · filtered ({filtered.length})
            </span>
          )}
        </h2>
        <div className="h-px my-3" style={{ backgroundColor: 'var(--terminal-border)' }} />
      </div>

      {loading && (
        <p style={{ color: 'var(--starship-cyan)' }}>⏳ Fetching projects from GitHub...</p>
      )}

      {!loading && filtered.length === 0 && (
        <p style={{ color: 'var(--text-muted)' }}>
          {searchQuery
            ? `No projects matching "${searchQuery}"`
            : 'No projects found. Tag repos with "showcase" on GitHub to see them here.'}
        </p>
      )}

      {!loading && filtered.length > 0 && (
        <div
          role="list"
          data-tui-projects-list
          className="grid gap-4"
          aria-label="Projects"
        >
          {filtered.map((project, i) => {
            const isSelected = i === selectedIndex;
            return (
              <div
                key={project.url}
                ref={el => {
                  itemRefs.current[i] = el;
                }}
                role="listitem"
                aria-current={isSelected ? 'true' : undefined}
                className={`tui-card tui-card-accent p-4 ${isSelected ? 'tui-card-selected' : ''}`}
                style={{ borderLeftColor: 'var(--starship-cyan)' }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span style={{ fontSize: '16px' }}>📦</span>
                  <a
                    href={project.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    tabIndex={-1}
                    className="font-semibold hover:underline"
                    style={{ color: 'var(--starship-cyan)' }}
                  >
                    {project.name}
                  </a>
                </div>
                <p className="text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>
                  {project.description || 'No description'}
                </p>
                <div className="flex items-center gap-4 text-xs">
                  {project.language && (
                    <span className="flex items-center gap-1" style={{ color: 'var(--text-primary)' }}>
                      <span
                        className="inline-block w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: langColor(project.language) }}
                      />
                      {project.language}
                    </span>
                  )}
                  <span style={{ color: 'var(--starship-yellow)' }}>⭐ {project.stars}</span>
                  <span style={{ color: 'var(--text-secondary)' }}>🍴 {project.forks}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Updated {timeAgo(project.updatedAt)}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
