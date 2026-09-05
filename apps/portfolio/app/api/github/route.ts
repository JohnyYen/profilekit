import { NextRequest } from 'next/server';
import projectsData from '@/app/data/projects.json';

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

interface GitHubRepo {
  name: string;
  description: string | null;
  language: string | null;
  stargazers_count: number;
  forks_count: number;
  updated_at: string;
  html_url: string;
  topics: string[];
}

interface ApiResponse {
  projects: Project[];
  source: 'github' | 'fallback';
  fetchedAt: string;
}

export async function GET(request: NextRequest): Promise<Response> {
  const refresh = request.nextUrl.searchParams.get('refresh') === '1';
  const fetchedAt = new Date().toISOString();

  try {
    const fetchOptions: RequestInit & { next?: { revalidate: number } } = {
      headers: {
        Accept: 'application/vnd.github.mercy-preview+json',
      },
    };

    if (refresh) {
      fetchOptions.cache = 'no-store';
    } else {
      fetchOptions.next = { revalidate: 21600 };
    }

    const res = await fetch(
      'https://api.github.com/users/JohnyYen/repos?per_page=100&sort=updated',
      fetchOptions
    );

    if (!res.ok) {
      throw new Error(`GitHub API responded with ${res.status}`);
    }

    const repos: GitHubRepo[] = await res.json();

    const showcaseRepos = repos.filter(
      (repo) => repo.topics && repo.topics.includes('showcase')
    );

    const projects: Project[] = showcaseRepos.map((repo) => ({
      name: repo.name,
      description: repo.description || '',
      language: repo.language,
      stars: repo.stargazers_count,
      forks: repo.forks_count,
      updatedAt: repo.updated_at,
      url: repo.html_url,
      topics: repo.topics || [],
    }));

    const response: ApiResponse = { projects, source: 'github', fetchedAt };
    return Response.json(response);
  } catch {
    // Fallback to projects.json when GitHub API fails
    const typedData = projectsData as Array<{
      name: string;
      description: string;
      tech: string;
      url: string;
    }>;

    const fallbackProjects: Project[] = typedData.map((p) => ({
      name: p.name,
      description: p.description,
      language: p.tech || null,
      stars: 0,
      forks: 0,
      updatedAt: new Date().toISOString(),
      url: p.url,
      topics: [],
    }));

    const response: ApiResponse = {
      projects: fallbackProjects,
      source: 'fallback',
      fetchedAt,
    };
    return Response.json(response);
  }
}
