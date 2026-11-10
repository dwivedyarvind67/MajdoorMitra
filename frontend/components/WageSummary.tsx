'use client';

import { AlertCircle, CalendarDays, IndianRupee, TrendingUp } from 'lucide-react';
import { LedgerSummary } from '../types';

interface WageSummaryProps { summary: LedgerSummary | null; isLoading?: boolean; }

function Metric({ label, value, detail, tone }: { label: string; value: string; detail?: string; tone: 'green' | 'sand' | 'plain' }) {
  const tones = {
    green: 'bg-[#e9f0e7] text-[#173b2f]',
    sand: 'bg-[#f7eddd] text-[#583e20]',
    plain: 'bg-[#f5f5f1] text-[#27352d]',
  };
  return (
    <div className={`min-w-0 rounded-2xl p-4 ${tones[tone]}`}>
      <span className="block text-sm font-bold leading-5 opacity-80">{label}</span>
      <p className="mt-1 break-words text-[1.35rem] font-black tracking-tight sm:text-2xl">₹{value}</p>
      {detail && <p className="mt-1 text-xs leading-5 opacity-75">{detail}</p>}
    </div>
  );
}

export default function WageSummary({ summary, isLoading }: WageSummaryProps) {
  if (isLoading) return (
    <div className="animate-pulse rounded-[1.75rem] border border-[#e7e5dc] bg-[#fffefa] p-5" aria-label="हिसाब लोड हो रहा है" role="status">
      <div className="h-5 w-32 rounded bg-slate-200" /><div className="mt-5 h-28 rounded-2xl bg-slate-100" />
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">{Array.from({ length: 3 }, (_, index) => <div key={index} className="h-24 rounded-2xl bg-slate-100" />)}</div>
    </div>
  );

  const earned = summary?.total_earned || '0.00';
  const received = summary?.total_received || '0.00';
  const advances = summary?.total_advances || '0.00';
  const pending = summary?.pending || '0.00';
  const overpaid = summary?.overpaid || '0.00';
  const workDays = summary?.total_work_days || '0.00';
  const hasOverpayment = Number(overpaid) > 0;
  const outstanding = hasOverpayment ? overpaid : pending;

  return (
    <section className="overflow-hidden rounded-[1.75rem] border border-[#e7e5dc] bg-[#fffefa] p-4 shadow-[0_12px_34px_rgba(40,54,43,0.055)] sm:p-5" aria-labelledby="wage-summary-heading">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 px-1">
        <h2 id="wage-summary-heading" className="flex items-center gap-2 text-lg font-black text-[#173b2f]">
          <TrendingUp className="h-5 w-5 text-[#28734e]" aria-hidden="true" /> मज़दूरी का हिसाब
        </h2>
        <span className="rounded-full border border-[#dbe7d9] bg-[#f1f5ef] px-3 py-1 text-xs font-bold text-[#315b3e]">आपके बताए रिकॉर्ड</span>
      </div>

      <div className="relative overflow-hidden rounded-2xl bg-[#173b2f] p-5 text-white sm:p-6">
        <div className="absolute -right-6 -top-10 h-36 w-36 rounded-full border border-white/10" aria-hidden="true" />
        <div className="absolute -right-1 -top-3 h-24 w-24 rounded-full border border-white/10" aria-hidden="true" />
        <div className="relative flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-[#d5e2d6]">
              <IndianRupee className="h-4 w-4 text-[#f1bf68]" aria-hidden="true" />{hasOverpayment ? 'कुल कमाई से ज़्यादा मिला' : 'आपको मिलना बाकी'}
            </p>
            <p className="mt-1 text-4xl font-black tracking-tight sm:text-5xl">₹{outstanding}</p>
          </div>
          <p className="max-w-[15rem] text-sm leading-6 text-[#d5e2d6]">{hasOverpayment ? 'दर्ज भुगतान, दर्ज कमाई से अधिक है।' : 'दर्ज कमाई में से दर्ज भुगतान घटाकर।'}</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-3">
        <Metric label="कुल कमाई" value={earned} tone="plain" />
        <Metric label="मिला भुगतान" value={received} tone="green" detail="अग्रिम सहित" />
        <Metric label="इसमें अग्रिम" value={advances} tone="sand" detail="मिले भुगतान में शामिल" />
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#e9e7df] bg-[#faf9f5] px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-bold text-[#36443b]"><CalendarDays className="h-4 w-4 text-[#28734e]" aria-hidden="true" />काम के दिन</span>
        <span className="text-base font-black text-[#173b2f]">{workDays}</span>
      </div>
      <p className="mt-3 flex items-start gap-2 px-1 text-xs leading-5 text-slate-600 sm:text-sm">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#9a6a2b]" aria-hidden="true" />
        यह हिसाब आपके पुष्टि किए रिकॉर्ड पर आधारित है। काम या भुगतान की स्वतंत्र जाँच नहीं हुई है।
      </p>
    </section>
  );
}
