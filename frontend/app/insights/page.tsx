'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, CalendarDays, IndianRupee, Plus, TrendingUp } from 'lucide-react';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth-context';
import type { FinancialInsights, SavingsGoal } from '../../types';

const money = (value: string | number) => new Intl.NumberFormat('hi-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 2,
}).format(Number(value || 0));

export default function InsightsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [insights, setInsights] = useState<FinancialInsights | null>(null);
  const [goals, setGoals] = useState<SavingsGoal[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [targetDate, setTargetDate] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) { router.push('/auth'); return; }
    if (!isAuthenticated) return;
    let active = true;
    Promise.all([api.getFinancialInsights(6), api.getSavingsGoals()])
      .then(([data, goalData]) => {
        if (!active) return;
        setInsights(data);
        setGoals(goalData);
      })
      .catch(() => { if (active) setError('आपका रुझान अभी नहीं खुल पाया। इंटरनेट जाँचकर फिर कोशिश करें।'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isAuthenticated, authLoading, router]);

  const createGoal = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    try {
      setSaving(true);
      const goal = await api.createSavingsGoal({ name: name.trim(), target_amount: target, target_date: targetDate || undefined });
      setGoals((current) => [goal, ...current]);
      setName(''); setTarget(''); setTargetDate('');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'लक्ष्य सुरक्षित नहीं हुआ।'); }
    finally { setSaving(false); }
  };

  const closeGoal = async (goal: SavingsGoal) => {
    setError('');
    try {
      const updated = await api.updateSavingsGoal(goal.id, !goal.active);
      setGoals((current) => current.map((item) => item.id === goal.id ? updated : item));
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'लक्ष्य नहीं बदला।'); }
  };

  if (authLoading || (!isAuthenticated && typeof window !== 'undefined')) return <div className="flex min-h-[50vh] items-center justify-center" role="status"><div className="h-9 w-9 animate-spin rounded-full border-4 border-zinc-500 border-t-transparent" /></div>;

  const maxEarnings = Math.max(1, ...(insights?.monthly.map((item) => Number(item.earnings)) || []));
  const activeGoals = goals.filter((goal) => goal.active);
  return <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 pb-5 sm:px-6 md:gap-7 md:px-0">
    <header className="flex flex-wrap items-end justify-between gap-4 rounded-[1.6rem] border border-zinc-200 bg-white p-5 shadow-sm sm:p-7"><div className="flex items-start gap-3"><button onClick={() => router.push('/dashboard')} aria-label="डैशबोर्ड पर जाएँ" className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-zinc-200 text-zinc-600 hover:bg-zinc-100"><ArrowLeft className="h-4 w-4" /></button><div><p className="text-sm font-bold text-zinc-500">आपके दर्ज हिसाब से</p><h1 className="mt-1 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl">कमाई के रुझान</h1><p className="mt-1 text-sm leading-6 text-zinc-600">सभी आँकड़े ledger से निकाले गए हैं। अनुमान या भविष्य की कमाई शामिल नहीं है।</p></div></div><span className="inline-flex items-center gap-2 rounded-xl bg-zinc-100 px-3 py-2 text-xs font-bold text-zinc-700"><CalendarDays className="h-4 w-4" />पिछले 6 महीने</span></header>
    {error && <p role="alert" className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-950">{error}</p>}
    {loading ? <div role="status" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><div className="h-28 animate-pulse rounded-2xl bg-white" /><div className="h-28 animate-pulse rounded-2xl bg-white" /><div className="h-28 animate-pulse rounded-2xl bg-white" /><div className="h-28 animate-pulse rounded-2xl bg-white" /></div> : insights && <>
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="छह महीने का हिसाब">
        {[
          ['कुल दर्ज कमाई', insights.total_earnings],
          ['कुल मिले भुगतान', insights.total_payments],
          ['दर्ज हिसाब में बाकी', insights.total_pending],
          ['औसत रोज़ाना कमाई', insights.average_daily_earnings],
        ].map(([label, value]) => <article key={label} className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm"><p className="text-xs font-bold text-zinc-500">{label}</p><p className="mt-2 text-xl font-black tracking-tight text-zinc-900">{money(value)}</p></article>)}
      </section>

      <div className="grid items-start gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="monthly-trend-title"><div className="flex items-start gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700"><TrendingUp className="h-4 w-4" /></span><div><h2 id="monthly-trend-title" className="font-black text-zinc-900">महीने के अनुसार कमाई</h2><p className="mt-0.5 text-xs text-zinc-500">हर बार की लंबाई ₹ के हिसाब से है।</p></div></div>
          <div className="mt-5 space-y-4">{insights.monthly.map((month) => { const value = Number(month.earnings); const width = value > 0 ? Math.max(2, value / maxEarnings * 100) : 0; return <div key={month.month} className="grid grid-cols-[4rem_1fr_auto] items-center gap-3"><span className="text-xs font-bold text-zinc-600">{new Intl.DateTimeFormat('hi-IN', { month: 'short', timeZone: 'UTC' }).format(new Date(`${month.month}-01T00:00:00Z`))}</span><div className="h-3 overflow-hidden rounded-full bg-zinc-100" role="img" aria-label={`${month.month} कमाई ${money(month.earnings)}`}><div className="h-full rounded-full bg-zinc-800" style={{ width: `${width}%` }} /></div><span className="w-24 text-right text-xs font-extrabold text-zinc-900">{money(value)}</span></div>; })}</div>
          <p className="mt-5 rounded-xl bg-zinc-50 px-3 py-2.5 text-xs leading-5 text-zinc-600">औसत रोज़ाना कमाई सिर्फ़ daily-rate वाले रिकॉर्ड से निकली है। घंटे के हिसाब से दर्ज रिकॉर्ड औसत में शामिल नहीं हैं। “दर्ज तारीख़ें” उपस्थिति का स्वतंत्र प्रमाण नहीं हैं।</p>
        </section>

        <section className="rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="employer-comparison-title"><div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">अलग-अलग काम</p><h2 id="employer-comparison-title" className="mt-1 font-black text-zinc-900">मालिक के अनुसार</h2></div>
          {insights.employers.length ? <ul className="mt-3 divide-y divide-zinc-100">{insights.employers.map((employer, index) => <li key={employer.employer_id || `unassigned-${index}`} className="py-3 first:pt-0 last:pb-0"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-extrabold text-zinc-900">{employer.employer_name}</p><p className="mt-1 text-xs text-zinc-500">कमाई {money(employer.earnings)} · भुगतान {money(employer.payments)}</p></div><span className="shrink-0 text-sm font-black text-zinc-900">बाकी {money(employer.pending)}</span></div></li>)}</ul> : <p className="mt-4 rounded-xl bg-zinc-50 p-4 text-sm text-zinc-600">अभी तुलना के लिए कोई वित्तीय रिकॉर्ड नहीं है।</p>}
        </section>
      </div>

      <section className="grid items-start gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <form onSubmit={createGoal} className="space-y-3 rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5"><div className="flex items-start gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700"><IndianRupee className="h-4 w-4" /></span><div><h2 className="font-black text-zinc-900">बचत का लक्ष्य</h2><p className="mt-0.5 text-xs leading-5 text-zinc-500">यह लक्ष्य है; ऐप आपकी असली बचत या प्रगति नहीं गिनता।</p></div></div><label className="block text-sm font-bold text-zinc-700">लक्ष्य का नाम<input required maxLength={120} value={name} onChange={(event) => setName(event.target.value)} placeholder="जैसे बच्चों की पढ़ाई" className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 text-sm font-medium" /></label><label className="block text-sm font-bold text-zinc-700">लक्ष्य राशि (₹)<input required type="number" min="0.01" step="0.01" value={target} onChange={(event) => setTarget(event.target.value)} inputMode="decimal" className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 text-sm font-medium" /></label><label className="block text-sm font-bold text-zinc-700">लक्ष्य तारीख़ (वैकल्पिक)<input type="date" value={targetDate} onChange={(event) => setTargetDate(event.target.value)} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 text-sm font-medium" /></label><button disabled={saving} className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-zinc-900 px-4 text-sm font-extrabold text-white disabled:opacity-50"><Plus className="h-4 w-4" />{saving ? 'सुरक्षित हो रहा है…' : 'लक्ष्य सुरक्षित करें'}</button></form>
        <section className="rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="goals-title"><div className="flex items-center justify-between gap-2"><div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">आपने तय किए</p><h2 id="goals-title" className="mt-1 font-black text-zinc-900">मेरे बचत लक्ष्य</h2></div><span className="rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-bold text-zinc-700">{activeGoals.length} चालू</span></div>{goals.length ? <ul className="mt-3 divide-y divide-zinc-100">{goals.map((goal) => <li key={goal.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"><div><p className="text-sm font-extrabold text-zinc-900">{goal.name}</p><p className="mt-0.5 text-xs text-zinc-500">लक्ष्य {money(goal.target_amount)}{goal.target_date ? ` · ${new Date(`${goal.target_date}T12:00:00`).toLocaleDateString('hi-IN')} तक` : ''}{!goal.active ? ' · बंद' : ''}</p></div><button type="button" onClick={() => void closeGoal(goal)} className="min-h-9 rounded-lg border border-zinc-200 px-3 text-xs font-bold text-zinc-700 hover:bg-zinc-50">{goal.active ? 'लक्ष्य रोकें' : 'फिर चालू करें'}</button></li>)}</ul> : <p className="mt-4 rounded-xl bg-zinc-50 p-4 text-sm text-zinc-600">अभी कोई बचत लक्ष्य नहीं। लक्ष्य जोड़ना वैकल्पिक है।</p>}</section>
      </section>
    </>}
  </div>;
}
