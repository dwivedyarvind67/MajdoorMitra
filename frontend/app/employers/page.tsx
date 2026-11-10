'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth-context';
import { api } from '../../lib/api';
import EmployerCard from '../../components/EmployerCard';
import { Employer, EmployerSummary, WageAgreement, Worksite } from '../../types';
import { Users, Plus, ArrowLeft, BriefcaseBusiness, CalendarDays, IndianRupee, MapPin } from 'lucide-react';

const money = (value: string | number) => new Intl.NumberFormat('hi-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 2,
}).format(Number(value || 0));

export default function EmployersPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [employers, setEmployers] = useState<EmployerSummary[]>([]);
  const [employerRecords, setEmployerRecords] = useState<Employer[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [selectedEmployerId, setSelectedEmployerId] = useState<string | null>(null);
  const [worksites, setWorksites] = useState<Worksite[]>([]);
  const [agreements, setAgreements] = useState<WageAgreement[]>([]);
  const [detailError, setDetailError] = useState('');
  const [detailBusy, setDetailBusy] = useState(false);
  const [showSiteForm, setShowSiteForm] = useState(false);
  const [showRateForm, setShowRateForm] = useState(false);
  const [siteName, setSiteName] = useState('');
  const [siteAddress, setSiteAddress] = useState('');
  const [rateBasis, setRateBasis] = useState<'daily' | 'hourly'>('daily');
  const [rateValue, setRateValue] = useState('');
  const [rateSite, setRateSite] = useState('');
  const [rateFrom, setRateFrom] = useState('');
  const [rateTo, setRateTo] = useState('');
  const [rateTerms, setRateTerms] = useState('');

  const fetchEmployers = useCallback(async () => {
    try {
      const [summary, employerData] = await Promise.all([api.getLedgerSummary(), api.getEmployers()]);
      setEmployers(summary.employers || []);
      setEmployerRecords(employerData);
      setListError(null);
    } catch {
      setListError('ठेकेदारों की सूची अभी नहीं खुल पाई। फिर कोशिश करें।');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth');
      return;
    }
    if (!isAuthenticated) return;

    let active = true;
    Promise.all([api.getLedgerSummary(), api.getEmployers()])
      .then(([summary, employerData]) => {
        if (!active) return;
        setEmployers(summary.employers || []);
        setEmployerRecords(employerData);
        setListError(null);
      })
      .catch(() => { if (active) setListError('ठेकेदारों की सूची अभी नहीं खुल पाई। फिर कोशिश करें।'); })
      .finally(() => { if (active) setLoading(false); });
    return () => {
      active = false;
    };
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    if (!selectedEmployerId) return;
    let active = true;
    Promise.all([api.getWorksites(selectedEmployerId), api.getWageAgreements(selectedEmployerId)])
      .then(([siteData, agreementData]) => {
        if (!active) return;
        setWorksites(siteData);
        setAgreements(agreementData);
        setDetailError('');
      })
      .catch(() => { if (active) setDetailError('ठेकेदार की जगह और दर अभी नहीं खुल पाई। फिर कोशिश करें।'); })
      .finally(() => { if (active) setDetailBusy(false); });
    return () => { active = false; };
  }, [selectedEmployerId]);

  const handleAddEmployer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setFormError(null);
    setLoading(true);
    try {
      await api.addEmployer({ name: name.trim(), contact_details: contact.trim() });
      setName('');
      setContact('');
      setShowAddForm(false);
      await fetchEmployers();
    } catch (err: unknown) {
      setLoading(false);
      setFormError(err instanceof Error ? err.message : 'मालिक जोड़ने में समस्या हुई।');
    }
  };

  const handleAddSite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEmployerId || !siteName.trim()) return;
    setDetailError('');
    try {
      await api.addWorksite(selectedEmployerId, { name: siteName.trim(), address: siteAddress.trim() || undefined });
      setSiteName(''); setSiteAddress(''); setShowSiteForm(false);
      const updated = await api.getWorksites(selectedEmployerId); setWorksites(updated);
    } catch (error) { setDetailError(error instanceof Error ? error.message : 'काम की जगह सुरक्षित नहीं हुई।'); }
  };

  const handleAddRate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEmployerId || !rateValue.trim()) return;
    setDetailError('');
    try {
      await api.addWageAgreement(selectedEmployerId, {
        wage_basis: rateBasis,
        daily_rate: rateBasis === 'daily' ? rateValue : undefined,
        hourly_rate: rateBasis === 'hourly' ? rateValue : undefined,
        worksite_id: rateSite || undefined,
        effective_from: rateFrom,
        effective_to: rateTo || undefined,
        terms: rateTerms.trim() || undefined,
      });
      setRateValue(''); setRateTerms(''); setRateTo(''); setShowRateForm(false);
      const updated = await api.getWageAgreements(selectedEmployerId); setAgreements(updated);
    } catch (error) { setDetailError(error instanceof Error ? error.message : 'मज़दूरी की दर सुरक्षित नहीं हुई।'); }
  };

  const selectedEmployer = employerRecords.find((employer) => employer.id === selectedEmployerId);
  const openEmployerDetails = (employerId: string) => {
    setDetailBusy(true);
    setDetailError('');
    setSelectedEmployerId(employerId);
  };
  const toggleRateForm = () => {
    if (!showRateForm && !rateFrom) {
      const now = new Date();
      setRateFrom(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`);
    }
    setShowRateForm((value) => !value);
  };

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-5 pb-4 sm:px-7 md:px-0">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/dashboard')}
            className="-ml-2 flex h-11 w-11 items-center justify-center rounded-xl border border-[#e4e4e7] bg-[#ffffff] text-slate-600 transition hover:text-[#27272a]"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <p className="text-sm font-extrabold text-[#71717a]">आपके काम की जगहें</p>
            <h1 className="text-2xl font-black tracking-tight text-[#27272a] sm:text-3xl">मालिक और ठेकेदार</h1>
          </div>
        </div>

        <button
          onClick={() => setShowAddForm(!showAddForm)}
          aria-label="नया मालिक या ठेकेदार जोड़ें"
          className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#27272a] text-white shadow-sm transition hover:bg-[#3f3f46]"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      {/* Add Employer Modal / Form */}
      {showAddForm && (
        <form
          onSubmit={handleAddEmployer}
          className="space-y-4 rounded-[1.75rem] border border-[#e4e4e7] bg-[#ffffff] p-5 shadow-sm sm:p-6"
        >
          <h3 className="text-lg font-black text-[#27272a]">
            नया ठेकेदार जोड़ें
          </h3>
          {formError && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-900">{formError}</p>}
          <label htmlFor="employer-name" className="block text-sm font-bold text-slate-800">नाम</label>
          <input
            id="employer-name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ठेकेदार या मालिक का नाम"
            className="min-h-12 w-full rounded-xl border border-[#e4e4e7] bg-[#fafafa] px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-[#52525b]"
          />
          <label htmlFor="employer-contact" className="block text-sm font-bold text-slate-800">मोबाइल नंबर <span className="font-medium text-slate-500">(वैकल्पिक)</span></label>
          <input
            id="employer-contact"
            type="tel"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            placeholder="मोबाइल नंबर (वैकल्पिक)"
            className="min-h-12 w-full rounded-xl border border-[#e4e4e7] bg-[#fafafa] px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-[#52525b]"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="min-h-12 flex-1 rounded-xl bg-[#27272a] px-4 py-3 text-base font-extrabold text-white shadow-sm transition hover:bg-[#3f3f46]"
            >
              {loading ? 'सेव हो रहा है…' : 'सेव करें'}
            </button>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="min-h-12 rounded-xl border border-[#e4e4e7] bg-white px-5 text-base font-bold text-slate-700 transition hover:bg-slate-50"
            >
              रद्द
            </button>
          </div>
        </form>
      )}

      {/* Employers List */}
      <div className="space-y-3">
        {listError && <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm font-semibold text-amber-950"><span>{listError}</span><button onClick={() => { setLoading(true); void fetchEmployers(); }} className="min-h-10 rounded-lg bg-white px-3 font-extrabold">फिर कोशिश करें</button></div>}
        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 animate-pulse rounded-3xl border border-[#e4e4e7] bg-[#ffffff]"></div>
            ))}
          </div>
        ) : employers.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-[#e4e4e7] bg-[#ffffff] px-6 py-10 text-center text-slate-600">
            <Users className="mx-auto mb-3 h-10 w-10 text-[#52525b]" />
            <p className="text-base font-bold text-[#27272a]">अभी कोई मालिक दर्ज नहीं</p>
            <p className="mx-auto mt-1 max-w-md text-sm leading-6">नाम बोलकर रिकॉर्ड करें या मालिक को खुद जोड़ें। हर मालिक का हिसाब अलग रहेगा।</p>
            <button type="button" onClick={() => setShowAddForm(true)} className="mt-5 min-h-11 rounded-xl bg-[#27272a] px-4 text-sm font-bold text-white">पहला मालिक जोड़ें</button>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">{employers.map((emp) => <EmployerCard key={emp.employer_id} summary={emp} onManage={openEmployerDetails} />)}</div>
        )}
      </div>

      {selectedEmployerId && selectedEmployer && <section className="rounded-[1.75rem] border border-zinc-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="employer-detail-title">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-100 pb-4"><div><p className="text-sm font-bold text-zinc-500">मालिक की जानकारी</p><h2 id="employer-detail-title" className="mt-1 text-xl font-black text-zinc-900">{selectedEmployer.name}</h2><p className="mt-1 text-xs text-zinc-500">ये दरें आपके बताए हुए रिकॉर्ड हैं। इन्हें स्वतंत्र रूप से सत्यापित नहीं किया गया है।</p></div><button onClick={() => { setSelectedEmployerId(null); setDetailBusy(false); }} className="min-h-10 rounded-lg border border-zinc-200 px-3 text-sm font-bold text-zinc-600 hover:bg-zinc-50">बंद करें</button></div>
        {detailError && <div role="alert" className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm font-semibold text-amber-950"><span>{detailError}</span><button onClick={() => { const id = selectedEmployerId; void Promise.all([api.getWorksites(id), api.getWageAgreements(id)]).then(([sites, rates]) => { setWorksites(sites); setAgreements(rates); setDetailError(''); }).catch(() => {}); }} className="min-h-9 rounded-lg bg-white px-3 font-bold">फिर कोशिश करें</button></div>}
        {detailBusy ? <div role="status" className="mt-5 grid gap-3 sm:grid-cols-2"><div className="h-28 animate-pulse rounded-xl bg-zinc-100" /><div className="h-28 animate-pulse rounded-xl bg-zinc-100" /></div> : <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <div className="rounded-2xl border border-zinc-200 p-4 sm:p-5"><div className="flex items-center justify-between gap-2"><div className="flex items-center gap-2"><BriefcaseBusiness className="h-4 w-4 text-zinc-500" /><h3 className="font-extrabold text-zinc-900">काम की जगहें</h3></div><button onClick={() => setShowSiteForm((value) => !value)} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-zinc-200 px-3 text-xs font-bold text-zinc-700 hover:bg-zinc-50"><Plus className="h-3.5 w-3.5" />जगह जोड़ें</button></div>
            {showSiteForm && <form onSubmit={handleAddSite} className="mt-4 space-y-2 rounded-xl bg-zinc-50 p-3"><label className="block text-xs font-bold text-zinc-700">जगह का नाम<input required maxLength={255} value={siteName} onChange={(e) => setSiteName(e.target.value)} placeholder="जैसे सेक्टर 18 साइट" className="mt-1 min-h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm" /></label><label className="block text-xs font-bold text-zinc-700">पता (वैकल्पिक)<input maxLength={500} value={siteAddress} onChange={(e) => setSiteAddress(e.target.value)} className="mt-1 min-h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm" /></label><button className="min-h-10 rounded-lg bg-zinc-900 px-4 text-sm font-bold text-white">जगह सुरक्षित करें</button></form>}
            {worksites.length ? <ul className="mt-4 divide-y divide-zinc-100">{worksites.map((site) => <li key={site.id} className="flex items-start gap-2 py-3 first:pt-0 last:pb-0"><MapPin className="mt-0.5 h-4 w-4 shrink-0 text-zinc-500" /><div><p className="text-sm font-bold text-zinc-900">{site.name}</p>{site.address && <p className="mt-0.5 text-xs text-zinc-500">{site.address}</p>}</div></li>)}</ul> : !showSiteForm && <p className="mt-4 text-sm text-zinc-500">अभी कोई जगह दर्ज नहीं है।</p>}
          </div>
          <div className="rounded-2xl border border-zinc-200 p-4 sm:p-5"><div className="flex items-center justify-between gap-2"><div className="flex items-center gap-2"><IndianRupee className="h-4 w-4 text-zinc-500" /><h3 className="font-extrabold text-zinc-900">तय मज़दूरी दरें</h3></div><button onClick={toggleRateForm} className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-zinc-200 px-3 text-xs font-bold text-zinc-700 hover:bg-zinc-50"><Plus className="h-3.5 w-3.5" />दर जोड़ें</button></div>
            {showRateForm && <form onSubmit={handleAddRate} className="mt-4 space-y-2 rounded-xl bg-zinc-50 p-3"><div className="grid grid-cols-2 gap-2"><label className="block text-xs font-bold text-zinc-700">दर का प्रकार<select value={rateBasis} onChange={(e) => setRateBasis(e.target.value as 'daily' | 'hourly')} className="mt-1 min-h-10 w-full rounded-lg border border-zinc-200 bg-white px-2 text-sm"><option value="daily">रोज़ाना</option><option value="hourly">प्रति घंटा</option></select></label><label className="block text-xs font-bold text-zinc-700">दर (₹)<input required type="number" min="0.01" step="0.01" value={rateValue} onChange={(e) => setRateValue(e.target.value)} className="mt-1 min-h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm" /></label></div><label className="block text-xs font-bold text-zinc-700">काम की जगह (वैकल्पिक)<select value={rateSite} onChange={(e) => setRateSite(e.target.value)} className="mt-1 min-h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm"><option value="">सभी जगहों के लिए</option>{worksites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><div className="grid grid-cols-2 gap-2"><label className="block text-xs font-bold text-zinc-700">लागू तारीख<input type="date" required value={rateFrom} onChange={(e) => setRateFrom(e.target.value)} className="mt-1 min-h-10 w-full rounded-lg border border-zinc-200 bg-white px-2 text-sm" /></label><label className="block text-xs font-bold text-zinc-700">अंतिम तारीख<input type="date" value={rateTo} min={rateFrom} onChange={(e) => setRateTo(e.target.value)} className="mt-1 min-h-10 w-full rounded-lg border border-zinc-200 bg-white px-2 text-sm" /></label></div><label className="block text-xs font-bold text-zinc-700">शर्तें / नोट<input maxLength={2000} value={rateTerms} onChange={(e) => setRateTerms(e.target.value)} className="mt-1 min-h-10 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm" /></label><button className="min-h-10 rounded-lg bg-zinc-900 px-4 text-sm font-bold text-white">दर सुरक्षित करें</button></form>}
            {agreements.length ? <ul className="mt-4 divide-y divide-zinc-100">{agreements.map((agreement) => <li key={agreement.id} className="flex items-start justify-between gap-3 py-3 first:pt-0 last:pb-0"><div><p className="text-sm font-bold text-zinc-900">{money(agreement.wage_basis === 'daily' ? agreement.daily_rate || 0 : agreement.hourly_rate || 0)} / {agreement.wage_basis === 'daily' ? 'दिन' : 'घंटा'}</p><p className="mt-0.5 text-xs text-zinc-500">{worksites.find((site) => site.id === agreement.worksite_id)?.name || 'सभी जगहें'} · {new Date(`${agreement.effective_from}T12:00:00`).toLocaleDateString('hi-IN')}{agreement.effective_to ? ` से ${new Date(`${agreement.effective_to}T12:00:00`).toLocaleDateString('hi-IN')}` : ' से आगे'}</p>{agreement.terms && <p className="mt-1 text-xs text-zinc-600">{agreement.terms}</p>}</div><CalendarDays className="h-4 w-4 shrink-0 text-zinc-400" /></li>)}</ul> : !showRateForm && <p className="mt-4 text-sm text-zinc-500">अभी कोई दर दर्ज नहीं है।</p>}
          </div>
        </div>}
      </section>}
    </div>
  );
}
