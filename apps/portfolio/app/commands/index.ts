import { KEYMAP, KEYMAP_GROUPS, SECTIONS, SECTION_IDS } from '../components/tui/keymap';

export interface Project {
  name: string;
  description: string;
  language: string | null;
  stars: number;
  forks: number;
  updatedAt: string;
  url: string;
  topics: string[];
}

export interface CommandContext {
  projects?: Project[];
  loading?: boolean;
  refresh?: () => void;
}

export interface Command {
  name: string;
  description: string;
  usage?: string;
  aliases?: string[];
  handler: (args: string[], history?: string[], context?: CommandContext) => CommandResult;
}

export interface CommandResult {
  output: string[];
  type: 'stdout' | 'stderr' | 'info';
  clearOutput?: boolean;
  setMode?: 'terminal' | 'tui';
  /** Optional TUI section to activate on `menu <section>` (REQ-E1/E2). */
  setSection?: string;
}

export interface ParsedCommand {
  command: string;
  args: string[];
  flags: string[];
}

// Parse command string into command, args, and flags
export function parseCommand(input: string): ParsedCommand {
  const parts = input.trim().split(/\s+/);
  const command = parts[0]?.toLowerCase() || '';
  const args: string[] = [];
  const flags: string[] = [];

  for (let i = 1; i < parts.length; i++) {
    const part = parts[i];
    if (part.startsWith('--')) {
      flags.push(part.substring(2));
    } else if (part.startsWith('-')) {
      flags.push(part.substring(1));
    } else {
      args.push(part);
    }
  }

  return { command, args, flags };
}

// Dragon ASCII Art
const DRAGON_ASCII = `
        ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
        ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
        ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
        ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
        ██║ ╚████║███████╗██╔╝ ╚██╗╚██████╔╝███████║
        ╚═╝  ╚═══╝╚══════╝╚═╝   ╚═╝ ╚═════╝ ╚══════╝`;

// Import data from JSON
import projectsData from '../data/projects.json';
import aboutData from '../data/about.json';
import skillsData from '../data/skills.json';
import socialData from '../data/social.json';

// Command registry
const commands: Command[] = [
  {
    name: 'help',
    description: 'Show available commands',
    handler: () => {
      const terminalKeys = KEYMAP.filter(k => k.group === 'Terminal');
      return {
        output: [
          'Available commands:',
          '',
          '  help                - Show this help message',
          '  menu, gui, nav, browse [section] - Open TUI menu at a section',
          '  sections            - List TUI sections',
          '  about               - Learn about me',
          '  projects            - Browse my pinned projects',
          '  skills              - View my technical skills',
          '  fetch               - Show system info (fastfetch-style)',
          '  cv                  - Download my CV',
          '  social              - Social links',
          '  contact             - How to reach me',
          '  shortcuts, keys, bindings - Show keyboard shortcuts',
          '  clear, cls          - Clear the terminal',
          '  exit                - Exit the terminal',
          '  whoami              - Display current user',
          '  date                - Show current date/time',
          '  echo                - Print text',
          '',
          'Shortcuts:',
          ...terminalKeys.map(kb => `  ${kb.keys.padEnd(14)} - ${kb.description}`),
        ],
        type: 'stdout' as const
      };
    }
  },
  {
    name: 'menu',
    description: 'Open TUI menu',
    aliases: ['gui', 'nav', 'browse'],
    usage: 'menu [section]',
    handler: (args: string[]) => {
      const line = 'Switching to TUI mode...\n';
      if (args.length === 0) {
        return { output: [line], type: 'info' as const, setMode: 'tui' as const };
      }
      const section = args[0].toLowerCase();
      if (SECTION_IDS.includes(section)) {
        return {
          output: [line],
          type: 'info' as const,
          setMode: 'tui' as const,
          setSection: section,
        };
      }
      return {
        output: ['menu <about|projects|skills|social|contact|cv>'],
        type: 'stderr' as const,
      };
    },
  },
  {
    name: 'sections',
    description: 'List TUI sections',
    handler: () => ({
      output: [
        '═ TUI SECTIONS ──────────────────────────',
        '',
        ...SECTIONS.map((s, i) => `  ${i + 1}  ${s.id.padEnd(10)} ${s.label}`),
        '',
        'Use "menu <section>" to open the TUI at a specific section.',
      ].filter(Boolean),
      type: 'stdout' as const,
    }),
  },
  {
    name: 'shortcuts',
    description: 'Show keyboard shortcuts',
    aliases: ['keys', 'bindings'],
    handler: () => {
      const lines: string[] = ['═ KEYBOARD SHORTCUTS ────────────────────────────', ''];
      for (const group of KEYMAP_GROUPS) {
        lines.push(`  ${group.title}:`);
        for (const kb of group.items) {
          lines.push(`    ${kb.keys.padEnd(20)} ${kb.description}`);
        }
        lines.push('');
      }
      return { output: lines.filter(Boolean), type: 'stdout' as const };
    },
  },
  {
    name: 'about',
    description: 'Learn about me',
    handler: () => {
      const focusLines = aboutData.currentFocus.map(f => 
        `   • ${f.title} - ${f.description}`
      ).join('\n');
      
      const buildLines = aboutData.whatIBuild.map(item => 
        `   • ${item}`
      ).join('\n');

      return {
        output: [
          '═ ABOUT ──────────────────────────────────────────',
          '',
          `👋 Hi! I'm ${aboutData.username}`,
          '',
          `💼 ${aboutData.tagline}`,
          `   ${aboutData.description}`,
          '',
          '🎯 Current Focus:',
          focusLines,
          '',
          '🔧 What I build:',
          buildLines,
          '',
          '📚 Learning Journey:',
          `   ${aboutData.learningJourney}`,
          '',
          '→ Try "fetch" for a quick summary of me!',
        ],
        type: 'stdout' as const
      };
    }
  },
  {
    name: 'fetch',
    description: 'Show quick system info (fastfetch-style)',
    handler: () => {
      const backend = skillsData.backend.join(', ');
      const database = skillsData.database.join(', ');
      const devops = skillsData.devops.join(', ');
      const learning = skillsData.learning.map(l => l.category).join(', ');

      return {
        output: [
          DRAGON_ASCII,
          '',
          '╭───────────────────╮',
          '│   user@portfolio  │',
          '╰───────────────────╯',
          '',
          '  ┌─ Info',
          '  │  OS:      Terminal Portfolio v1.0',
          `  │  Host:    ${aboutData.username.split(' ')[0]}`,
          '  │  Kernel:  React + Next.js',
          '  │  Shell:   Custom Terminal',
          '  │',
          '  ├─ Tech Stack',
          `  │  Backend:  ${backend}`,
          `  │  Database: ${database}`,
          `  │  DevOps:   ${devops}`,
          '  │',
          '  ├─ Currently Learning',
          ...skillsData.learning.map(l => `  │  • ${l.category}`),
          '  │',
          '  └─ Location',
          '     🌎 Available remotely',
          '',
          'Type "about" for more details!',
        ],
        type: 'stdout' as const
      };
    },
    aliases: ['neofetch', 'sysinfo']
  },
  {
    name: 'projects',
    description: 'Browse my pinned projects',
    usage: 'projects [--all] [--refresh] [language]',
    handler: (args: string[], _history?: string[], context?: CommandContext) => {
      const cleanArgs = args.filter(a => !a.startsWith('--'));
      const flags = args.filter(a => a.startsWith('--'));
      const filter = cleanArgs[0]?.toLowerCase();

      // Handle --refresh flag
      if (flags.includes('refresh')) {
        if (context?.refresh) {
          context.refresh();
        }
        return {
          output: ['⏳ Refreshing projects from GitHub...'],
          type: 'stdout' as const,
        };
      }

      // Handle loading state
      if (context?.loading) {
        return {
          output: ['⏳ Fetching projects from GitHub...'],
          type: 'stdout' as const,
        };
      }

      // Helper: relative time display
      const relativeTime = (dateString: string): string => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Updated today';
        if (diffDays === 1) return 'Updated yesterday';
        if (diffDays < 30) return `Updated ${diffDays}d ago`;
        const diffMonths = Math.floor(diffDays / 30);
        if (diffMonths === 1) return 'Updated 1 month ago';
        if (diffMonths < 12) return `Updated ${diffMonths}mo ago`;
        const diffYears = Math.floor(diffMonths / 12);
        return `Updated ${diffYears}y ago`;
      };

      // Use live data if available and not empty
      if (context?.projects && context.projects.length > 0) {
        const projects = context.projects;

        let filtered = projects;
        if (filter) {
          filtered = projects.filter(
            (p) =>
              (p.language &&
                p.language.toLowerCase().includes(filter)) ||
              p.name.toLowerCase().includes(filter)
          );
        }

        const showAll = flags.includes('all');
        const display = showAll ? filtered : filtered.slice(0, 8);

        return {
          output: [
            '═ PROJECTS ──────────────────────────────────────────',
            '',
            ...display
              .map((p) =>
                [
                  `📦 ${p.name}`,
                  `   ${p.description || 'No description'}`,
                  `   └─ ${p.language || 'N/A'} ${'⭐ ' + p.stars} ${'🍴 ' + p.forks}`,
                  `   🔗 ${p.url}`,
                  `   📅 ${relativeTime(p.updatedAt)}`,
                  '',
                ].flat()
              )
              .flat(),
            filter && filtered.length === 0
              ? `No projects matching "${filter}"`
              : '',
            filter
              ? `Found ${filtered.length} project(s)`
              : '',
            !showAll && filtered.length > 8
              ? `Showing 8 of ${filtered.length} projects (use --all to see all)`
              : '',
          ].filter(Boolean),
          type: 'stdout' as const,
        };
      }

      // Live data loaded but empty — fall back to static data
      if (context?.projects && context.projects.length === 0 && !context.loading) {
        // Return static data with enhanced format
        const staticFiltered = filter
          ? projectsData.filter(
              (p: { tech: string; name: string }) =>
                p.tech.toLowerCase().includes(filter) ||
                p.name.toLowerCase().includes(filter)
            )
          : projectsData;

        return {
          output: [
            '═ PROJECTS ──────────────────────────────────────────',
            '',
            ...staticFiltered
              .map((p: { name: string; description: string; tech: string; url: string }) =>
                [
                  `📦 ${p.name}`,
                  `   ${p.description}`,
                  `   └─ ${p.tech}`,
                  `   🔗 ${p.url}`,
                  '',
                ].flat()
              )
              .flat(),
            filter && staticFiltered.length === 0
              ? `No projects matching "${filter}"`
              : '',
          ].filter(Boolean),
          type: 'stdout' as const,
        };
      }

      // No context at all — use static data (original behavior as fallback)
      const staticFiltered = filter
        ? projectsData.filter(
            (p: { tech: string; name: string }) =>
              p.tech.toLowerCase().includes(filter) ||
              p.name.toLowerCase().includes(filter)
          )
        : projectsData;

      return {
        output: [
          '═ PROJECTS ──────────────────────────────────────────',
          '',
          ...staticFiltered
            .map((p: { name: string; description: string; tech: string; url: string }) =>
              [
                `📦 ${p.name}`,
                `   ${p.description}`,
                `   └─ ${p.tech}`,
                `   🔗 ${p.url}`,
                '',
              ].flat()
            )
            .flat(),
          filter && staticFiltered.length === 0
            ? `No projects matching "${filter}"`
            : '',
          filter
            ? `Found ${staticFiltered.length} project(s)`
            : '',
        ].filter(Boolean),
        type: 'stdout' as const,
      };
    },
    aliases: ['work', 'repo']
  },
  {
    name: 'skills',
    description: 'View my technical skills',
    handler: () => {
      const learningLines = skillsData.learning.map(l => 
        `   • ${l.category} (${l.topics.join(', ')})`
      ).join('\n');

      return {
        output: [
          '═ SKILLS ──────────────────────────────────────────',
          '',
          `Backend:    ${skillsData.backend.join(' │ ')}`,
          `Database:   ${skillsData.database.join(' │ ')}`,
          `DevOps:     ${skillsData.devops.join(' │ ')}`,
          `Tools:      ${skillsData.tools.join(' │ ')}`,
          '',
          '📚 Currently Learning:',
          learningLines,
          '',
          '→ Check "fetch" for a quick overview!',
          '→ Check "projects" for my work!',
        ],
        type: 'stdout' as const
      };
    }
  },
  {
    name: 'cv',
    description: 'Download my CV',
    handler: () => ({
      output: [
        '═ CV/RESUME ────────────────────────────────────────',
        '',
        `📥 Download: ${socialData.cvUrl || '[CV not configured]'}`,
        '',
        'Last updated: 2026-07-30',
        '',
        'Contents:',
        '  • Professional Summary',
        '  • Work Experience',
        '  • Skills & Technologies',
        '  • Projects',
        '  • Education',
      ],
      type: 'stdout' as const
    }),
    aliases: ['resume']
  },
  {
    name: 'social',
    description: 'Social links',
    handler: () => ({
      output: [
        '═ SOCIAL ───────────────────────────────────────────',
        '',
        `🐙 GitHub:    ${socialData.github.replace('https://', '')}`,
        `💼 LinkedIn:  ${socialData.linkedin.replace('https://', '')}`,
        `📧 Email:     ${socialData.email}`,
        '',
      ],
      type: 'stdout' as const
    })
  },
  {
    name: 'contact',
    description: 'How to reach me',
    handler: () => ({
      output: [
        '═ CONTACT ──────────────────────────────────────────',
        '',
        '💬 Let\'s connect!',
        '',
        `📧 Email:    ${socialData.email}`,
        `💼 LinkedIn: ${socialData.linkedin.replace('https://', '')}`,
        `🐙 GitHub:   ${socialData.github.replace('https://', '')}`,
        '',
        'Open for:',
        '  • Backend development opportunities',
        '  • Software architecture discussions',
        '  • AI/ML collaboration',
        '  • Tech mentorship',
        '',
        'Response: Usually within 48h',
      ],
      type: 'stdout' as const
    }),
    aliases: ['email', 'reach']
  },
  {
    name: 'clear',
    description: 'Clear the terminal',
    handler: () => ({
      output: [],
      type: 'stdout' as const,
      clearOutput: true
    }),
    aliases: ['cls', 'reset']
  },
  {
    name: 'exit',
    description: 'Exit the terminal',
    handler: () => ({
      output: [
        'Goodbye! 👋',
        '',
        'Thanks for visiting my terminal portfolio.',
        'Feel free to come back anytime!',
      ],
      type: 'stdout' as const
    }),
    aliases: ['quit', 'q']
  },
  {
    name: 'history',
    description: 'Show command history',
    handler: (_args: string[], history?: string[]) => {
      if (!history || history.length === 0) {
        return {
          output: ['No commands in history.'],
          type: 'stdout' as const
        };
      }

      return {
        output: [
          'Command history:',
          '',
          ...history.map((cmd, i) => `  ${i + 1}  ${cmd}`)
        ],
        type: 'stdout' as const
      };
    }
  },
  {
    name: 'whoami',
    description: 'Display current user',
    handler: () => ({
      output: ['visitor'],
      type: 'stdout' as const
    })
  },
  {
    name: 'date',
    description: 'Show current date/time',
    handler: () => ({
      output: [new Date().toString()],
      type: 'stdout' as const
    })
  },
  {
    name: 'echo',
    description: 'Print text',
    handler: (args: string[]) => ({
      output: [args.join(' ') || ''],
      type: 'stdout' as const
    })
  }
];

// Get list of available command names
export function getAvailableCommands(): string[] {
  const names = commands.map(c => c.name);
  commands.forEach(c => {
    if (c.aliases) {
      names.push(...c.aliases);
    }
  });
  return [...new Set(names)];
}

// Execute a parsed command
export function executeCommand(parsed: ParsedCommand, history?: string[], context?: CommandContext): CommandResult {
  const { command, args } = parsed;

  if (!command) {
    return { output: [''], type: 'stdout' };
  }

  // Find command by name or alias
  const cmd = commands.find(c => 
    c.name === command || c.aliases?.includes(command)
  );

  if (!cmd) {
    // Improved command not found message with suggestions
    const available = getAvailableCommands();
    const similar = available.filter(c => 
      c.length > 2 && (c.startsWith(command[0]) || command.includes(c))
    ).slice(0, 3);
    
    return {
      output: [
        `╭─ Command not found ─────────────────────────────`,
        `│`,
        `│  ${command}: command not found`,
        `│`,
        `│  Did you mean?`,
        ...similar.map(s => `│    • ${s}`),
        `│`,
        `│  Type "help" to see all available commands.`,
        `╰──────────────────────────────────────────────`,
      ],
      type: 'stderr'
    };
  }

  // Execute command handler
  return cmd.handler(args, history, context);
}

// Get command suggestions for autocomplete
export function getCommandSuggestions(partial: string): string[] {
  const available = getAvailableCommands();
  return available.filter(cmd => 
    cmd.toLowerCase().startsWith(partial.toLowerCase())
  ).slice(0, 5);
}

// Export dragon ASCII for boot sequence
export const getDragonAscii = () => DRAGON_ASCII;