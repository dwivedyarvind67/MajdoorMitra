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

  const fetchEmployers = useCallback(async () => {
    try {
      const summary = await api.getLedgerSummary();
      setEmployers(summary.employers || []);
    } catch (err) {
      console.error(err);
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
        if (active) setEmployers(summary.employers || []);
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

  const handleAddEmployer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    try {
      await api.addEmployer({ name: name.trim(), contact_details: contact.trim() });
      setName('');
      setContact('');
      setShowAddForm(false);
      await fetchEmployers();
    } catch (err: unknown) {
      setLoading(false);
      alert(err instanceof Error ? err.message : 'मालिक जोड़ने में समस्या हुई।');
    }
  };

  return (
    <div className="flex flex-col px-5 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/dashboard')}
            className="p-2 -ml-2 text-slate-600 hover:text-slate-900 rounded-full hover:bg-slate-100 transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-black text-slate-900">मालिक / ठेकेदार</h1>
            <p className="text-xs text-slate-500">अलग-अलग ठेकेदारों का हिसाब</p>
          </div>
        </div>

        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="p-2 bg-blue-600 text-white rounded-xl shadow hover:bg-blue-700 transition"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      {/* Add Employer Modal / Form */}
      {showAddForm && (
        <form
          onSubmit={handleAddEmployer}
          className="p-4 bg-blue-50 border border-blue-200 rounded-2xl space-y-3"
        >
          <h3 className="text-xs font-bold text-blue-900 uppercase">
            नया ठेकेदार जोड़ें
          </h3>
          <input
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ठेकेदार या मालिक का नाम"
            className="w-full bg-white border border-blue-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="tel"
            value={contact}
            onChange={(e) => setContact(e.target.value)}
            placeholder="मोबाइल नंबर (वैकल्पिक)"
            className="w-full bg-white border border-blue-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="flex-1 py-2 bg-blue-600 text-white font-bold rounded-xl text-xs shadow hover:bg-blue-700 transition"
            >
              सेव करें
            </button>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 bg-slate-200 text-slate-700 font-bold rounded-xl text-xs hover:bg-slate-300 transition"
            >
              रद्द
            </button>
          </div>
        </form>
      )}

      {/* Employers List */}
      <div className="space-y-3">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-24 bg-slate-100 rounded-2xl animate-pulse"></div>
            ))}
          </div>
        ) : employers.length === 0 ? (
          <div className="p-8 text-center bg-white rounded-2xl border border-dashed border-slate-200 text-slate-400">
            <Users className="w-10 h-10 mx-auto mb-2 opacity-40" />
            <p className="text-sm font-semibold">कोई ठेकेदार नहीं मिला</p>
            <p className="text-xs text-slate-400 mt-1">
              जब आप बोलकर रिकॉर्ड करेंगे, तो ठेकेदार का नाम अपने आप जुड़ जाएगा।
            </p>
          </div>
        ) : (
          employers.map((emp) => <EmployerCard key={emp.employer_id} summary={emp} />)
        )}
      </div>
    </div>
  );
}
