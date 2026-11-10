'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth-context';
import { api } from '../../lib/api';
import EmployerCard from '../../components/EmployerCard';
import { EmployerSummary } from '../../types';
import { Users, Plus, ArrowLeft } from 'lucide-react';

export default function EmployersPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [employers, setEmployers] = useState<EmployerSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [name, setName] = useState('');
  const [contact, setContact] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  const fetchEmployers = useCallback(async () => {
    try {
      const summary = await api.getLedgerSummary();
      setEmployers(summary.employers || []);
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
    api.getLedgerSummary()
      .then((summary) => {
        if (active) { setEmployers(summary.employers || []); setListError(null); }
      })
      .catch(() => { if (active) setListError('ठेकेदारों की सूची अभी नहीं खुल पाई। फिर कोशिश करें।'); })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isAuthenticated, authLoading, router]);

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

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-5 pb-4 sm:px-7 md:px-0">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/dashboard')}
            className="-ml-2 flex h-11 w-11 items-center justify-center rounded-xl border border-[#e7e5dc] bg-[#fffefa] text-slate-600 transition hover:text-[#173b2f]"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <p className="text-sm font-extrabold text-[#9a6a2b]">आपके काम की जगहें</p>
            <h1 className="text-2xl font-black tracking-tight text-[#173b2f] sm:text-3xl">मालिक और ठेकेदार</h1>
          </div>
        </div>

        <button
          onClick={() => setShowAddForm(!showAddForm)}
          aria-label="नया मालिक या ठेकेदार जोड़ें"
          className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#173b2f] text-white shadow-sm transition hover:bg-[#22543f]"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      {/* Add Employer Modal / Form */}
      {showAddForm && (
        <form
          onSubmit={handleAddEmployer}
          className="space-y-4 rounded-[1.75rem] border border-[#dce5d8] bg-[#fffefa] p-5 shadow-sm sm:p-6"
        >
          <h3 className="text-lg font-black text-[#173b2f]">
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
            className="min-h-12 w-full rounded-xl border border-[#d8ddd4] bg-[#fafaf6] px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-[#28734e]"
          />
          <label htmlFor="employer-contact" className="block text-sm font-bold text-slate-800">मोबाइल नंबर <span className="font-medium text-slate-500">(वैकल्पिक)</span></label>
          <input
            id="employer-contact"
            type="tel"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            placeholder="मोबाइल नंबर (वैकल्पिक)"
            className="min-h-12 w-full rounded-xl border border-[#d8ddd4] bg-[#fafaf6] px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-[#28734e]"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="min-h-12 flex-1 rounded-xl bg-[#173b2f] px-4 py-3 text-base font-extrabold text-white shadow-sm transition hover:bg-[#22543f]"
            >
              {loading ? 'सेव हो रहा है…' : 'सेव करें'}
            </button>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="min-h-12 rounded-xl border border-[#dddcd3] bg-white px-5 text-base font-bold text-slate-700 transition hover:bg-slate-50"
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
              <div key={i} className="h-32 animate-pulse rounded-3xl border border-[#e7e5dc] bg-[#fffefa]"></div>
            ))}
          </div>
        ) : employers.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-[#d9ddd3] bg-[#fffefa] px-6 py-10 text-center text-slate-600">
            <Users className="mx-auto mb-3 h-10 w-10 text-[#28734e]" />
            <p className="text-base font-bold text-[#173b2f]">अभी कोई मालिक दर्ज नहीं</p>
            <p className="mx-auto mt-1 max-w-md text-sm leading-6">नाम बोलकर रिकॉर्ड करें या मालिक को खुद जोड़ें। हर मालिक का हिसाब अलग रहेगा।</p>
            <button type="button" onClick={() => setShowAddForm(true)} className="mt-5 min-h-11 rounded-xl bg-[#173b2f] px-4 text-sm font-bold text-white">पहला मालिक जोड़ें</button>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">{employers.map((emp) => <EmployerCard key={emp.employer_id} summary={emp} />)}</div>
        )}
      </div>
    </div>
  );
}
