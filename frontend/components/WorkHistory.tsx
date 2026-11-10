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
          <div key={i} className="h-16 bg-slate-100 rounded-xl animate-pulse"></div>
        ))}
      </div>
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400 bg-white rounded-2xl border border-dashed border-slate-200">
        <Briefcase className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm font-medium">कोई काम का रिकॉर्ड नहीं मिला</p>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {entries.map((w) => {
        const dateStr = new Date(w.work_date).toLocaleDateString('hi-IN', {
          day: 'numeric',
          month: 'short',
          year: 'numeric',
        });

        return (
          <div
            key={w.id}
            className="flex items-center justify-between p-3.5 bg-white border border-slate-100 rounded-xl shadow-sm"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-bold">
                <Briefcase className="w-5 h-5" />
              </div>
              <div className="text-left">
                <h4 className="text-sm font-bold text-slate-800">
                  {w.employer_name || 'मालिक का नाम नहीं'}
                </h4>
                <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                  <span>{dateStr}</span>
                  <span>•</span>
                  <span>{w.days_worked} दिन @ ₹{w.daily_wage}</span>
                </div>
              </div>
            </div>

            <div className="text-right">
              <span className="text-base font-extrabold text-blue-800">
                ₹{w.total_earned}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
