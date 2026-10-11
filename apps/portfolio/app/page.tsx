'use client';

import React from 'react';
import Terminal from './components/terminal/terminal';

export default function Home() {
  return (
    <Terminal 
      username="visitor"
      hostname="portfolio"
    />
  );
}