'use client';

import { useState, useEffect, useCallback } from 'react';

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

interface ApiResponse {
  projects: Project[];
  source: 'github' | 'fallback';
  fetchedAt: string;
}

interface UseGithubProjectsReturn {
  projects: Project[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useGithubProjects(): UseGithubProjectsReturn {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = useCallback(async (refresh = false) => {
    setLoading(true);
    setError(null);

    try {
      const url = refresh ? '/api/github?refresh=1' : '/api/github';
      const res = await fetch(url);

      if (!res.ok) {
        throw new Error(`Failed to fetch projects: ${res.statusText}`);
      }

      const data: ApiResponse = await res.json();
      setProjects(data.projects);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to fetch projects'
      );
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const refresh = useCallback(() => {
    fetchProjects(true);
  }, [fetchProjects]);

  return { projects, loading, error, refresh };
}
