'use client';

import React from 'react';
import { Globe } from 'lucide-react';

interface LanguageSelectorProps {
  currentLanguage: string;
  onLanguageChange: (lang: string) => void;
}

export default function LanguageSelector({
  currentLanguage,
  onLanguageChange,
}: LanguageSelectorProps) {
  const languages = [
    { code: 'hi', label: 'हिंदी (Hindi)' },
    { code: 'en', label: 'English' },
  ];

  return (
    <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl">
      <Globe className="w-4 h-4 text-slate-500 ml-2" />
      <div className="flex gap-1">
        {languages.map((l) => (
          <button
            key={l.code}
            onClick={() => onLanguageChange(l.code)}
            className={`px-3 py-1 text-xs font-bold rounded-lg transition ${
              currentLanguage === l.code
                ? 'bg-white text-blue-700 shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {l.label}
          </button>
        ))}
      </div>
    </div>
  );
}
