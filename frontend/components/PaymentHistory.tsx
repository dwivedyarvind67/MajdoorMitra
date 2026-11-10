'use client';

import React, { useMemo, useState } from 'react';
import { ArrowDownLeft, ArrowRightLeft } from 'lucide-react';
import { Payment, WorkEntry } from '../types';

interface PaymentHistoryProps {
  payments: Payment[];
  workEntries: WorkEntry[];
  onAllocate: (paymentId: string, workEntryId: string, amount: string) => Promise<void>;
  isLoading?: boolean;
}

function AllocationForm({
  payment,
  workEntries,
  onAllocate,
}: {
  payment: Payment;
  workEntries: WorkEntry[];
  onAllocate: PaymentHistoryProps['onAllocate'];
}) {
  const available = useMemo(
    () => workEntries.filter((entry) =>
      Number(entry.outstanding_amount ?? entry.total_earned) > 0 &&
      (!payment.employer_id || payment.employer_id === entry.employer_id)
    ),
    [payment.employer_id, workEntries],
  );
  const remaining = Number(payment.unallocated_amount ?? payment.amount);
  const [workId, setWorkId] = useState('');
  const [amount, setAmount] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const selectedWork = available.find((entry) => entry.id === workId) ?? available[0];
  const selectedWorkId = selectedWork?.id ?? '';
  const maxAmount = Math.min(remaining, Number(selectedWork?.outstanding_amount ?? selectedWork?.total_earned ?? 0));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedWorkId || !amount || Number(amount) <= 0 || Number(amount) > maxAmount) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await onAllocate(payment.id, selectedWorkId, amount);
      setAmount('');
      setSaved(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'रकम काम से नहीं जुड़ पाई।');
    } finally {
      setBusy(false);
    }
  };

  if (available.length === 0) {
    return <p className="mt-2 text-sm text-slate-600">इस मालिक के लिए अभी कोई बाकी काम दर्ज नहीं है।</p>;
  }

  return (
    <form onSubmit={submit} className="mt-3 grid gap-3 rounded-2xl border border-[#e6e8df] bg-[#f8f8f3] p-3 sm:grid-cols-[1fr_10rem_auto] sm:items-end">
      <label className="text-sm font-bold text-slate-700">
        किस काम से जोड़ें
        <select value={selectedWorkId} onChange={(event) => setWorkId(event.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-[#d9ded5] bg-white px-3 text-base text-slate-950 focus:outline-none focus:ring-2 focus:ring-[#28734e]">
          {available.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {entry.employer_name || 'काम'} · {new Date(entry.work_date).toLocaleDateString('hi-IN')} · बाकी ₹{entry.outstanding_amount ?? entry.total_earned}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm font-bold text-slate-700">
        कितनी रकम
        <input type="number" inputMode="decimal" min="0.01" max={maxAmount} step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder={`₹${maxAmount.toFixed(2)} तक`} className="mt-1 min-h-11 w-full rounded-xl border border-[#d9ded5] bg-white px-3 text-base text-slate-950 focus:outline-none focus:ring-2 focus:ring-[#28734e]" />
      </label>
      <button type="submit" disabled={busy || !amount || Number(amount) > maxAmount} className="min-h-11 rounded-xl bg-[#173b2f] px-4 text-sm font-bold text-white hover:bg-[#245541] disabled:opacity-50">
        {busy ? 'जोड़ रहे हैं…' : 'काम से जोड़ें'}
      </button>
      {error && <p className="text-sm font-semibold text-red-800 sm:col-span-3" role="alert">{error}</p>}
      {saved && <p className="text-sm font-semibold text-[#285c3d] sm:col-span-3" role="status">रकम काम के रिकॉर्ड से जोड़ दी गई। कुल हिसाब नहीं बदला है।</p>}
    </form>
  );
}

export default function PaymentHistory({ payments, workEntries, onAllocate, isLoading }: PaymentHistoryProps) {
  if (isLoading) {
    return <div className="space-y-3" role="status" aria-label="भुगतान लोड हो रहे हैं">
      {[1, 2, 3].map((i) => <div key={i} className="h-24 animate-pulse rounded-2xl border border-[#e7e5dc] bg-[#fffefa]"></div>)}
    </div>;
  }

  if (!payments || payments.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-[#d9ddd3] bg-[#fffefa] py-10 text-center text-slate-600">
        <ArrowDownLeft className="mx-auto mb-3 h-9 w-9 text-[#a06d2c]" />
        <p className="text-base font-bold text-[#173b2f]">अभी कोई भुगतान रिकॉर्ड नहीं</p>
        <p className="mt-1 text-sm">मिला हुआ पैसा दर्ज होने के बाद यहाँ दिखाई देगा।</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {payments.map((payment) => {
        const dateStr = new Date(payment.payment_date).toLocaleDateString('hi-IN', {
          day: 'numeric', month: 'short', year: 'numeric',
        });
        const unallocated = Number(payment.unallocated_amount ?? payment.amount);
        const matchingWork = workEntries.some((entry) =>
          Number(entry.outstanding_amount ?? entry.total_earned) > 0 &&
          (!payment.employer_id || payment.employer_id === entry.employer_id)
        );

        return (
          <article key={payment.id} className="min-w-0 rounded-2xl border border-[#e7e5dc] bg-[#fffefa] p-4 shadow-[0_6px_20px_rgba(40,54,43,0.035)] sm:p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[#e8efe6] text-[#28734e]">
                  <ArrowDownLeft className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="min-w-0 text-left">
                  <h4 className="truncate text-base font-extrabold text-[#173b2f]">{payment.employer_name || 'मालिक का नाम नहीं'}</h4>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5 text-sm text-slate-600">
                    <span>{dateStr}</span><span>•</span><span className="capitalize">{payment.payment_type}</span>
                  </div>
                </div>
              </div>
              <div className="shrink-0 text-right">
                <span className="text-base font-black text-[#28734e] sm:text-lg">+₹{payment.amount}</span>
                {unallocated > 0 && <p className="mt-1 text-xs font-semibold text-slate-500">काम से नहीं जोड़ा: ₹{unallocated.toFixed(2)}</p>}
              </div>
            </div>
            {unallocated > 0 && matchingWork && (
              <details className="mt-3 border-t border-[#eeece4] pt-3">
                <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 rounded-xl px-2 text-sm font-extrabold text-[#285c3d] hover:bg-[#f3f6f0]">
                  <span className="inline-flex items-center gap-2"><ArrowRightLeft className="h-4 w-4" aria-hidden="true" /> किस काम का भुगतान है?</span>
                  <span aria-hidden="true">＋</span>
                </summary>
                <AllocationForm payment={payment} workEntries={workEntries} onAllocate={onAllocate} />
              </details>
            )}
            {unallocated > 0 && !matchingWork && <p className="mt-3 border-t border-[#eeece4] pt-3 text-xs leading-5 text-slate-600">यह रकम दर्ज है। इसे काम से जोड़ने के लिए पहले उसी मालिक का काम दर्ज करें।</p>}
          </article>
        );
      })}
    </div>
  );
}
