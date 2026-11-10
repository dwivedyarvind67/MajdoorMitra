'use client';

import React from 'react';
import { Users, ChevronRight } from 'lucide-react';
import { EmployerSummary } from '../types';

interface EmployerCardProps {
  summary: EmployerSummary;
  onClick?: () => void;
}

export default function EmployerCard({ summary, onClick }: EmployerCardProps) {
  const pendingNum = Number(summary.pending || 0);

  return (
    <div
      onClick={onClick}
      className="p-4 bg-white rounded-2xl border border-slate-100 shadow-sm hover:border-blue-200 transition cursor-pointer text-left"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-700">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <h4 className="font-bold text-slate-800 text-sm">{summary.employer_name}</h4>
            <span className="text-xs text-slate-400">{summary.total_work_days} दिन काम</span>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-400" />
      </div>

      <div className="grid grid-cols-2 gap-3 border-t border-slate-100 pt-3 text-sm sm:grid-cols-4">
        <div>
          <span className="text-slate-400">कमाई</span>
          <p className="font-bold text-slate-700">₹{summary.total_earned}</p>
        </div>
        <div>
          <span className="text-slate-400">मिला</span>
          <p className="font-bold text-emerald-700">₹{summary.total_received}</p>
        </div>
        <div>
          <span className="text-slate-500">अग्रिम</span>
          <p className="font-bold text-blue-800">₹{summary.total_advances || '0.00'}</p>
        </div>
        <div>
          <span className="text-slate-500">मिलना बाकी</span>
          <p className={`font-bold ${pendingNum > 0 ? 'text-amber-700' : 'text-slate-600'}`}>
            ₹{summary.pending}
          </p>
        </div>
      </div>
    </div>
  );
}
