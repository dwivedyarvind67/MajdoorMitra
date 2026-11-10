'use client';

import React from 'react';
import { Globe } from 'lucide-react';
import { useLanguage } from '../lib/language-context';

interface LanguageToggleProps {
  className?: string;
  compact?: boolean;
}

export default function LanguageToggle({ className = '', compact = false }: LanguageToggleProps) {
  const { language, setLanguage, toggleLanguage } = useLanguage();

  if (compact) {
    return (
      <button
        type="button"
        onClick={toggleLanguage}
        aria-label={`Switch language to ${language === 'hi' ? 'English' : 'हिंदी'}`}
        className={`inline-flex items-center gap-1.5 rounded-xl border border-[#e4e4e7] bg-white px-2.5 py-1.5 text-xs font-bold text-zinc-700 shadow-sm transition hover:bg-[#f4f4f5] active:scale-95 ${className}`}
      >
        <Globe className="h-3.5 w-3.5 text-zinc-500" aria-hidden="true" />
        <span>{language === 'hi' ? 'EN' : 'हिं'}</span>
      </button>
    );
  }

  return (
    <div
      role="group"
      aria-label="Language / भाषा"
      className={`inline-flex items-center gap-0.5 rounded-xl border border-[#e4e4e7] bg-[#f4f4f5] p-1 shadow-inner ${className}`}
    >
      <button
        type="button"
        onClick={() => setLanguage('hi')}
        aria-pressed={language === 'hi'}
        className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-extrabold transition ${
          language === 'hi'
            ? 'bg-white text-zinc-900 shadow-sm'
            : 'text-zinc-600 hover:text-zinc-900'
        }`}
      >
        <span>हिंदी</span>
      </button>
      <button
        type="button"
        onClick={() => setLanguage('en')}
        aria-pressed={language === 'en'}
        className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-extrabold transition ${
          language === 'en'
            ? 'bg-white text-zinc-900 shadow-sm'
            : 'text-zinc-600 hover:text-zinc-900'
        }`}
      >
        <span>English</span>
      </button>
    </div>
  );
}
