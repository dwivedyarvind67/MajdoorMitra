'use client';

import React, { Suspense, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth-context';
import { api } from '../../lib/api';
import WorkHistory from '../../components/WorkHistory';
import PaymentHistory from '../../components/PaymentHistory';
import { WorkEntry, Payment } from '../../types';
import { Briefcase, IndianRupee, ArrowLeft, Clock3 } from 'lucide-react';
import WageStory from '../../components/WageStory';

export default function HistoryPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [activeTab, setActiveTab] = useState<'story' | 'work' | 'payment'>('story');
  const [workEntries, setWorkEntries] = useState<WorkEntry[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);

  const refreshHistory = useCallback(async () => {
    const [wList, pList] = await Promise.all([api.getWorkEntries(), api.getPayments()]);
    setWorkEntries(wList || []);
    setPayments(pList || []);
  }, []);

  const handleAllocate = useCallback(async (paymentId: string, workEntryId: string, amount: string) => {
    await api.allocatePayment(paymentId, workEntryId, amount);
    await refreshHistory();
  }, [refreshHistory]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth');
      return;
    }
    if (!isAuthenticated) return;

    let active = true;
    Promise.all([api.getWorkEntries(), api.getPayments()])
      .then(([wList, pList]) => {
        if (!active) return;
        setWorkEntries(wList || []);
        setPayments(pList || []);
        setPageError(null);
      })
      .catch((error: unknown) => {
        if (active) setPageError(error instanceof Error ? error.message : 'इतिहास लोड नहीं हुआ। फिर से कोशिश करें।');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isAuthenticated, authLoading, router]);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-5 pb-4 sm:px-7 md:px-0">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push('/dashboard')}
          aria-label="डैशबोर्ड पर वापस जाएँ"
          className="-ml-2 flex h-11 w-11 items-center justify-center rounded-xl border border-[#e7e5dc] bg-[#fffefa] text-slate-600 transition hover:text-[#173b2f]"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <p className="text-sm font-extrabold text-[#9a6a2b]">आपके पुराने रिकॉर्ड</p>
          <h1 className="text-2xl font-black tracking-tight text-[#173b2f] sm:text-3xl">लेन-देन इतिहास</h1>
        </div>
      </div>

      {/* Tabs */}
      <div role="group" aria-label="इतिहास का प्रकार" className="grid grid-cols-3 gap-1 rounded-2xl border border-[#e7e5dc] bg-[#eeeee8] p-1.5">
        <button
          onClick={() => setActiveTab('story')}
          aria-pressed={activeTab === 'story'}
          className={`flex min-h-12 items-center justify-center gap-1.5 rounded-xl px-2 text-xs font-extrabold transition sm:gap-2 sm:px-3 sm:text-sm ${activeTab === 'story' ? 'bg-[#fffefa] text-[#173b2f] shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
        >
          <Clock3 className="h-4 w-4" /> कहानी
        </button>
        <button
          onClick={() => setActiveTab('work')}
          aria-pressed={activeTab === 'work'}
          className={`flex min-h-12 items-center justify-center gap-1.5 rounded-xl px-2 text-xs font-extrabold transition sm:gap-2 sm:px-3 sm:text-sm ${
            activeTab === 'work'
            ? 'bg-[#fffefa] text-[#173b2f] shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Briefcase className="w-4 h-4" />
          काम <span className="rounded-full bg-black/5 px-2 py-0.5">{workEntries.length}</span>
        </button>
        <button
          onClick={() => setActiveTab('payment')}
          aria-pressed={activeTab === 'payment'}
          className={`flex min-h-12 items-center justify-center gap-1.5 rounded-xl px-2 text-xs font-extrabold transition sm:gap-2 sm:px-3 sm:text-sm ${
            activeTab === 'payment'
            ? 'bg-[#fffefa] text-[#173b2f] shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <IndianRupee className="w-4 h-4" />
          भुगतान <span className="rounded-full bg-black/5 px-2 py-0.5">{payments.length}</span>
        </button>
      </div>

      {/* Content */}
      <div className="pt-1">
        {pageError && <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">{pageError}</div>}
        {activeTab === 'story' ? (
          <Suspense fallback={<div role="status" className="rounded-2xl border border-[#e7e5dc] bg-[#fffefa] p-8 text-center text-sm font-semibold text-slate-600">आपका हिसाब तैयार हो रहा है…</div>}>
            <WageStory />
          </Suspense>
        ) : activeTab === 'work' ? (
          <WorkHistory entries={workEntries} isLoading={loading} />
        ) : (
          <PaymentHistory payments={payments} workEntries={workEntries} onAllocate={handleAllocate} isLoading={loading} />
        )}
      </div>
    </div>
  );
}
