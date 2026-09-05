'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';

interface InputProps {
  onSubmit: (command: string) => void;
  commands: string[];
  commandHistory: string[];
  onHistoryUp: () => string | null;
  onHistoryDown: () => string | null;
  onFirstInput?: () => void;
  disabled?: boolean;
  promptComponent?: React.ReactNode;
}

export default function Input({ 
  onSubmit, 
  commands, 
  commandHistory,
  onHistoryUp,
  onHistoryDown,
  onFirstInput,
  disabled = false,
  promptComponent
}: InputProps) {
  const [inputValue, setInputValue] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [selectedSuggestion, setSelectedSuggestion] = useState(0);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const cursorRef = useRef<HTMLSpanElement>(null);
  const firstInputFired = useRef(false);

  useEffect(() => {
    if (inputValue.trim()) {
      const filtered = commands.filter(cmd => 
        cmd.toLowerCase().startsWith(inputValue.toLowerCase())
      ).slice(0, 5);
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
      setSelectedSuggestion(0);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [inputValue, commands]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const getCursorPosition = useCallback(() => {
    const charWidth = 8.4;
    return inputValue.length * charWidth;
  }, [inputValue]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return;

    // Ctrl+C - Interrupt/Cancel
    if (e.key === 'c' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      setInputValue('');
      return;
    }

    // Ctrl+L - Clear terminal (handled by parent)
    if (e.key === 'l' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      onSubmit('clear');
      return;
    }

    switch (e.key) {
      case 'Tab':
        e.preventDefault();
        if (suggestions.length > 0) {
          setInputValue(suggestions[selectedSuggestion]);
          setShowSuggestions(false);
        }
        break;

      case 'Enter':
        e.preventDefault();
        if (inputValue.trim()) {
          onSubmit(inputValue.trim());
          setInputValue('');
          setShowSuggestions(false);
        }
        break;

      case 'ArrowUp':
        e.preventDefault();
        if (showSuggestions) {
          setSelectedSuggestion(prev => 
            prev > 0 ? prev - 1 : suggestions.length - 1
          );
        } else {
          const prevCommand = onHistoryUp();
          if (prevCommand !== null) {
            setInputValue(prevCommand);
          }
        }
        break;

      case 'ArrowDown':
        e.preventDefault();
        if (showSuggestions) {
          setSelectedSuggestion(prev => 
            prev < suggestions.length - 1 ? prev + 1 : 0
          );
        } else {
          const nextCommand = onHistoryDown();
          if (nextCommand !== null) {
            setInputValue(nextCommand);
          }
        }
        break;

      case 'Escape':
        setShowSuggestions(false);
        break;
    }
  }, [disabled, suggestions, selectedSuggestion, inputValue, onSubmit, onHistoryUp, onHistoryDown, showSuggestions]);

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  return (
    <div className="relative">
      <div className="flex items-center">
        {/* Prompt */}
        {promptComponent}
        
        {/* Input */}
        <div className="flex-1 relative flex items-center">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={(e) => {
              if (!firstInputFired.current && e.target.value) {
                firstInputFired.current = true;
                onFirstInput?.();
              }
              setInputValue(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className="w-full bg-transparent text-[var(--text-primary)] caret-transparent focus:outline-none py-1 font-mono"
            placeholder=""
            aria-label="Terminal input"
            autoComplete="off"
            autoCapitalize="off"
            spellCheck="false"
          />
          
          {/* Custom cursor */}
          <span 
            ref={cursorRef}
            className="absolute top-1/2 -translate-y-1/2 inline-block w-[8px] h-[18px] bg-[var(--starship-green)] cursor-blink pointer-events-none"
            style={{ 
              left: `${getCursorPosition()}px`,
            }}
            aria-hidden="true"
          />
        </div>
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div 
          className="absolute left-0 top-full mt-2 z-10 min-w-[200px]"
          style={{
            backgroundColor: 'var(--terminal-bg)',
            border: '1px solid var(--text-muted)',
            borderRadius: '4px',
          }}
        >
          <div 
            className="px-3 py-1.5 text-xs"
            style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--text-muted)' }}
          >
            Suggestions
          </div>
          {suggestions.map((suggestion, index) => (
            <div
              key={suggestion}
              className={`px-3 py-1.5 cursor-pointer flex items-center gap-2 ${
                index === selectedSuggestion 
                  ? 'text-[var(--text-primary)]' 
                  : 'text-[var(--text-secondary)]'
              }`}
              style={{
                backgroundColor: index === selectedSuggestion ? 'rgba(54, 209, 234, 0.15)' : 'transparent',
              }}
              onClick={() => handleSuggestionClick(suggestion)}
            >
              <span style={{ color: 'var(--starship-cyan)' }}>›</span>
              <span>{suggestion}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}