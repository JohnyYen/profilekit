'use client';

import React from 'react';

interface SkillsData {
  backend: string[];
  database: string[];
  devops: string[];
  tools: string[];
  learning: { category: string; topics: string[] }[];
}

interface SkillsSectionProps {
  data: SkillsData;
}

export default function SkillsSection({ data }: SkillsSectionProps) {
  const categories: { label: string; items: string[]; color: string }[] = [
    { label: 'Backend', items: data.backend, color: 'var(--starship-cyan)' },
    { label: 'Database', items: data.database, color: 'var(--starship-green)' },
    { label: 'DevOps', items: data.devops, color: 'var(--starship-yellow)' },
    { label: 'Tools', items: data.tools, color: 'var(--starship-purple)' },
  ];

  return (
    <div className="font-mono space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--starship-cyan)' }}>
          Skills
        </h2>
        <div className="h-px my-3" style={{ backgroundColor: 'var(--terminal-border)' }} />
      </div>

      <div className="grid gap-4">
        {categories.map(cat => (
          <div key={cat.label}>
            <h3 className="text-sm font-semibold mb-2" style={{ color: cat.color }}>
              {cat.label}
            </h3>
            <div className="flex flex-wrap gap-2">
              {cat.items.map((item, i) => (
                <span
                  key={i}
                  className="px-3 py-1 text-xs rounded"
                  style={{
                    backgroundColor: 'var(--terminal-bg-elevated)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--terminal-border)',
                  }}
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      {data.learning.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--starship-yellow)' }}>
            📚 Currently Learning
          </h3>
          <div className="space-y-2">
            {data.learning.map((item, i) => (
              <div key={i} style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-primary)' }}>{item.category}</span>
                <br />
                <span className="text-xs">{item.topics.join(', ')}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}