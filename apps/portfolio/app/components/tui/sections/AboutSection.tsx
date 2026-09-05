'use client';

import React from 'react';

interface AboutData {
  username: string;
  tagline: string;
  description: string;
  currentFocus: { title: string; description: string }[];
  whatIBuild: string[];
  learningJourney: string;
}

interface AboutSectionProps {
  data: AboutData;
}

export default function AboutSection({ data }: AboutSectionProps) {
  return (
    <div className="font-mono space-y-6">
      <div>
        <h2 className="text-lg font-bold" style={{ color: 'var(--starship-cyan)' }}>
          About
        </h2>
        <div className="h-px my-3" style={{ backgroundColor: 'var(--terminal-border)' }} />
      </div>

      <div>
        <p style={{ color: 'var(--text-primary)' }}>
          👋 Hi! I&apos;m <strong>{data.username}</strong>
        </p>
        <p className="mt-1" style={{ color: 'var(--starship-green)' }}>
          {data.tagline}
        </p>
        <p className="mt-2" style={{ color: 'var(--text-secondary)' }}>
          {data.description}
        </p>
      </div>

      <div>
        <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--starship-yellow)' }}>
          🎯 Current Focus
        </h3>
        <ul className="space-y-2">
          {data.currentFocus.map((item, i) => (
            <li key={i} style={{ color: 'var(--text-secondary)' }}>
              <span style={{ color: 'var(--text-primary)' }}>{item.title}</span>
              <br />
              <span className="text-sm">{item.description}</span>
            </li>
          ))}
        </ul>
      </div>

      {data.whatIBuild.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--starship-yellow)' }}>
            🔧 What I Build
          </h3>
          <ul className="space-y-1">
            {data.whatIBuild.map((item, i) => (
              <li key={i} style={{ color: 'var(--text-secondary)' }}>
                • {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--starship-yellow)' }}>
          📚 Learning Journey
        </h3>
        <p style={{ color: 'var(--text-secondary)' }}>{data.learningJourney}</p>
      </div>
    </div>
  );
}