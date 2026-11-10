'use client';

import React from 'react';
import { AlertCircle, Calendar, TrendingUp } from 'lucide-react';
import { LedgerSummary } from '../types';

interface WageSummaryProps {
  summary: LedgerSummary | null;
  isLoading?: boolean;
}

const toneClasses: Record<string, string> = {
  slate: 'border-slate-200 bg-slate-50 text-slate-950',
  emerald: 'border-emerald-200 bg-emerald-50 text-emerald-950',
  amber: 'border-amber-300 bg-amber-50 text-amber-950',
  blue: 'border-blue-200 bg-blue-50 text-blue-950',
  rose: 'border-rose-200 bg-rose-50 text-rose-950',
};

function Metric({ label, value, tone, detail }: { label: string; value: string; tone: string; detail?: string }) {
  return (
    <div className={`min-w-0 rounded-xl border p-3 ${toneClasses[tone]}`}>
      <span className="text-sm font-semibold leading-5">{label}</span>
      <p className="mt-1 break-words text-xl font-black">₹{value}</p>
      {detail && <p className="mt-1 text-xs leading-4 opacity-80">{detail}</p>}
    </div>
  );
}

export default function WageSummary({ summary, isLoading }: WageSummaryProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4 rounded-2xl border border-slate-200 bg-white p-5" aria-label="हिसाब लोड हो रहा है">
        <div className="h-6 w-1/3 rounded bg-slate-200" />
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 6 }, (_, index) => <div key={index} className="h-24 rounded-xl bg-slate-100" />)}
        </div>
      </div>
    );
  }

  const earned = summary?.total_earned || '0.00';
  const received = summary?.total_received || '0.00';
  const advances = summary?.total_advances || '0.00';
  const balance = summary?.balance || '0.00';
  const pending = summary?.pending || '0.00';
  const overpaid = summary?.overpaid || '0.00';
  const workDays = summary?.total_work_days || '0.00';

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm" aria-labelledby="wage-summary-heading">
      <div className="mb-4 flex items-center justify-between gap-2">
        <h2 id="wage-summary-heading" className="flex items-center gap-2 text-lg font-bold text-slate-900">
          <TrendingUp className="h-5 w-5 text-blue-700" aria-hidden="true" />
          मज़दूरी का हिसाब
        </h2>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-900">रिपोर्ट किए रिकॉर्ड</span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Metric label="कुल कमाई" value={earned} tone="slate" />
        <Metric label="मिला भुगतान" value={received} tone="emerald" />
        <Metric label="इसमें अग्रिम" value={advances} tone="blue" detail="कुल मिले भुगतान में शामिल" />
        <Metric label="बाकी हिसाब" value={balance} tone={Number(balance) < 0 ? 'rose' : 'amber'} detail="कमाई घटा मिला भुगतान" />
        <Metric label="आपको मिलना बाकी" value={pending} tone="amber" />
        <Metric label="अधिक मिला" value={overpaid} tone="rose" detail="अग्रिम सहित कुल भुगतान के बाद" />
      </div>

      <div className="mt-3 flex items-center justify-between rounded-xl bg-slate-50 px-3 py-3 text-sm text-slate-800">
        <span className="flex items-center gap-2 font-semibold"><Calendar className="h-4 w-4 text-blue-700" aria-hidden="true" />काम के दिन</span>
        <span className="font-bold">{workDays}</span>
      </div>
      <p className="mt-3 flex items-start gap-2 text-sm leading-5 text-slate-600">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        हिसाब में काम के रिकॉर्ड से कमाई और नकद, UPI, बैंक व अग्रिम भुगतान शामिल हैं।
      </p>
    </section>
  );
}
