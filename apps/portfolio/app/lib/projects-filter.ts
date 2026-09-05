import type { Project } from '../hooks/use-github-projects';

/**
 * Shared projects filter (REQ-B3) used by both ProjectsSection and the global
 * search corpus. Supports `lang:<language>` (case-insensitive equality) and
 * `topic:<topic>` (case-insensitive includes) tokens alongside free-text
 * name/language/description matching. Tokens are AND-combined; digits are
 * never treated as filters (1-6 stay reserved for section jumps).
 */

function parseTokens(query: string): string[] {
  return query.trim().toLowerCase().split(/\s+/).filter(Boolean);
}

function matchToken(project: Project, token: string): boolean {
  if (token.startsWith('lang:')) {
    const language = token.slice('lang:'.length);
    return (project.language ?? '').toLowerCase() === language;
  }
  if (token.startsWith('topic:')) {
    const topic = token.slice('topic:'.length);
    return project.topics.some(t => t.toLowerCase().includes(topic));
  }
  return (
    project.name.toLowerCase().includes(token) ||
    (project.language ?? '').toLowerCase().includes(token) ||
    (project.description ?? '').toLowerCase().includes(token)
  );
}

export function filterProjects(projects: Project[], query: string): Project[] {
  const tokens = parseTokens(query);
  if (tokens.length === 0) return projects;
  return projects.filter(project => tokens.every(token => matchToken(project, token)));
}
