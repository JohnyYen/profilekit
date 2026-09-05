export default function Loading() {
  return (
    <div
      className="h-screen w-screen flex flex-col items-center justify-center"
      style={{
        backgroundColor: 'var(--terminal-bg)',
        fontFamily: 'var(--font-mono)',
      }}
    >
      <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--starship-cyan)' }}>
        <span className="flex gap-0.5">
          <span className="terminal-dot">⠋</span>
          <span className="terminal-dot">⠙</span>
          <span className="terminal-dot">⠹</span>
        </span>
        <span style={{ color: 'var(--text-muted)' }}>Initializing terminal</span>
        <span
          className="inline-block w-[6px] h-[14px]"
          style={{
            backgroundColor: 'var(--starship-green)',
            animation: 'cursor-blink 1s step-end infinite',
          }}
        />
      </div>
    </div>
  );
}