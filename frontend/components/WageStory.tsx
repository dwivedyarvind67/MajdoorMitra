'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { ArrowDownLeft, ArrowUpRight, Briefcase, CalendarDays, CircleCheck, Clock3, Search } from 'lucide-react';
import { api } from '../lib/api';
import { Employer, LedgerAlert, LedgerSummary, TransactionItem } from '../types';

const todayISO = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
};

const monthStartISO = () => `${todayISO().slice(0, 7)}-01`;
const money = (value: string | number) => new Intl.NumberFormat('hi-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 2,
}).format(Number(value));

type Filters = { employer_id?: string; start_date?: string; end_date?: string };

export default function WageStory() {
  const [employers, setEmployers] = useState<Employer[]>([]);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [alerts, setAlerts] = useState<LedgerAlert[]>([]);
  const [draft, setDraft] = useState({ start_date: monthStartISO(), end_date: todayISO(), employer_id: '' });
  const [filters, setFilters] = useState<Filters>({ start_date: monthStartISO(), end_date: todayISO() });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getEmployers().then(setEmployers).catch(() => setEmployers([]));
    api.getLedgerAlerts().then(setAlerts).catch(() => setAlerts([]));
  }, []);

  useEffect(() => {
    let current = true;
    Promise.all([api.getTransactions(200, filters), api.getLedgerSummary(filters)])
      .then(([timeline, totals]) => {
        if (!current) return;
        setTransactions(timeline.transactions || []);
        setSummary(totals);
      })
      .catch((cause: unknown) => {
        if (current) setError(cause instanceof Error ? cause.message : 'कहानी लोड नहीं हो पाई। फिर कोशिश करें।');
      })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [filters]);

  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase('hi-IN');
    if (!needle) return transactions;
    return transactions.filter((item) =>
      [item.employer_name, item.description, item.type, item.payment_type]
        .filter(Boolean).join(' ').toLocaleLowerCase('hi-IN').includes(needle),
    );
  }, [transactions, search]);

  const applyFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setFilters({
      employer_id: draft.employer_id || undefined,
      start_date: draft.start_date || undefined,
      end_date: draft.end_date || undefined,
    });
  };

  const invalidRange = !!draft.start_date && !!draft.end_date && draft.start_date > draft.end_date;

  return (
    <section className="space-y-5" aria-labelledby="wage-story-title">
      <div className="rounded-[1.75rem] bg-[#173b2f] p-5 text-white shadow-[0_18px_44px_rgba(23,59,47,0.14)] sm:p-7">
        <div className="flex items-center gap-2 text-[#f1bf68]"><CalendarDays className="h-4 w-4" aria-hidden="true" /><p className="text-sm font-extrabold">आपके रिकॉर्ड, एक जगह</p></div>
        <h2 id="wage-story-title" className="mt-1 text-2xl font-black tracking-tight sm:text-3xl">मेरी मज़दूरी की कहानी</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#d5e2d6]">काम और भुगतान तारीख़ के क्रम में। हर रिकॉर्ड के साथ यह भी दिखेगा कि जानकारी कैसे दर्ज हुई।</p>
        <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.07] p-4"><p className="text-xs font-bold text-[#d5e2d6]">इस अवधि की कमाई</p><p className="mt-1 text-xl font-black">{money(summary?.total_earned || 0)}</p></div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.07] p-4"><p className="text-xs font-bold text-[#d5e2d6]">मिला भुगतान</p><p className="mt-1 text-xl font-black">{money(summary?.total_received || 0)}</p></div>
          <div className="rounded-2xl border border-[#f1bf68]/30 bg-[#f1bf68]/10 p-4"><p className="text-xs font-bold text-[#f5d79e]">बाकी हिसाब</p><p className="mt-1 text-xl font-black">{money(summary?.pending || 0)}</p></div>
        </div>
      </div>

      <form onSubmit={applyFilters} className="grid gap-3 rounded-2xl border border-[#e7e5dc] bg-[#fffefa] p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1.2fr_auto] lg:items-end">
        <label className="text-sm font-bold text-[#34443a]">से
          <input type="date" value={draft.start_date} max={draft.end_date || undefined} onChange={(event) => setDraft((current) => ({ ...current, start_date: event.target.value }))} className="mt-1.5 block min-h-11 w-full rounded-xl border border-[#dfe2d8] bg-white px-3 text-sm font-medium" />
        </label>
        <label className="text-sm font-bold text-[#34443a]">तक
          <input type="date" value={draft.end_date} min={draft.start_date || undefined} onChange={(event) => setDraft((current) => ({ ...current, end_date: event.target.value }))} className="mt-1.5 block min-h-11 w-full rounded-xl border border-[#dfe2d8] bg-white px-3 text-sm font-medium" />
        </label>
        <label className="text-sm font-bold text-[#34443a]">मालिक
          <select value={draft.employer_id} onChange={(event) => setDraft((current) => ({ ...current, employer_id: event.target.value }))} className="mt-1.5 block min-h-11 w-full rounded-xl border border-[#dfe2d8] bg-white px-3 text-sm font-medium">
            <option value="">सभी मालिक</option>
            {employers.map((employer) => <option key={employer.id} value={employer.id}>{employer.name}</option>)}
          </select>
        </label>
        <button type="submit" disabled={invalidRange || loading} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#173b2f] px-5 text-sm font-extrabold text-white transition hover:bg-[#22543f] disabled:cursor-not-allowed disabled:opacity-50"><CalendarDays className="h-4 w-4" aria-hidden="true" />हिसाब देखें</button>
      </form>

      <label className="relative block">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
        <span className="sr-only">इतिहास में खोजें</span>
        <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="मालिक या काम में खोजें" className="min-h-12 w-full rounded-xl border border-[#e7e5dc] bg-[#fffefa] pl-10 pr-4 text-sm outline-none transition placeholder:text-slate-400 focus:border-[#28734e] focus:ring-2 focus:ring-[#28734e]/15" />
      </label>

      <p className="rounded-xl border border-[#e7e5dc] bg-[#f5f4ed] px-4 py-3 text-xs leading-5 text-slate-600">“मज़दूर ने पुष्टि की” का अर्थ है कि आपने दर्ज करने से पहले विवरण की पुष्टि की। यह जानकारी की स्वतंत्र जाँच नहीं है। “बताई गई” जानकारी भी अपने आप में प्रमाणित नहीं मानी जाती।</p>

      {alerts.length > 0 && <section aria-labelledby="ledger-alerts-title" className="space-y-3">
        <div><p className="text-sm font-extrabold text-[#9a6a2b]">आपके रिकॉर्ड पर आधारित</p><h3 id="ledger-alerts-title" className="mt-1 text-xl font-black text-[#173b2f]">जाँचने लायक बातें</h3></div>
        {alerts.map((alert) => <article key={alert.id} className={`rounded-2xl border p-4 sm:p-5 ${alert.severity === 'review' ? 'border-amber-200 bg-amber-50/70' : 'border-[#e7e5dc] bg-[#fffefa]'}`}>
          <div className="flex flex-wrap items-start justify-between gap-2"><div><h4 className="font-extrabold text-[#24352b]">{alert.employer_name || 'मालिक दर्ज नहीं'}</h4><p className="mt-1 text-sm leading-6 text-slate-700">{alert.explanation}</p></div>{alert.amount && <span className="rounded-full bg-white/80 px-3 py-1 text-sm font-black text-[#173b2f]">{money(alert.amount)}</span>}</div>
          <p className="mt-2 text-sm font-semibold text-[#285c3d]">अगला कदम: {alert.recommendation}</p>
          <details className="mt-3 rounded-xl bg-white/70 p-3">
            <summary className="cursor-pointer text-xs font-extrabold text-slate-700">{alert.source_records.length} स्रोत रिकॉर्ड देखें</summary>
            <ul className="mt-2 space-y-2">
              {alert.source_records.map((record) => <li key={record.id} className="flex flex-wrap justify-between gap-2 border-t border-black/5 pt-2 text-xs text-slate-600"><span>{record.record_type === 'work' ? 'काम' : 'भुगतान'} · {new Date(record.date).toLocaleDateString('hi-IN')} · {record.description}</span><span className="font-bold">{money(record.amount)}</span></li>)}
            </ul>
          </details>
          <p className="mt-2 text-[11px] leading-5 text-slate-500">यह संकेत आपके दर्ज रिकॉर्ड से निकला है। MazdoorMitra इसे बदलता नहीं है और वास्तविक भुगतान की स्वतंत्र पुष्टि नहीं करता।</p>
        </article>)}
      </section>}

      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900">{error}</div>}
      {loading ? <div role="status" className="rounded-2xl border border-[#e7e5dc] bg-[#fffefa] p-8 text-center text-sm font-semibold text-slate-600">आपका हिसाब तैयार हो रहा है…</div> : visible.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#d9ddd3] bg-[#fffefa] px-5 py-10 text-center"><Clock3 className="mx-auto h-8 w-8 text-[#9a6a2b]" aria-hidden="true" /><p className="mt-3 font-extrabold text-[#173b2f]">इस अवधि में कोई रिकॉर्ड नहीं मिला</p><p className="mt-1 text-sm text-slate-600">तारीख़ या मालिक बदलकर देखें।</p></div>
      ) : (
        <ol className="space-y-3" aria-label="तारीख़ के क्रम में काम और भुगतान">
          {visible.map((item) => {
            const work = item.type === 'work';
            return <li key={`${item.type}-${item.id}`} className="relative rounded-2xl border border-[#e7e5dc] bg-[#fffefa] p-4 shadow-[0_5px_18px_rgba(40,54,43,0.035)] sm:p-5">
              <div className="flex items-start gap-3">
                <span className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${work ? 'bg-[#e5eee2] text-[#28734e]' : 'bg-[#f4ebdc] text-[#9a6326]'}`}>
                  {work ? <Briefcase className="h-5 w-5" aria-hidden="true" /> : <ArrowDownLeft className="h-5 w-5" aria-hidden="true" />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div><h3 className="font-extrabold text-[#24352b]">{work ? 'काम की कमाई' : item.payment_type === 'advance' ? 'अग्रिम मिला' : 'भुगतान मिला'}</h3><p className="mt-0.5 text-sm text-slate-600">{item.employer_name || 'मालिक दर्ज नहीं'}{item.description ? ` · ${item.description}` : ''}</p></div>
                    <p className={`whitespace-nowrap text-base font-black ${work ? 'text-[#285c3d]' : 'text-[#9a6326]'}`}>{work ? <ArrowUpRight className="mr-1 inline h-4 w-4" aria-hidden="true" /> : <ArrowDownLeft className="mr-1 inline h-4 w-4" aria-hidden="true" />}{money(item.amount)}</p>
                  </div>
                  {work && <p className="mt-2 text-xs leading-5 text-slate-600">{item.wage_basis === 'hourly' ? `${item.hours_worked || 0} घंटे × ${money(item.hourly_rate || 0)}/घंटा${Number(item.overtime_hours || 0) > 0 ? ` · ${item.overtime_hours} घंटे ओवरटाइम (${item.overtime_multiplier || '1.5'}×)` : ''}` : `${item.days_worked || 0} दिन × ${money(item.daily_wage || 0)}/दिन`}</p>}
                  <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs">
                    <span className="font-semibold text-slate-600">{new Date(item.date).toLocaleDateString('hi-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</span>
                    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-bold ${item.record_status === 'worker_confirmed' ? 'bg-[#e8f2e8] text-[#245d39]' : 'bg-[#f4eee1] text-[#855c20]'}`}>
                      {item.record_status === 'worker_confirmed' ? <><CircleCheck className="h-3.5 w-3.5" aria-hidden="true" />आपने पुष्टि की</> : 'आपकी बताई जानकारी'}
                    </span>
                    {item.was_corrected && <span className="rounded-full bg-blue-50 px-2.5 py-1 font-bold text-blue-800">सुधार के बाद दर्ज</span>}
                    {item.confirmed_at && <time dateTime={item.confirmed_at} className="text-slate-500">पुष्टि: {new Date(item.confirmed_at).toLocaleString('hi-IN')}</time>}
                  </div>
                </div>
              </div>
            </li>;
          })}
        </ol>
      )}
      {!loading && transactions.length >= 200 && <p className="text-center text-xs text-slate-500">इस सूची में सबसे नए 200 रिकॉर्ड दिखाए गए हैं। संकरी तारीख़ सीमा चुनें।</p>}
    </section>
  );
}
