'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft, BriefcaseBusiness, CalendarDays, ChevronLeft, ChevronRight,
  Clock3, IndianRupee, MapPin, Pencil, Plus, RotateCw, Save, X,
} from 'lucide-react';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth-context';
import type { AttendanceDay, Employer, WageAgreement, WorkEntry, Worksite } from '../../types';

type WageBasis = 'daily' | 'hourly';
type DiaryForm = {
  work_date: string;
  employer_id: string;
  worksite_id: string;
  wage_basis: WageBasis;
  days_worked: string;
  hours_worked: string;
  daily_wage: string;
  hourly_rate: string;
  overtime_hours: string;
  overtime_multiplier: string;
  description: string;
};

const today = () => {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

const emptyForm = (workDate: string): DiaryForm => ({
  work_date: workDate, employer_id: '', worksite_id: '', wage_basis: 'daily',
  days_worked: '1', hours_worked: '', daily_wage: '', hourly_rate: '',
  overtime_hours: '0', overtime_multiplier: '1.5', description: '',
});

const money = (value: string | number) => new Intl.NumberFormat('hi-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 2,
}).format(Number(value || 0));

export default function DiaryPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [monthDate, setMonthDate] = useState<Date | null>(null);
  const [selectedDate, setSelectedDate] = useState('');
  const [employers, setEmployers] = useState<Employer[]>([]);
  const [entries, setEntries] = useState<WorkEntry[]>([]);
  const [calendar, setCalendar] = useState<AttendanceDay[]>([]);
  const [worksites, setWorksites] = useState<Worksite[]>([]);
  const [agreements, setAgreements] = useState<WageAgreement[]>([]);
  const [form, setForm] = useState<DiaryForm>(() => emptyForm(''));
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pageError, setPageError] = useState('');
  const [formError, setFormError] = useState('');
  const [notice, setNotice] = useState('');
  const [reload, setReload] = useState(0);

  const year = monthDate?.getFullYear() ?? 0;
  const month = monthDate?.getMonth() ?? 0;
  const monthStart = `${year}-${String(month + 1).padStart(2, '0')}-01`;
  const lastDay = new Date(year, month + 1, 0).getDate();
  const monthEnd = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;

  useEffect(() => {
    const initialDate = today();
    // Initialize the browser's local date after hydration; it must not be baked into static prerender output.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMonthDate(new Date(`${initialDate}T12:00:00`));
    setSelectedDate(initialDate);
    setForm(emptyForm(initialDate));
  }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) { router.push('/auth'); return; }
    if (!isAuthenticated || !monthDate) return;
    let active = true;
    Promise.all([
      api.getEmployers(),
      api.getWorkEntries({ start_date: monthStart, end_date: monthEnd }),
      api.getAttendanceCalendar(year, month + 1),
    ]).then(([employerData, workData, calendarData]) => {
      if (!active) return;
      setEmployers(employerData);
      setEntries(workData);
      setCalendar(calendarData);
      setPageError('');
    }).catch(() => {
      if (active) setPageError('काम का हिसाब अभी नहीं खुल पाया। इंटरनेट जाँचकर फिर कोशिश करें।');
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isAuthenticated, authLoading, router, monthDate, monthStart, monthEnd, year, month, reload]);

  useEffect(() => {
    if (!form.employer_id) return;
    let active = true;
    Promise.all([
      api.getWorksites(form.employer_id),
      api.getWageAgreements(form.employer_id),
    ]).then(([siteData, agreementData]) => {
      if (!active) return;
      setWorksites(siteData);
      setAgreements(agreementData);
    }).catch(() => {
      if (active) { setWorksites([]); setAgreements([]); }
    });
    return () => { active = false; };
  }, [form.employer_id]);

  const selectedEntries = useMemo(
    () => entries.filter((entry) => entry.work_date.slice(0, 10) === selectedDate),
    [entries, selectedDate],
  );
  const attendanceByDate = useMemo(
    () => new Map(calendar.map((item) => [item.date, item])),
    [calendar],
  );
  const agreementSuggestion = useMemo(() => agreements
    .filter((agreement) => agreement.effective_from <= form.work_date
      && (!agreement.effective_to || agreement.effective_to >= form.work_date)
      && (agreement.worksite_id === form.worksite_id || (!agreement.worksite_id && !form.worksite_id)))
    .sort((a, b) => b.effective_from.localeCompare(a.effective_from))[0],
  [agreements, form.work_date, form.worksite_id]);

  const changeMonth = (delta: number) => {
    const next = new Date(year, month + delta, 1);
    setMonthDate(next);
    setLoading(true);
    const nextToday = today();
    const nextSelected = nextToday.startsWith(`${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}`)
      ? nextToday
      : `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-01`;
    setSelectedDate(nextSelected);
    setForm(emptyForm(nextSelected));
    setEditingId(null);
  };

  const chooseDate = (date: string) => {
    setSelectedDate(date);
    if (!editingId) setForm((current) => ({ ...current, work_date: date }));
    setNotice('');
  };

  const startEdit = (entry: WorkEntry) => {
    setEditingId(entry.id);
    setSelectedDate(entry.work_date.slice(0, 10));
    setForm({
      work_date: entry.work_date.slice(0, 10),
      employer_id: entry.employer_id || '',
      worksite_id: entry.worksite_id || '',
      wage_basis: entry.wage_basis || 'daily',
      days_worked: entry.days_worked || '1',
      hours_worked: entry.hours_worked || '',
      daily_wage: entry.wage_basis === 'hourly' ? '' : entry.daily_wage || '',
      hourly_rate: entry.hourly_rate || '',
      overtime_hours: entry.overtime_hours || '0',
      overtime_multiplier: entry.overtime_multiplier || '1.5',
      description: entry.description || '',
    });
    setFormError('');
    setNotice('');
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(emptyForm(selectedDate));
    setFormError('');
  };

  const applyAgreement = () => {
    if (!agreementSuggestion) return;
    setForm((current) => ({
      ...current,
      wage_basis: agreementSuggestion.wage_basis,
      daily_wage: agreementSuggestion.daily_rate || '',
      hourly_rate: agreementSuggestion.hourly_rate || '',
      overtime_multiplier: agreementSuggestion.overtime_multiplier || '1.5',
    }));
    setNotice('आपकी दर्ज दर भर दी गई है। सेव करने से पहले रकम जाँच लें।');
  };

  const saveWork = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    setNotice('');
    const payload = {
      work_date: form.work_date,
      employer_id: form.employer_id || undefined,
      worksite_id: form.worksite_id || undefined,
      wage_basis: form.wage_basis,
      days_worked: form.wage_basis === 'hourly' ? '0' : form.days_worked,
      hours_worked: form.wage_basis === 'hourly' ? form.hours_worked : undefined,
      daily_wage: form.wage_basis === 'daily' ? form.daily_wage : undefined,
      hourly_rate: form.wage_basis === 'hourly' ? form.hourly_rate : undefined,
      overtime_hours: form.overtime_hours || '0',
      overtime_multiplier: form.overtime_multiplier || '1.5',
      description: form.description.trim() || undefined,
    };
    try {
      setSaving(true);
      if (editingId) await api.updateWorkEntry(editingId, payload);
      else await api.addWorkEntry(payload);
      setEditingId(null);
      setForm(emptyForm(form.work_date));
      setNotice(editingId ? 'सुधार सुरक्षित हुआ। पुराने और नए हिसाब का रिकॉर्ड रखा गया है।' : 'काम का रिकॉर्ड सुरक्षित हुआ।');
      setReload((value) => value + 1);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'रिकॉर्ड सुरक्षित नहीं हो पाया। दोबारा कोशिश करें।');
    } finally {
      setSaving(false);
    }
  };

  const offset = (new Date(year, month, 1).getDay() + 6) % 7;
  const monthName = monthDate ? new Intl.DateTimeFormat('hi-IN', { month: 'long', year: 'numeric' }).format(monthDate) : '';
  const totalMonthEarnings = calendar.reduce((sum, day) => sum + Number(day.total_earned), 0);

  if (authLoading || !monthDate || (!isAuthenticated && typeof window !== 'undefined')) {
    return <div className="flex min-h-[50vh] items-center justify-center" role="status" aria-label="काम का हिसाब खुल रहा है"><div className="h-9 w-9 animate-spin rounded-full border-4 border-zinc-500 border-t-transparent" /></div>;
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 pb-5 sm:px-6 md:gap-7 md:px-0">
      <header className="flex flex-wrap items-end justify-between gap-4 rounded-[1.6rem] border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
        <div className="flex items-start gap-3">
          <button onClick={() => router.push('/dashboard')} aria-label="हिसाब पर वापस जाएँ" className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-zinc-200 text-zinc-600 hover:bg-zinc-100"><ArrowLeft className="h-4 w-4" /></button>
          <div><p className="text-sm font-bold text-zinc-500">दर्ज काम का कैलेंडर</p><h1 className="mt-1 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl">काम की डायरी</h1><p className="mt-1 max-w-xl text-sm leading-6 text-zinc-600">काम के दिन, तय हुई दर और कमाई अपने पास साफ़ रखें। कैलेंडर सिर्फ़ दर्ज रिकॉर्ड दिखाता है।</p></div>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-2.5"><IndianRupee className="h-4 w-4 text-zinc-500" /><div><p className="text-[11px] font-bold text-zinc-500">इस महीने दर्ज कमाई</p><p className="text-base font-black text-zinc-900">{money(totalMonthEarnings)}</p></div></div>
      </header>

      {pageError && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm font-semibold text-amber-950"><span>{pageError}</span><button onClick={() => { setLoading(true); setReload((value) => value + 1); }} className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-white px-3 font-bold"><RotateCw className="h-4 w-4" />फिर कोशिश करें</button></div>}
      {notice && <p role="status" className="rounded-xl border border-zinc-200 bg-zinc-100 px-4 py-3 text-sm font-semibold text-zinc-800">{notice}</p>}

      <div className="grid items-start gap-5 lg:grid-cols-[1.05fr_0.95fr]">
        <section className="rounded-[1.6rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-6" aria-label="महीने का काम कैलेंडर">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">महीने का रिकॉर्ड</p><h2 className="mt-1 text-xl font-black text-zinc-900">{monthName}</h2></div>
            <div className="flex items-center gap-1"><button onClick={() => changeMonth(-1)} aria-label="पिछला महीना" className="flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-200 hover:bg-zinc-100"><ChevronLeft className="h-4 w-4" /></button><button onClick={() => changeMonth(1)} aria-label="अगला महीना" className="flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-200 hover:bg-zinc-100"><ChevronRight className="h-4 w-4" /></button></div>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center text-xs font-bold text-zinc-500" aria-hidden="true">
            {['सोम', 'मंगल', 'बुध', 'गुरु', 'शुक्र', 'शनि', 'रवि'].map((day) => <span key={day} className="py-2">{day}</span>)}
          </div>
          <div className="grid grid-cols-7 gap-1.5" role="grid" aria-label={monthName}>
            {Array.from({ length: offset }, (_, index) => <span key={`empty-${index}`} aria-hidden="true" />)}
            {Array.from({ length: lastDay }, (_, index) => {
              const day = index + 1;
              const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
              const record = attendanceByDate.get(dateKey);
              const active = selectedDate === dateKey;
              return <button key={dateKey} type="button" role="gridcell" aria-selected={active} aria-label={`${day} ${monthName}${record ? `, ${record.recorded_entries} दर्ज काम` : ', कोई दर्ज काम नहीं'}`} onClick={() => chooseDate(dateKey)} className={`relative flex min-h-[3.35rem] flex-col items-center justify-center rounded-xl text-sm font-bold transition sm:min-h-[4rem] ${active ? 'bg-zinc-900 text-white' : record ? 'bg-zinc-100 text-zinc-900 hover:bg-zinc-200' : 'text-zinc-600 hover:bg-zinc-50'}`}>
                <span>{day}</span>{record && <span className={`mt-0.5 h-1.5 w-1.5 rounded-full ${active ? 'bg-white' : 'bg-zinc-500'}`} aria-hidden="true" />}
              </button>;
            })}
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3 border-t border-zinc-100 pt-4 sm:grid-cols-3">
            <div className="rounded-xl bg-zinc-50 p-3"><p className="text-xs font-semibold text-zinc-500">दर्ज दिन</p><p className="mt-1 text-lg font-black text-zinc-900">{calendar.length}</p></div>
            <div className="rounded-xl bg-zinc-50 p-3"><p className="text-xs font-semibold text-zinc-500">काम के दिन</p><p className="mt-1 text-lg font-black text-zinc-900">{calendar.reduce((sum, day) => sum + Number(day.total_days_worked), 0).toLocaleString('hi-IN')}</p></div>
            <div className="col-span-2 rounded-xl bg-zinc-50 p-3 sm:col-span-1"><p className="text-xs font-semibold text-zinc-500">दर्ज घंटे</p><p className="mt-1 text-lg font-black text-zinc-900">{calendar.reduce((sum, day) => sum + Number(day.total_hours_worked), 0).toLocaleString('hi-IN')}</p></div>
          </div>
          <p className="mt-3 flex items-start gap-2 text-xs leading-5 text-zinc-500"><CalendarDays className="mt-0.5 h-3.5 w-3.5 shrink-0" />खाली तारीख का मतलब यह नहीं कि उस दिन काम नहीं हुआ—उस तारीख का रिकॉर्ड अभी दर्ज नहीं है।</p>
        </section>

        <section className="rounded-[1.6rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-6">
          <div className="mb-4 flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">{new Date(`${selectedDate}T12:00:00`).toLocaleDateString('hi-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</p><h2 className="mt-1 text-xl font-black text-zinc-900">{editingId ? 'काम का सुधार' : 'काम दर्ज करें'}</h2></div>{editingId ? <button onClick={cancelEdit} aria-label="सुधार रद्द करें" className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-200 text-zinc-600"><X className="h-4 w-4" /></button> : <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-zinc-100 text-zinc-700"><BriefcaseBusiness className="h-4 w-4" /></span>}</div>

          <form onSubmit={saveWork} className="space-y-3.5">
            <div className="grid grid-cols-2 gap-2" role="group" aria-label="मज़दूरी की दर का प्रकार">
              <button type="button" onClick={() => setForm((current) => ({ ...current, wage_basis: 'daily' }))} aria-pressed={form.wage_basis === 'daily'} className={`min-h-11 rounded-xl border text-sm font-bold ${form.wage_basis === 'daily' ? 'border-zinc-900 bg-zinc-900 text-white' : 'border-zinc-200 text-zinc-700 hover:bg-zinc-50'}`}>दिन के हिसाब से</button>
              <button type="button" onClick={() => setForm((current) => ({ ...current, wage_basis: 'hourly' }))} aria-pressed={form.wage_basis === 'hourly'} className={`min-h-11 rounded-xl border text-sm font-bold ${form.wage_basis === 'hourly' ? 'border-zinc-900 bg-zinc-900 text-white' : 'border-zinc-200 text-zinc-700 hover:bg-zinc-50'}`}>घंटे के हिसाब से</button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm font-bold text-zinc-700">काम की तारीख<input type="date" required value={form.work_date} onChange={(event) => { const value = event.target.value; setForm((current) => ({ ...current, work_date: value })); setSelectedDate(value); if (value) { const [nextYear, nextMonth] = value.split('-').map(Number); if (nextYear !== year || nextMonth !== month + 1) { setMonthDate(new Date(nextYear, nextMonth - 1, 1)); setLoading(true); } } }} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 bg-white px-3 font-medium focus:border-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-200" /></label>
              <label className="block text-sm font-bold text-zinc-700">मालिक / ठेकेदार<select value={form.employer_id} onChange={(event) => { const employerId = event.target.value; setForm((current) => ({ ...current, employer_id: employerId, worksite_id: '' })); if (!employerId) { setWorksites([]); setAgreements([]); } }} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 bg-white px-3 font-medium focus:border-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-200"><option value="">मालिक चुनें (वैकल्पिक)</option>{employers.map((employer) => <option key={employer.id} value={employer.id}>{employer.name}</option>)}</select></label>
            </div>

            {form.employer_id && <label className="block text-sm font-bold text-zinc-700">काम की जगह <span className="font-normal text-zinc-500">(वैकल्पिक)</span><select value={form.worksite_id} onChange={(event) => setForm((current) => ({ ...current, worksite_id: event.target.value }))} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 bg-white px-3 font-medium focus:border-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-200"><option value="">जगह चुनें</option>{worksites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label>}

            {agreementSuggestion && <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-zinc-200 bg-zinc-50 p-3"><div className="flex items-start gap-2"><MapPin className="mt-0.5 h-4 w-4 text-zinc-500" /><p className="text-xs leading-5 text-zinc-600">इस तारीख के लिए आपकी दर्ज दर: <strong className="text-zinc-900">{money(agreementSuggestion.wage_basis === 'daily' ? agreementSuggestion.daily_rate || 0 : agreementSuggestion.hourly_rate || 0)} / {agreementSuggestion.wage_basis === 'daily' ? 'दिन' : 'घंटा'}</strong></p></div><button type="button" onClick={applyAgreement} className="min-h-9 rounded-lg border border-zinc-300 bg-white px-3 text-xs font-extrabold text-zinc-800 hover:bg-zinc-100">दर भरें</button></div>}

            <div className="grid grid-cols-2 gap-3">
              {form.wage_basis === 'daily' ? <>
                <label className="block text-sm font-bold text-zinc-700">काम के दिन<input type="number" required min="0.01" max="31" step="0.5" inputMode="decimal" value={form.days_worked} onChange={(event) => setForm((current) => ({ ...current, days_worked: event.target.value }))} placeholder="1 या 0.5" className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 font-medium" /></label>
                <label className="block text-sm font-bold text-zinc-700">दैनिक दर (₹)<input type="number" required min="0.01" step="0.01" inputMode="decimal" value={form.daily_wage} onChange={(event) => setForm((current) => ({ ...current, daily_wage: event.target.value }))} placeholder="जैसे 700" className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 font-medium" /></label>
              </> : <>
                <label className="block text-sm font-bold text-zinc-700">कुल घंटे<input type="number" required min="0.01" max="24" step="0.25" inputMode="decimal" value={form.hours_worked} onChange={(event) => setForm((current) => ({ ...current, hours_worked: event.target.value }))} placeholder="जैसे 8" className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 font-medium" /></label>
                <label className="block text-sm font-bold text-zinc-700">घंटे की दर (₹)<input type="number" required min="0.01" step="0.01" inputMode="decimal" value={form.hourly_rate} onChange={(event) => setForm((current) => ({ ...current, hourly_rate: event.target.value }))} placeholder="जैसे 100" className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 font-medium" /></label>
              </>}
            </div>

            {form.wage_basis === 'hourly' && <div className="grid grid-cols-2 gap-3"><label className="block text-sm font-bold text-zinc-700">ओवरटाइम घंटे<input type="number" min="0" max={form.hours_worked || 24} step="0.25" inputMode="decimal" value={form.overtime_hours} onChange={(event) => setForm((current) => ({ ...current, overtime_hours: event.target.value }))} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 font-medium" /></label><label className="block text-sm font-bold text-zinc-700">ओवरटाइम गुणक<input type="number" min="1" max="3" step="0.25" inputMode="decimal" value={form.overtime_multiplier} onChange={(event) => setForm((current) => ({ ...current, overtime_multiplier: event.target.value }))} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 font-medium" /></label></div>}

            <label className="block text-sm font-bold text-zinc-700">काम का छोटा विवरण <span className="font-normal text-zinc-500">(वैकल्पिक)</span><input type="text" maxLength={500} value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder="जैसे ईंट की दीवार बनाना" className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 px-3 font-medium" /></label>
            {formError && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-sm font-semibold text-red-800">{formError}</p>}
            <button type="submit" disabled={saving} className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-zinc-900 px-4 text-sm font-extrabold text-white transition hover:bg-zinc-700 disabled:cursor-wait disabled:opacity-60">{saving ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />सुरक्षित हो रहा है…</> : editingId ? <><Save className="h-4 w-4" />सुधार सुरक्षित करें</> : <><Plus className="h-4 w-4" />काम सुरक्षित करें</>}</button>
          </form>
        </section>
      </div>

      <section className="rounded-[1.6rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-6" aria-labelledby="day-records-title">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">दर्ज जानकारी</p><h2 id="day-records-title" className="mt-1 text-xl font-black text-zinc-900">इस तारीख के काम</h2></div><span className="rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-bold text-zinc-700">{selectedEntries.length} रिकॉर्ड</span></div>
        {loading ? <div role="status" className="space-y-2"><div className="h-16 animate-pulse rounded-xl bg-zinc-100" /><div className="h-16 animate-pulse rounded-xl bg-zinc-100" /></div> : selectedEntries.length === 0 ? <div className="rounded-xl border border-dashed border-zinc-300 bg-zinc-50 px-4 py-7 text-center"><Clock3 className="mx-auto h-6 w-6 text-zinc-500" /><p className="mt-2 text-sm font-bold text-zinc-800">इस तारीख का कोई काम दर्ज नहीं है</p><p className="mt-1 text-xs text-zinc-500">अगर काम किया था, ऊपर से रिकॉर्ड जोड़ें।</p></div> : <ul className="divide-y divide-zinc-100">{selectedEntries.map((entry) => <li key={entry.id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"><div className="min-w-0"><p className="truncate text-sm font-extrabold text-zinc-900">{entry.employer_name || 'मालिक दर्ज नहीं'}{entry.worksite_name ? ` · ${entry.worksite_name}` : ''}</p><p className="mt-0.5 text-xs text-zinc-500">{entry.wage_basis === 'hourly' ? `${entry.hours_worked || 0} घंटे × ${money(entry.hourly_rate || 0)}` : `${entry.days_worked} दिन × ${money(entry.daily_wage)}`}{entry.description ? ` · ${entry.description}` : ''}</p></div><div className="flex items-center gap-2"><span className="mr-1 text-sm font-black text-zinc-900">{money(entry.total_earned)}</span><button type="button" onClick={() => startEdit(entry)} aria-label={`${entry.employer_name || 'काम'} का रिकॉर्ड सुधारें`} className="inline-flex min-h-10 items-center gap-1.5 rounded-lg border border-zinc-200 px-3 text-xs font-bold text-zinc-700 hover:bg-zinc-50"><Pencil className="h-3.5 w-3.5" /><span className="hidden sm:inline">सुधारें</span></button></div></li>)}</ul>}
      </section>
    </div>
  );
}
