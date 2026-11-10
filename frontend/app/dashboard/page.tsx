'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowRight, CircleHelp, Download, FileText, Mic, RotateCw, TrendingUp, Users } from 'lucide-react';
import { useAuth } from '../../lib/auth-context';
import { api } from '../../lib/api';
import WageSummary from '../../components/WageSummary';
import EmployerCard from '../../components/EmployerCard';
import { LedgerSummary, TransactionItem } from '../../types';

export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, workerName, logout } = useAuth();
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) { router.push('/auth'); return; }
    if (!isAuthenticated) return;
    let active = true;
    Promise.all([api.getLedgerSummary(), api.getTransactions(10)])
      .then(([sumData, txData]) => {
        if (!active) return;
        setLoadError(null);
        setSummary(sumData);
        setTransactions(txData.transactions || []);
      })
      .catch(() => { if (active) setLoadError('हिसाब अभी नहीं खुल पाया। इंटरनेट जाँचकर फिर कोशिश करें।'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isAuthenticated, authLoading, router, reload]);

  if (authLoading || (!isAuthenticated && typeof window !== 'undefined')) return (
    <div className="flex min-h-[45vh] items-center justify-center" role="status" aria-label="खाता खुल रहा है">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#52525b] border-t-transparent" />
    </div>
  );

  const amount = (value: string | number) => new Intl.NumberFormat('hi-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(Number(value));
  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-5 pb-4 sm:px-7 md:gap-8 md:px-0">
      <header className="flex flex-wrap items-end justify-between gap-4 rounded-[1.75rem] border border-[#e4e4e7] bg-[#ffffff] p-5 shadow-[0_8px_28px_rgba(24,24,27,0.04)] sm:p-7">
        <div><p className="text-sm font-extrabold text-[#71717a]">आपका काम · आपका हिसाब</p><h1 className="mt-1 text-3xl font-black tracking-tight text-[#27272a] sm:text-4xl">नमस्ते, {workerName || 'मज़दूर साथी'} जी</h1><p className="mt-2 text-base text-slate-600">कमाई, भुगतान और बाकी रकम एक जगह।</p></div>
        <div className="flex flex-wrap items-center gap-2"><Link href="/insights" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[#e4e4e7] bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-zinc-50"><TrendingUp className="h-4 w-4" />कमाई के रुझान</Link><Link href="/voice-studio" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[#e4e4e7] bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-zinc-50"><Mic className="h-4 w-4" />Voice Studio</Link><Link href="/help" aria-label="सहायता" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-[#e4e4e7] bg-white px-3 text-sm font-bold text-slate-700 transition hover:bg-zinc-50"><CircleHelp className="h-4 w-4" />मदद</Link><button onClick={logout} className="min-h-11 rounded-xl border border-[#e4e4e7] bg-white px-4 text-sm font-bold text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-800">लॉग आउट</button></div>
      </header>

      {loadError && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-950"><span>{loadError}</span><button onClick={() => { setLoading(true); setLoadError(null); setReload((value) => value + 1); }} className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-white px-3 font-bold text-amber-900"><RotateCw className="h-4 w-4" /> फिर कोशिश करें</button></div>}

      <div className="grid items-start gap-5 lg:grid-cols-[1.1fr_0.9fr] lg:gap-7">
        <div className="space-y-5">
          <WageSummary summary={summary} isLoading={loading} />
          {summary?.employers && summary.employers.length > 0 && (
            <section className="rounded-[1.75rem] border border-[#e4e4e7] bg-[#ffffff] p-5 shadow-[0_8px_28px_rgba(24,24,27,0.04)] sm:p-6">
              <div className="mb-4 flex items-center justify-between gap-2"><div><p className="text-sm font-bold text-[#71717a]">अलग-अलग काम का हिसाब</p><h2 className="mt-1 text-xl font-black text-[#27272a]">मालिक के अनुसार</h2></div><Link href="/employers" className="inline-flex min-h-10 items-center gap-1 rounded-lg px-2 text-sm font-extrabold text-[#52525b] hover:bg-[#f4f4f5]">सभी देखें <ArrowRight className="h-4 w-4" /></Link></div>
              <div className="space-y-3">{summary.employers.slice(0, 3).map((employer) => <EmployerCard key={employer.employer_id} summary={employer} />)}</div>
            </section>
          )}
        </div>

        <div className="space-y-5">
          <section className="grid grid-cols-2 gap-3">
            <Link href="/voice" className="group flex min-h-32 flex-col justify-between rounded-3xl bg-[#27272a] p-4 text-white shadow-[0_12px_30px_rgba(24,24,27,0.14)] transition hover:-translate-y-0.5 hover:bg-[#3f3f46] sm:p-5">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 text-[#d4d4d8]"><Mic className="h-5 w-5" /></span><span className="flex items-center justify-between gap-1 text-sm font-extrabold sm:text-base">बोलकर दर्ज करें <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></span>
            </Link>
            <Link href="/statements" className="group flex min-h-32 flex-col justify-between rounded-3xl border border-[#e4e4e7] bg-[#ffffff] p-4 text-[#27272a] shadow-[0_8px_28px_rgba(24,24,27,0.04)] transition hover:-translate-y-0.5 hover:shadow-lg sm:p-5">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#f4f4f5] text-[#71717a]"><Download className="h-5 w-5" /></span><span className="flex items-center justify-between gap-1 text-sm font-extrabold sm:text-base">मज़दूरी पर्ची <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></span>
            </Link>
          </section>

          <section className="rounded-[1.75rem] border border-[#e4e4e7] bg-[#ffffff] p-5 shadow-[0_8px_28px_rgba(24,24,27,0.04)] sm:p-6">
            <div className="mb-4 flex items-end justify-between gap-2"><div><p className="text-sm font-bold text-[#71717a]">सबसे नए रिकॉर्ड</p><h2 className="mt-1 text-xl font-black text-[#27272a]">हाल की गतिविधि</h2></div><Link href="/history" className="inline-flex min-h-10 items-center gap-1 rounded-lg px-2 text-sm font-extrabold text-[#52525b] hover:bg-[#f4f4f5]">इतिहास <ArrowRight className="h-4 w-4" /></Link></div>
            {loading ? <div role="status" className="space-y-3"><div className="h-16 animate-pulse rounded-2xl bg-slate-100" /><div className="h-16 animate-pulse rounded-2xl bg-slate-100" /></div> : transactions.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[#e4e4e7] bg-[#fafafa] px-5 py-7 text-center"><span className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-[#f4f4f5] text-[#52525b]"><FileText className="h-5 w-5" /></span><p className="mt-3 text-base font-bold text-[#27272a]">अभी कोई रिकॉर्ड नहीं</p><p className="mt-1 text-sm leading-6 text-slate-600">पहला काम या भुगतान बोलकर दर्ज करें।</p><Link href="/voice" className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl bg-[#27272a] px-4 text-sm font-bold text-white"><Mic className="h-4 w-4" />रिकॉर्ड करें</Link></div>
            ) : (
              <ul className="space-y-2">{transactions.map((tx) => <li key={tx.id} className="flex items-center justify-between gap-3 rounded-2xl bg-[#fafafa] p-3.5 sm:p-4"><div className="flex min-w-0 items-center gap-3"><span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${tx.type === 'work' ? 'bg-[#e4e4e7] text-[#52525b]' : 'bg-[#f4f4f5] text-[#71717a]'}`}>{tx.type === 'work' ? <Users className="h-5 w-5" /> : <Download className="h-5 w-5" />}</span><div className="min-w-0"><h3 className="truncate text-sm font-extrabold text-[#27272a]">{tx.employer_name || (tx.type === 'work' ? 'काम का रिकॉर्ड' : 'मिला भुगतान')}</h3><p className="mt-0.5 truncate text-xs text-slate-500">{new Date(tx.date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short', year: 'numeric' })}{tx.description ? ` · ${tx.description}` : ''}</p></div></div><span className={`shrink-0 text-sm font-black ${tx.type === 'work' ? 'text-[#52525b]' : 'text-[#71717a]'}`}>{amount(tx.amount)}</span></li>)}</ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
