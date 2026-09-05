'use client';

import React, { useEffect } from 'react';

interface TuiSearchProps {
  /** Ref owned by TuiMenu — the input is focused/returned from here (REQ-X3). */
  inputRef: React.RefObject<HTMLInputElement | null>;
  query: string;
  onQueryChange: (query: string) => void;
  onClose: () => void;
  /** Total matches across the global corpus (REQ-C1). */
  resultCount: number;
}

export default function TuiSearch({ inputRef, query, onQueryChange, onClose, resultCount }: TuiSearchProps) {
  useEffect(() => {
    inputRef.current?.focus();
  }, [inputRef]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  return (
    <div
      className="flex items-center gap-3 px-4 py-2.5 mb-4 rounded"
      style={{
        backgroundColor: 'var(--terminal-bg-secondary)',
        border: '1px solid var(--terminal-border)',
      }}
    >
      <span style={{ color: 'var(--starship-cyan)', fontSize: '14px' }}>🔍</span>

      <input
        ref={inputRef}
        type="text"
        value={query}
        onChange={e => onQueryChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Search all sections…"
        className="flex-1 bg-transparent text-sm font-mono outline-none"
        style={{
          color: 'var(--text-primary)',
          caretColor: 'var(--starship-green)',
        }}
        autoComplete="off"
        spellCheck={false}
      />

      {query && (
        <span className="text-xs whitespace-nowrap" style={{ color: 'var(--text-muted)' }}>
          {resultCount} result{resultCount !== 1 ? 's' : ''}
        </span>
      )}

      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
        <kbd style={{ color: 'var(--starship-green)' }}>Esc</kbd> close
      </span>
    </div>
  );
}
