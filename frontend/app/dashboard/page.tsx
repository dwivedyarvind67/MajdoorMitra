'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth-context';
import { api } from '../../lib/api';
import WageSummary from '../../components/WageSummary';
import EmployerCard from '../../components/EmployerCard';
import { LedgerSummary, TransactionItem } from '../../types';
import { ArrowRight, Mic, Download } from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, workerName, logout } = useAuth();

  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth');
      return;
    }
    if (!isAuthenticated) return;

    let active = true;
    Promise.all([api.getLedgerSummary(), api.getTransactions(10)])
      .then(([sumData, txData]) => {
        if (!active) return;
        setSummary(sumData);
        setTransactions(txData.transactions || []);
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

  if (authLoading || (!isAuthenticated && typeof window !== 'undefined')) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col px-5 py-6 space-y-6">
      {/* Top Bar */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-bold text-slate-400">खाता सारांश</span>
          <h1 className="text-xl font-black text-slate-900">{workerName || 'मज़दूर साथी'}</h1>
        </div>
        <button
          onClick={logout}
          className="text-xs font-semibold text-slate-500 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition"
        >
          लॉग आउट
        </button>
      </div>

      {/* Main Wage KPI Widget */}
      <WageSummary summary={summary} isLoading={loading} />

      {/* Quick Action Bar */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          href="/voice"
          className="flex items-center justify-center gap-2 py-3.5 px-4 bg-blue-600 text-white rounded-2xl font-bold text-xs shadow-md hover:bg-blue-700 transition"
        >
          <Mic className="w-4 h-4" />
          बोलकर दर्ज करें
        </Link>
        <Link
          href="/statements"
          className="flex items-center justify-center gap-2 py-3.5 px-4 bg-slate-100 text-slate-700 rounded-2xl font-bold text-xs hover:bg-slate-200 transition"
        >
          <Download className="w-4 h-4" />
          PDF पर्ची निकालें
        </Link>
      </div>

      {/* Employer Breakdown */}
      {summary?.employers && summary.employers.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-800">ठेकेदार-वार हिसाब</h3>
            <Link
              href="/employers"
              className="text-xs font-bold text-blue-600 flex items-center gap-1"
            >
              सभी देखें <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <div className="space-y-2">
            {summary.employers.slice(0, 3).map((emp) => (
              <EmployerCard key={emp.employer_id} summary={emp} />
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity Timeline */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">हाल के रिकॉर्ड (Recent)</h3>
          <Link
            href="/history"
            className="text-xs font-bold text-blue-600 flex items-center gap-1"
          >
            पूरा इतिहास <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {transactions.length === 0 ? (
          <div className="p-6 bg-slate-50 border border-dashed border-slate-200 rounded-2xl text-center text-xs text-slate-400">
            अभी तक कोई रिकॉर्ड दर्ज नहीं हुआ है।
          </div>
        ) : (
          <div className="space-y-2">
            {transactions.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between p-3.5 bg-white border border-slate-100 rounded-xl shadow-sm text-left"
              >
                <div>
                  <h4 className="text-xs font-bold text-slate-800">
                    {tx.employer_name || (tx.type === 'work' ? 'काम' : 'भुगतान')}
                  </h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {new Date(tx.date).toLocaleDateString('hi-IN', {
                      day: 'numeric',
                      month: 'short',
                    })}{' '}
                    • {tx.description || tx.type}
                  </p>
                </div>
                <span
                  className={`text-sm font-extrabold ${
                    tx.type === 'work' ? 'text-blue-800' : 'text-emerald-700'
                  }`}
                >
                  {tx.type === 'work' ? `₹${tx.amount}` : `+₹${tx.amount}`}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
