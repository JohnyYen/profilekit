'use client';

import React from 'react';

// Canonical skill detail: either a plain string or an object with name + optional icon references.
type SkillDetail = string | { name: string; icon?: string; iconUrl?: string };

interface SkillsData {
  categories: { label: string; details: SkillDetail[] }[];
}

interface SkillsSectionProps {
  data: SkillsData;
}

// Category heading colors cycle through the terminal palette.
const CATEGORY_COLORS = [
  'var(--starship-cyan)',
  'var(--starship-green)',
  'var(--starship-yellow)',
  'var(--starship-purple)',
  'var(--starship-cyan)',
  'var(--starship-green)',
  'var(--starship-yellow)',
];

function SkillIcon({ detail }: { detail: Exclude<SkillDetail, string> }) {
  if (detail.icon) {
    return (
      <img
        src={`https://skillicons.dev/icons?i=${detail.icon}`}
        alt={detail.name}
        width={20}
        height={20}
        className="inline-block"
        style={{ verticalAlign: 'middle' }}
      />
    );
  }
  if (detail.iconUrl) {
    return (
      <img
        src={detail.iconUrl}
        alt={detail.name}
        width={20}
        height={20}
        className="inline-block"
        style={{ verticalAlign: 'middle' }}
      />
    );
  }
  return null;
}

function SkillChip({ detail }: { detail: SkillDetail }) {
  if (typeof detail === 'string') {
    return (
      <span
        className="px-3 py-1 text-xs rounded"
        style={{
          backgroundColor: 'var(--terminal-bg-elevated)',
          color: 'var(--text-primary)',
          border: '1px solid var(--terminal-border)',
        }}
      >
        {detail}
      </span>
    );
  }

  const hasIcon = !!(detail.icon || detail.iconUrl);

  return (
    <span
      className="px-3 py-1 text-xs rounded inline-flex items-center gap-1.5"
      style={{
        backgroundColor: 'var(--terminal-bg-elevated)',
        color: 'var(--text-primary)',
        border: '1px solid var(--terminal-border)',
      }}
    >
      {hasIcon && <SkillIcon detail={detail} />}
      {detail.name}
    </span>
  );
}

export default function SkillsSection({ data }: SkillsSectionProps) {
  return (
    <div className="font-mono space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--starship-cyan)' }}>
          Skills
        </h2>
        <div className="h-px my-3" style={{ backgroundColor: 'var(--terminal-border)' }} />
      </div>

      <div className="grid gap-4">
        {data.categories.map((cat, idx) => (
          <div key={cat.label}>
            <h3
              className="text-sm font-semibold mb-2"
              style={{ color: CATEGORY_COLORS[idx % CATEGORY_COLORS.length] }}
            >
              {cat.label}
            </h3>
            <div className="flex flex-wrap gap-2">
              {cat.details.map((detail, i) => (
                <SkillChip key={i} detail={detail} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
