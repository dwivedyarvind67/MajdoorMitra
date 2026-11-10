'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth-context';
import { api } from '../../lib/api';
import WorkHistory from '../../components/WorkHistory';
import PaymentHistory from '../../components/PaymentHistory';
import { WorkEntry, Payment } from '../../types';
import { Briefcase, IndianRupee, ArrowLeft } from 'lucide-react';

export default function HistoryPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [activeTab, setActiveTab] = useState<'work' | 'payment'>('work');
  const [workEntries, setWorkEntries] = useState<WorkEntry[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);

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
      })
      .catch((error: unknown) => {
        if (active) console.error(error);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isAuthenticated, authLoading, router]);

  return (
    <div className="flex flex-col px-5 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push('/dashboard')}
          className="p-2 -ml-2 text-slate-600 hover:text-slate-900 rounded-full hover:bg-slate-100 transition"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-black text-slate-900">लेन-देन इतिहास</h1>
          <p className="text-xs text-slate-500">सभी काम और भुगतान के रिकॉर्ड</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex bg-slate-100 p-1 rounded-xl">
        <button
          onClick={() => setActiveTab('work')}
          className={`flex-1 py-2 rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition ${
            activeTab === 'work'
              ? 'bg-white text-blue-700 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Briefcase className="w-4 h-4" />
          काम का रिकॉर्ड ({workEntries.length})
        </button>
        <button
          onClick={() => setActiveTab('payment')}
          className={`flex-1 py-2 rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition ${
            activeTab === 'payment'
              ? 'bg-white text-emerald-700 shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <IndianRupee className="w-4 h-4" />
          मिला भुगतान ({payments.length})
        </button>
      </div>

      {/* Content */}
      <div className="pt-2">
        {activeTab === 'work' ? (
          <WorkHistory entries={workEntries} isLoading={loading} />
        ) : (
          <PaymentHistory payments={payments} isLoading={loading} />
        )}
      </div>
    </div>
  );
}
