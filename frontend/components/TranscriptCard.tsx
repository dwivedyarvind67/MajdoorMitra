'use client';

import React from 'react';
import { MessageSquare } from 'lucide-react';

interface TranscriptCardProps {
  transcript: string;
  language?: string;
}

export default function TranscriptCard({ transcript, language }: TranscriptCardProps) {
  if (!transcript) return null;

  return (
    <section className="my-3 rounded-2xl border border-[#e4e4e7] bg-[#f4f4f5] p-4 text-left sm:p-5" aria-label="मूल आवाज़ का लेखा">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-extrabold text-[#52525b]">
          <MessageSquare className="w-4 h-4" />
          आपकी मूल बात
        </span>
        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-slate-700">
          {language === 'hi' ? 'हिंदी' : 'English'}
        </span>
      </div>
      <p className="text-base font-medium leading-7 text-slate-900 sm:text-lg">
        &ldquo;{transcript}&rdquo;
      </p>
    </section>
  );
}
