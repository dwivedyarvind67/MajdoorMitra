'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth-context';
import { api } from '../../lib/api';
import { Download, ArrowLeft, ShieldCheck } from 'lucide-react';
import { StatementListItem } from '../../types';

export default function StatementsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, workerName } = useAuth();

  const [statements, setStatements] = useState<StatementListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const downloadPdf = async (id: string) => {
    setDownloadingId(id);
    setPdfError(null);
    try {
      const blob = await api.downloadStatementPdf(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `wage_statement_${id.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      setPdfError(error instanceof Error ? error.message : 'PDF डाउनलोड नहीं हो पाया।');
    } finally {
      setDownloadingId(null);
    }
  };

  const latestConfirmed = statements.find((statement) => statement.status === 'CONFIRMED');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/auth');
      return;
    }

    if (isAuthenticated) {
      api
        .getStatements()
        .then((data) => setStatements(data || []))
        .catch(() => setListError('आपके पुराने रिकॉर्ड अभी नहीं खुल पाए। कृपया पृष्ठ फिर से खोलें।'))
        .finally(() => setLoading(false));
    }
  }, [isAuthenticated, authLoading, router]);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-5 pb-4 sm:px-7 md:px-0">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push('/dashboard')}
          aria-label="डैशबोर्ड पर वापस जाएँ"
          className="-ml-2 flex h-11 w-11 items-center justify-center rounded-xl border border-[#e7e5dc] bg-[#fffefa] text-slate-600 transition hover:text-[#173b2f]"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <p className="text-sm font-extrabold text-[#9a6a2b]">आपके रिकॉर्ड की प्रति</p>
          <h1 className="text-2xl font-black tracking-tight text-[#173b2f] sm:text-3xl">मज़दूरी पर्ची</h1>
        </div>
      </div>

      {/* Main Statement Card */}
      <div className="space-y-5 rounded-[1.75rem] bg-[#173b2f] p-5 text-white shadow-[0_18px_44px_rgba(23,59,47,0.16)] sm:p-7">
        <div className="flex items-center justify-between">
          <span className="rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-extrabold text-[#f1bf68]">
            आपकी पुष्टि का रिकॉर्ड
          </span>
          <ShieldCheck className="h-6 w-6 text-[#8fca9a]" />
        </div>

        <div>
          <h3 className="text-lg font-black">{workerName || 'मज़दूर साथी'}</h3>
            <p className="mt-2 text-base leading-7 text-[#d5e2d6]">
            इसमें आपके बताए और पुष्टि किए गए रिकॉर्ड व हिसाब शामिल हैं। MazdoorMitra ने जानकारी की स्वतंत्र जाँच नहीं की है।
          </p>
        </div>

        <div className="pt-2">
          {latestConfirmed ? (
            <button
              type="button"
              onClick={() => void downloadPdf(latestConfirmed.id)}
              disabled={!!downloadingId}
              className="flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-[#f1bf68] px-4 py-3 text-base font-extrabold text-[#26321f] shadow transition hover:bg-[#f8cf83] disabled:cursor-wait disabled:opacity-60"
            >
              <Download className="w-4 h-4" />
              {downloadingId === latestConfirmed.id ? 'PDF तैयार हो रही है…' : 'पुष्टि की गई PDF पर्ची डाउनलोड करें'}
            </button>
          ) : (
            <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-center text-sm text-[#d5e2d6]">
              पुष्टि किया गया रिकॉर्ड बनने के बाद PDF यहाँ उपलब्ध होगी।
            </div>
          )}
          {pdfError && <p role="alert" className="rounded-xl border border-red-200/30 bg-red-950/20 p-3 text-sm text-red-100">{pdfError}</p>}
        </div>
      </div>

      {/* Legal Disclaimer */}
      <div className="space-y-1 rounded-2xl border border-[#e7e5dc] bg-[#fffefa] p-4 text-slate-600">
        <span className="text-sm font-extrabold text-[#173b2f]">जानकारी के बारे में</span>
        <p className="text-sm leading-6">
          यह मज़दूर द्वारा बताई गई और उसकी पुष्टि की गई जानकारी का रिकॉर्ड है। काम, समय, मज़दूरी या भुगतान की स्वतंत्र जाँच नहीं हुई है। यह कानूनी सलाह नहीं है।
        </p>
      </div>

      {/* Voice Statements History */}
      <div className="space-y-3 pt-1">
        <div><p className="text-sm font-extrabold text-[#9a6a2b]">आवाज़ से दर्ज</p><h2 className="mt-1 text-xl font-black text-[#173b2f]">आपके बयान</h2></div>
        {listError && <p role="alert" className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm font-semibold text-amber-950">{listError}</p>}

        {statements.length === 0 ? (
          loading ? (
            <div role="status" className="text-center py-6 text-sm text-slate-500">रिकॉर्ड लोड हो रहे हैं…</div>
          ) : (
            <div className="text-center py-6 text-sm text-slate-500">कोई पुराना वक्तव्य उपलब्ध नहीं है।</div>
          )
        ) : (
          <div className="space-y-2">
            {statements.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between gap-3 rounded-2xl border border-[#e7e5dc] bg-[#fffefa] p-4 shadow-[0_6px_20px_rgba(40,54,43,0.035)] sm:p-5"
              >
                <div>
                  <p className="line-clamp-2 text-base font-semibold leading-6 text-[#25372c]">
                    &ldquo;{s.transcript || 'रिकॉर्डिंग'}&rdquo;
                  </p>
                    <span className="mt-1 block text-xs leading-5 text-slate-600 sm:text-sm">
                    शुरू: {new Date(s.created_at).toLocaleString('hi-IN')} • स्थिति:{' '}
                    <span className="font-bold text-emerald-800">{s.status === 'CONFIRMED' ? 'मज़दूर ने पुष्टि की' : 'अभी पुष्टि नहीं हुई'}</span>
                    {s.confirmed_at ? ` • पुष्टि: ${new Date(s.confirmed_at).toLocaleString('hi-IN')}` : ''}
                  </span>
                </div>
                {s.status === 'CONFIRMED' && (
                  <button
                    type="button"
                    onClick={() => void downloadPdf(s.id)}
                    disabled={!!downloadingId}
                    aria-label="PDF डाउनलोड करें"
                    className="flex min-h-12 min-w-12 items-center justify-center rounded-xl text-[#28734e] hover:bg-[#edf3ea] disabled:opacity-50"
                  >
                    <Download className="h-5 w-5" aria-hidden="true" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
