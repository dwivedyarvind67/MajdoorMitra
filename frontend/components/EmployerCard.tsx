'use client';

import React from 'react';
import { Users } from 'lucide-react';
import { EmployerSummary } from '../types';

interface EmployerCardProps {
  summary: EmployerSummary;
  onManage?: (employerId: string) => void;
}

export default function EmployerCard({ summary, onManage }: EmployerCardProps) {
  const pendingNum = Number(summary.pending || 0);

  return (
    <article
      className="rounded-2xl border border-[#e4e4e7] bg-[#ffffff] p-4 text-left shadow-[0_6px_20px_rgba(24,24,27,0.035)] transition hover:border-[#e4e4e7] sm:p-5"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#f4f4f5] text-[#52525b]">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-base font-extrabold text-[#27272a]">{summary.employer_name}</h4>
            <span className="text-sm text-slate-500">{summary.total_work_days} दिन काम</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 border-t border-[#f4f4f5] pt-3 text-sm sm:grid-cols-4">
        <div>
          <span className="text-slate-500">कमाई</span>
          <p className="font-extrabold text-slate-800">₹{summary.total_earned}</p>
        </div>
        <div>
          <span className="text-slate-500">मिला</span>
          <p className="font-extrabold text-[#52525b]">₹{summary.total_received}</p>
        </div>
        <div>
          <span className="text-slate-500">अग्रिम</span>
          <p className="font-extrabold text-[#71717a]">₹{summary.total_advances || '0.00'}</p>
        </div>
        <div>
          <span className="text-slate-500">मिलना बाकी</span>
          <p className={`font-extrabold ${pendingNum > 0 ? 'text-[#71717a]' : 'text-slate-600'}`}>
            ₹{summary.pending}
          </p>
        </div>
      </div>
      {onManage && <button type="button" onClick={() => onManage(summary.employer_id)} className="mt-4 inline-flex min-h-10 items-center gap-2 rounded-lg border border-zinc-200 px-3 text-sm font-bold text-zinc-700 transition hover:bg-zinc-50">काम की जगह और दरें <span aria-hidden="true">→</span></button>}
    </article>
  );
}
