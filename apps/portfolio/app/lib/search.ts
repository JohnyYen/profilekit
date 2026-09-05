import type { Project } from '../hooks/use-github-projects';
import { filterProjects } from './projects-filter';

/**
 * Global TUI search corpus (REQ-C1). Groups matches by section across
 * projects, skills, about, social, contact and cv. Project results reuse the
 * shared token filter (REQ-B3) and are omitted while GitHub data is loading
 * (REQ-C4).
 */

export interface SearchResult {
  section: string;
  label: string;
  subtitle?: string;
  kind: 'project' | 'skill' | 'about' | 'social' | 'contact' | 'cv';
}

export interface SearchGroup {
  section: string;
  label: string;
  items: SearchResult[];
}

export interface SearchCorpus {
  /** Undefined while projects are loading — the group is omitted (REQ-C4). */
  projects?: Project[];
  skills: {
    backend: string[];
    database: string[];
    devops: string[];
    tools: string[];
    learning: { category: string; topics: string[] }[];
  };
  about: {
    username: string;
    tagline: string;
    description: string;
    currentFocus: { title: string; description: string }[];
    whatIBuild: string[];
    learningJourney: string;
  };
  social: {
    github: string;
    linkedin: string;
    email: string;
    cvUrl?: string;
  };
}

export interface SearchOutcome {
  groups: SearchGroup[];
  total: number;
}

function includes(text: string | undefined, query: string): boolean {
  return (text ?? '').toLowerCase().includes(query);
}

export function searchAll(corpus: SearchCorpus, rawQuery: string): SearchOutcome {
  const query = rawQuery.trim().toLowerCase();
  if (!query) return { groups: [], total: 0 };

  const groups: SearchGroup[] = [];
  let total = 0;

  const push = (section: string, label: string, items: SearchResult[]): void => {
    if (items.length === 0) return;
    groups.push({ section, label, items });
    total += items.length;
  };

  // Projects — via the shared token filter; omitted while loading (REQ-C4).
  if (corpus.projects) {
    push(
      'projects',
      'Projects',
      filterProjects(corpus.projects, rawQuery).map(project => ({
        section: 'projects',
        kind: 'project',
        label: project.name,
        subtitle: [project.language, project.description].filter(Boolean).join(' — '),
      }))
    );
  }

  // Skills — individual tech entries plus learning categories/topics.
  const skillEntries: { text: string; category: string }[] = [
    ...corpus.skills.backend.map(text => ({ text, category: 'Backend' })),
    ...corpus.skills.database.map(text => ({ text, category: 'Database' })),
    ...corpus.skills.devops.map(text => ({ text, category: 'DevOps' })),
    ...corpus.skills.tools.map(text => ({ text, category: 'Tools' })),
    ...corpus.skills.learning.flatMap(learning => [
      { text: learning.category, category: 'Learning' },
      ...learning.topics.map(text => ({ text, category: learning.category })),
    ]),
  ];
  push(
    'skills',
    'Skills',
    skillEntries
      .filter(entry => includes(entry.text, query))
      .map(entry => ({
        section: 'skills',
        kind: 'skill',
        label: entry.text,
        subtitle: entry.category,
      }))
  );

  // About — tagline, description, current focus and "what I build".
  const aboutEntries: { label: string; subtitle?: string }[] = [
    { label: corpus.about.tagline },
    { label: corpus.about.description },
    ...corpus.about.currentFocus.map(focus => ({
      label: focus.title,
      subtitle: focus.description,
    })),
    ...corpus.about.whatIBuild.map(label => ({ label })),
  ];
  push(
    'about',
    'About',
    aboutEntries
      .filter(entry => includes(entry.label, query) || includes(entry.subtitle, query))
      .map(entry => ({ section: 'about', kind: 'about', label: entry.label, subtitle: entry.subtitle }))
  );

  // Social — github / linkedin / email.
  const socialEntries: { label: string; url: string }[] = [
    { label: 'GitHub', url: corpus.social.github },
    { label: 'LinkedIn', url: corpus.social.linkedin },
    { label: 'Email', url: corpus.social.email },
  ];
  push(
    'social',
    'Social',
    socialEntries
      .filter(entry => includes(entry.url, query) || includes(entry.label, query))
      .map(entry => ({
        section: 'social',
        kind: 'social',
        label: entry.label,
        subtitle: entry.url.replace('https://', ''),
      }))
  );

  // Contact — email/linkedin/github surfaced as a dedicated group (design fix 7).
  push(
    'contact',
    'Contact',
    socialEntries
      .filter(entry => includes(entry.url, query) || includes(entry.label, query))
      .map(entry => ({
        section: 'contact',
        kind: 'contact',
        label: entry.label,
        subtitle: entry.url.replace('mailto:', '').replace('https://', ''),
      }))
  );

  // CV — name + cvUrl.
  const cvLabel = `${corpus.about.username} — CV`;
  if (includes(cvLabel, query) || includes(corpus.social.cvUrl, query)) {
    push('cv', 'CV', [
      {
        section: 'cv',
        kind: 'cv',
        label: cvLabel,
        subtitle: corpus.social.cvUrl,
      },
    ]);
  }

  return { groups, total };
}
