'use client';

import React from 'react';
import { Briefcase } from 'lucide-react';
import { WorkEntry } from '../types';

interface WorkHistoryProps {
  entries: WorkEntry[];
  isLoading?: boolean;
}

export default function WorkHistory({ entries, isLoading }: WorkHistoryProps) {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-2xl border border-[#e4e4e7] bg-[#ffffff]"></div>
        ))}
      </div>
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-[#e4e4e7] bg-[#ffffff] py-10 text-center text-slate-600">
        <Briefcase className="mx-auto mb-3 h-9 w-9 text-[#52525b]" />
        <p className="text-base font-bold text-[#27272a]">अभी कोई काम का रिकॉर्ड नहीं</p>
        <p className="mt-1 text-sm">काम दर्ज होने के बाद वह यहाँ दिखाई देगा।</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {entries.map((w) => {
        const dateStr = new Date(w.work_date).toLocaleDateString('hi-IN', {
          day: 'numeric',
          month: 'short',
          year: 'numeric',
        });

        return (
          <div
            key={w.id}
            className="flex min-w-0 items-center justify-between gap-3 rounded-2xl border border-[#e4e4e7] bg-[#ffffff] p-4 shadow-[0_6px_20px_rgba(24,24,27,0.035)] sm:p-5"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#f4f4f5] text-[#52525b]">
                <Briefcase className="w-5 h-5" />
              </div>
              <div className="text-left">
                <h4 className="text-base font-extrabold text-[#27272a]">
                  {w.employer_name || 'मालिक का नाम नहीं'}
                </h4>
                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-sm text-slate-600">
                  <span>{dateStr}</span>
                  <span>•</span>
                  {w.wage_basis === 'hourly' ? (
                    <span>{w.hours_worked} घंटे @ ₹{w.hourly_rate}/घंटा</span>
                  ) : (
                    <span>{w.days_worked} दिन @ ₹{w.daily_wage}</span>
                  )}
                  {Number(w.overtime_hours || 0) > 0 && <span>• {w.overtime_hours} घंटे ओवरटाइम</span>}
                </div>
                {Number(w.allocated_amount || 0) > 0 && (
                  <p className="mt-1 text-xs font-semibold text-slate-500">काम से जोड़ा गया: ₹{w.allocated_amount}</p>
                )}
              </div>
            </div>

            <div className="text-right">
              <span className="shrink-0 text-base font-black text-[#52525b] sm:text-lg">
                ₹{w.total_earned}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
