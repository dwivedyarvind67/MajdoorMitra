'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Mic, ArrowRight, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../lib/auth-context';
import { api } from '../lib/api';
import WageSummary from '../components/WageSummary';
import { LedgerSummary } from '../types';

export default function HomePage() {
  const { isAuthenticated, workerName } = useAuth();
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isAuthenticated) {
      api
        .getLedgerSummary()
        .then((data) => setSummary(data))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [isAuthenticated]);

  return (
    <div className="flex flex-col min-h-full px-5 py-6 space-y-6">
      {/* Header & Branding */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-extrabold text-lg shadow">
              M
            </div>
            <h1 className="text-2xl font-black tracking-tight text-blue-900">
              MazdoorMitra
            </h1>
          </div>
          <p className="text-xs font-semibold text-slate-500 mt-0.5">
            आपका काम। आपकी मज़दूरी। आपका रिकॉर्ड।
          </p>
        </div>

        {!isAuthenticated && (
          <Link
            href="/auth"
            className="text-xs font-bold bg-blue-600 text-white px-3.5 py-1.5 rounded-full shadow hover:bg-blue-700 transition"
          >
            लॉग इन
          </Link>
        )}
      </div>

      {/* Greeting Banner */}
      <div className="bg-gradient-to-br from-blue-700 to-indigo-800 text-white p-5 rounded-3xl shadow-lg relative overflow-hidden">
        <div className="relative z-10">
          <span className="text-xs font-bold bg-white/20 px-2.5 py-1 rounded-full text-blue-100">
            {isAuthenticated ? 'नमस्ते' : 'स्वागत है'}
          </span>
          <h2 className="text-xl font-black mt-2 leading-snug">
            {isAuthenticated ? `${workerName} जी` : 'दैनिक मज़दूरों का सच्चा साथी'}
          </h2>
          <p className="text-xs text-blue-100 mt-1.5 leading-relaxed">
            बोलकर अपनी दिहाड़ी और मिला हुआ पैसा दर्ज करें। हिसाब अपने आप तैयार होगा।
          </p>
        </div>
        <div className="absolute -bottom-6 -right-6 w-28 h-28 bg-white/10 rounded-full blur-xl pointer-events-none"></div>
      </div>

      {/* Main Big Voice Action Button */}
      <div className="bg-white border border-slate-100 shadow-sm rounded-3xl p-6 text-center space-y-4">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
          एक क्लिक में रिकॉर्ड करें
        </span>

        <div className="flex justify-center">
          <Link
            href="/voice"
            className="group relative w-32 h-32 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex flex-col items-center justify-center text-white shadow-xl hover:scale-105 active:scale-95 transition-all duration-300"
          >
            <div className="absolute inset-0 rounded-full bg-blue-400 opacity-20 animate-ping group-hover:opacity-40"></div>
            <Mic className="w-14 h-14" />
            <span className="text-xs font-bold mt-1">बोलें</span>
          </Link>
        </div>

        <p className="text-xs text-slate-500 font-medium">
          &ldquo;मैंने 6 दिन काम किया, 700 रुपये रोज़ के...&rdquo;
        </p>
      </div>

      {/* Financial Summary if authenticated */}
      {isAuthenticated ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-800">आपका हिसाब-किताब</h3>
            <Link
              href="/dashboard"
              className="text-xs font-bold text-blue-600 flex items-center gap-1 hover:underline"
            >
              विस्तार देखें <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <WageSummary summary={summary} isLoading={loading} />
        </div>
      ) : (
        /* Features List for Unauthenticated */
        <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100 space-y-3">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            MazdoorMitra के फ़ायदे
          </h4>
          <div className="space-y-2 text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>बिना लिखे सिर्फ बोलकर काम और पैसे का हिसाब</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>ठेकेदार-वार बकाया और एडवांस की सही गणना</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>सबूत के लिए डाउनलोड करने योग्य PDF पर्ची</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
