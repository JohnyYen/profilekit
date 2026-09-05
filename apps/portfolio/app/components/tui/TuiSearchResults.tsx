'use client';

import React, { useEffect, useRef } from 'react';
import type { SearchGroup, SearchResult } from '../../lib/search';

interface TuiSearchResultsProps {
  groups: SearchGroup[];
  total: number;
  resultIndex: number;
  searchFocus: 'input' | 'results';
  query: string;
  onActivate: (result: SearchResult) => void;
}

/**
 * Grouped global-search results (REQ-C2). Group headers are non-focusable;
 * ↑/↓/j/k navigate a flat, wrap-around result list via `resultIndex` (owned by
 * TuiMenu). The parent wrapper (tabIndex={-1}) is the programmatic focus
 * target — this component is never tabbable (hard gate 2).
 */
export default function TuiSearchResults({
  groups,
  total,
  resultIndex,
  searchFocus,
  query,
  onActivate,
}: TuiSearchResultsProps) {
  const itemRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    if (searchFocus === 'results') {
      itemRefs.current[resultIndex]?.scrollIntoView({ block: 'nearest' });
    }
  }, [resultIndex, searchFocus]);

  if (total === 0) {
    return (
      <p className="font-mono text-sm" style={{ color: 'var(--text-muted)' }}>
        No matches for &quot;{query}&quot;
      </p>
    );
  }

  let flatIndex = 0;

  return (
    <div className="font-mono space-y-3">
      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
        {total} result{total !== 1 ? 's' : ''} across {groups.length} section{groups.length !== 1 ? 's' : ''}
      </p>

      {groups.map(group => (
        <div key={group.section} role="group" aria-label={group.label}>
          <h3
            className="text-xs font-semibold uppercase mb-1"
            style={{ color: 'var(--starship-yellow)' }}
          >
            -- {group.label}
          </h3>
          <div className="space-y-1">
            {group.items.map(item => {
              const index = flatIndex++;
              const isSelected = searchFocus === 'results' && index === resultIndex;
              return (
                <div
                  key={`${group.section}-${index}`}
                  ref={el => {
                    itemRefs.current[index] = el;
                  }}
                  role="option"
                  aria-selected={isSelected}
                  id={`tui-result-${index}`}
                  onClick={() => onActivate(item)}
                  className={`px-2 py-1 cursor-pointer text-sm ${isSelected ? 'tui-card-selected' : ''}`}
                  style={{
                    color: 'var(--text-primary)',
                    backgroundColor: isSelected ? 'rgba(54, 209, 234, 0.08)' : 'transparent',
                  }}
                >
                  <span style={{ color: 'var(--starship-cyan)' }}>{item.label}</span>
                  {item.subtitle && (
                    <span className="text-xs ml-2" style={{ color: 'var(--text-muted)' }}>
                      {item.subtitle}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
