'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import Output from './output';
import Input from './input';
import Prompt from './prompt';
import { parseCommand, executeCommand, getAvailableCommands } from '../../commands/index';
import WelcomeBanner from '../welcome-banner';
import { useGithubProjects } from '../../hooks/use-github-projects';
import aboutData from '../../data/about.json';
import skillsData from '../../data/skills.json';
import socialData from '../../data/social.json';
import TuiMenu from '../tui/TuiMenu';

interface OutputLine {
  type: 'stdout' | 'stderr' | 'stdin' | 'info' | 'success' | 'warning';
  content: string;
  timestamp: number;
}

interface TerminalProps {
  username?: string;
  hostname?: string;
  onReady?: () => void;
}

export default function Terminal({ 
  username = 'visitor', 
  hostname = 'portfolio',
  onReady 
}: TerminalProps) {
  const [outputLines, setOutputLines] = useState<OutputLine[]>([]);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [currentPath] = useState('~');
  const [isReady, setIsReady] = useState(false);
  const [currentCommand, setCurrentCommand] = useState('Terminal');
  const [isExecuting, setIsExecuting] = useState(false);
  const [showWelcome, setShowWelcome] = useState(true);
  const [mode, setMode] = useState<'terminal' | 'tui'>('terminal');
  const [renderedMode, setRenderedMode] = useState<'terminal' | 'tui'>('terminal');
  const [transitionPhase, setTransitionPhase] = useState<'idle' | 'fading'>('idle');
  const [activeSection, setActiveSection] = useState('about');
  const terminalRef = useRef<HTMLDivElement>(null);
  const transitionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Animate mode transitions
  useEffect(() => {
    if (mode === renderedMode) return;

    // Fade out current content
    setTransitionPhase('fading');

    transitionTimer.current = setTimeout(() => {
      // Swap content (starts at opacity-0 since still 'fading')
      setRenderedMode(mode);
      // Small tick to let the new content render at opacity-0, then fade in
      requestAnimationFrame(() => {
        setTransitionPhase('idle');
      });
    }, 150);

    return () => {
      if (transitionTimer.current) clearTimeout(transitionTimer.current);
    };
  }, [mode, renderedMode]);

  const { projects, loading, refresh } = useGithubProjects();

  // Load history from localStorage on mount
  useEffect(() => {
    const savedHistory = localStorage.getItem('terminalHistory');
    if (savedHistory) {
      try {
        const parsed = JSON.parse(savedHistory);
        if (Array.isArray(parsed)) {
          setCommandHistory(parsed);
          setHistoryIndex(parsed.length); // Point to end (ready for new command)
        }
      } catch (e) {
        console.warn('Failed to parse terminal history from localStorage', e);
      }
    }
  }, []);

  // Save history to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('terminalHistory', JSON.stringify(commandHistory));
  }, [commandHistory]);

  const availableCommands = getAvailableCommands();

  const addOutput = useCallback((type: OutputLine['type'], content: string) => {
    setOutputLines(prev => [
      ...prev,
      { type, content, timestamp: Date.now() }
    ]);
  }, []);

  const handleCommand = useCallback(async (command: string) => {
    // Dismiss welcome banner on any command
    setShowWelcome(false);

    // Show processing indicator
    setIsExecuting(true);

    try {
      const parsed = parseCommand(command);

      // Check for clear command
      if (parsed.command === 'clear' || parsed.command === 'cls' || parsed.command === 'reset') {
        setOutputLines([]);
        setCommandHistory(prev => [...prev, command]);
        setHistoryIndex(-1);
        setCurrentCommand('Terminal');
        return;
      }

      // Check for exit command
      if (parsed.command === 'exit' || parsed.command === 'quit' || parsed.command === 'q') {
        setOutputLines([]);
        setCommandHistory(prev => [...prev, command]);
        const result = executeCommand(parsed, undefined, { projects, loading, refresh });
        if (result.output) {
          result.output.forEach((line: string) => {
            addOutput(result.type || 'stdout', line);
          });
        }
        setCurrentCommand('Goodbye');
        return;
      }

      setCommandHistory(prev => [...prev, command]);
      setHistoryIndex(-1);

      const context = { projects, loading, refresh };
      const result = executeCommand(parsed, undefined, context);

      // Update window title with command
      setCurrentCommand(parsed.command === 'menu' ? 'Menu' : (parsed.command || 'Terminal'));

      // Handle clear flag from command result
      if (result.clearOutput) {
        setOutputLines([]);
      }

      // Emit output BEFORE the mode switch so the "Switching to TUI mode..."
      // line is visible, then survives in the scrollback buffer after Esc
      // (REQ-E3). exit/clear return earlier and are unaffected.
      if (result.output && result.output.length > 0) {
        result.output.forEach((line: string) => {
          addOutput(result.type || 'stdout', line);
        });
      }

      // Handle mode switch AFTER output (REQ-E2): apply setSection before
      // setMode so `menu <section>` opens the TUI at the requested section and
      // bare `menu` re-enters the last section (activeSection persists).
      if (result.setMode) {
        if (result.setSection) {
          setActiveSection(result.setSection);
        }
        setMode(result.setMode);
        return;
      }

      addOutput('stdout', '');
    } finally {
      // Hide processing indicator
      setIsExecuting(false);
    }
  }, [addOutput, projects, loading, refresh, mode]);

  const getHistoryUp = useCallback(() => {
    if (commandHistory.length === 0) return null;
    
    const newIndex = historyIndex < 0 
      ? commandHistory.length - 1 
      : Math.max(0, historyIndex - 1);
    
    setHistoryIndex(newIndex);
    return commandHistory[newIndex];
  }, [commandHistory, historyIndex]);

  const getHistoryDown = useCallback(() => {
    if (commandHistory.length === 0 || historyIndex < 0) return null;
    
    const newIndex = historyIndex + 1;
    
    if (newIndex >= commandHistory.length) {
      setHistoryIndex(-1);
      return '';
    }
    
    setHistoryIndex(newIndex);
    return commandHistory[newIndex];
  }, [commandHistory, historyIndex]);

  // Update document title
  useEffect(() => {
    document.title = `${currentCommand} | Terminal Portfolio`;
  }, [currentCommand]);

  // Initialize terminal ready state
  useEffect(() => {
    if (!isReady) {
      setIsReady(true);
      onReady?.();
    }
  }, [isReady, onReady]);

  // Auto-scroll
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [outputLines]);

  const handleTerminalClick = () => {
    if (renderedMode === 'tui') return;
    const input = document.querySelector('input[aria-label="Terminal input"]') as HTMLInputElement;
    input?.focus();
  };

  return (
    <div 
      className="h-screen w-full bg-[var(--terminal-bg)] flex flex-col"
      onClick={handleTerminalClick}
    >
      {/* Terminal Window - macOS style */}
      <div className="terminal-window flex-1">
        {/* Terminal Header - macOS style */}
        <div className="terminal-header">
          {/* Traffic lights */}
          <div className="flex items-center gap-2.5">
            <button 
              className="traffic-light close" 
              aria-label="Close"
              onClick={(e) => e.preventDefault()}
            />
            <button 
              className="traffic-light minimize" 
              aria-label="Minimize"
              onClick={(e) => e.preventDefault()}
            />
            <button 
              className="traffic-light maximize" 
              aria-label="Maximize"
              onClick={(e) => e.preventDefault()}
            />
          </div>
          
          {/* Terminal title */}
          <div className="terminal-title">
            <span style={{ color: 'var(--starship-cyan)' }}>⌘</span>
            {mode === 'tui' ? (
              <span>Menu</span>
            ) : (
              <span>{username}@{hostname}: {currentPath}</span>
            )}
            {isExecuting && (
              <span className="ml-2 animate-spin text-[var(--starship-green)] text-xs">
                ●
              </span>
            )}
          </div>
          
          {/* Spacer for centering */}
          <div className="w-14" />
        </div>
        
        {/* Terminal Content */}
        <div 
          ref={terminalRef}
          className="flex-1 overflow-y-auto p-0"
        >
          <div
            className={`p-4 transition-all duration-200 ease-in-out will-change-transform ${
              renderedMode === 'tui' ? 'h-full' : ''
            } ${
              transitionPhase === 'fading'
                ? 'opacity-0 translate-y-2'
                : 'opacity-100 translate-y-0'
            }`}
          >
            {renderedMode === 'tui' ? (
              <TuiMenu
                projects={projects}
                loading={loading}
                aboutData={aboutData}
                skillsData={skillsData}
                socialData={socialData}
                activeSection={activeSection}
                onSectionChange={setActiveSection}
                onExit={() => setMode('terminal')}
              />
            ) : (
              <>
                {/* Welcome banner */}
                {showWelcome && isReady && (
                  <div className="mb-4">
                    <WelcomeBanner
                      onCommand={handleCommand}
                      onDismiss={() => setShowWelcome(false)}
                    />
                  </div>
                )}

                <Output lines={outputLines} typingSpeed={2} />
                
                {/* Input area */}
                {isReady && (
                  <div className="terminal-input-container mt-1">
                    <Input
                      onSubmit={handleCommand}
                      onFirstInput={() => setShowWelcome(false)}
                      commands={availableCommands}
                      commandHistory={commandHistory}
                      onHistoryUp={getHistoryUp}
                      onHistoryDown={getHistoryDown}
                      promptComponent={
                        <Prompt 
                          username={username}
                          hostname={hostname}
                          currentPath={currentPath}
                        />
                      }
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}