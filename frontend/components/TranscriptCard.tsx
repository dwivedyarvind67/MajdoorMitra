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
    <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 my-3 text-left">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold text-blue-800 flex items-center gap-1.5 uppercase tracking-wide">
          <MessageSquare className="w-4 h-4" />
          आपकी बात (Your Statement)
        </span>
        <span className="text-[11px] bg-blue-200 text-blue-900 px-2 py-0.5 rounded-full font-medium">
          {language === 'hi' ? 'हिंदी' : 'English'}
        </span>
      </div>
      <p className="text-slate-800 font-medium text-base leading-relaxed">
        &ldquo;{transcript}&rdquo;
      </p>
    </div>
  );
}
