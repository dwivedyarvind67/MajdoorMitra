'use client';

import React from 'react';
import { Users } from 'lucide-react';
import { EmployerSummary } from '../types';

interface EmployerCardProps {
  summary: EmployerSummary;
}

export default function EmployerCard({ summary }: EmployerCardProps) {
  const pendingNum = Number(summary.pending || 0);

  return (
    <article
      className="rounded-2xl border border-[#e7e5dc] bg-[#fffefa] p-4 text-left shadow-[0_6px_20px_rgba(40,54,43,0.035)] transition hover:border-[#cad8c6] sm:p-5"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e8efe6] text-[#28734e]">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-base font-extrabold text-[#173b2f]">{summary.employer_name}</h4>
            <span className="text-sm text-slate-500">{summary.total_work_days} दिन काम</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 border-t border-[#eeece4] pt-3 text-sm sm:grid-cols-4">
        <div>
          <span className="text-slate-500">कमाई</span>
          <p className="font-extrabold text-slate-800">₹{summary.total_earned}</p>
        </div>
        <div>
          <span className="text-slate-500">मिला</span>
          <p className="font-extrabold text-[#28734e]">₹{summary.total_received}</p>
        </div>
        <div>
          <span className="text-slate-500">अग्रिम</span>
          <p className="font-extrabold text-[#81581f]">₹{summary.total_advances || '0.00'}</p>
        </div>
        <div>
          <span className="text-slate-500">मिलना बाकी</span>
          <p className={`font-extrabold ${pendingNum > 0 ? 'text-[#93601c]' : 'text-slate-600'}`}>
            ₹{summary.pending}
          </p>
        </div>
      </div>
    </article>
  );
}
