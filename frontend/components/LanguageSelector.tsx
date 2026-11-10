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
    { code: 'hi', label: 'हिंदी' },
    { code: 'en', label: 'English' },
    { code: 'hinglish', label: 'हिंग्लिश' },
  ];

  return (
    <div role="group" aria-label="रिकॉर्डिंग की भाषा" className="flex items-center gap-1 rounded-2xl border border-[#e4e4e7] bg-[#ffffff] p-1 shadow-sm">
      <Globe className="ml-2 h-4 w-4 shrink-0 text-[#71717a]" aria-hidden="true" />
      <div className="flex gap-1">
        {languages.map((l) => (
          <button
            key={l.code}
            type="button"
            onClick={() => onLanguageChange(l.code)}
            aria-pressed={currentLanguage === l.code}
            className={`min-h-10 rounded-xl px-3 text-sm font-extrabold transition ${
              currentLanguage === l.code
                ? 'bg-[#27272a] text-white shadow-sm'
                : 'text-slate-600 hover:bg-[#f4f4f5] hover:text-slate-900'
            }`}
          >
            {l.label}
          </button>
        ))}
      </div>
    </div>
  );
}
