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
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [isAuthenticated, authLoading, router]);

  return (
    <div className="flex flex-col px-5 py-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push('/dashboard')}
          className="p-2 -ml-2 text-slate-600 hover:text-slate-900 rounded-full hover:bg-slate-100 transition"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-xl font-black text-slate-900">मज़दूरी पर्ची (Statement)</h1>
          <p className="text-xs text-slate-500">आधिकारिक और प्रमाणित रिकॉर्ड</p>
        </div>
      </div>

      {/* Main Statement Card */}
      <div className="p-5 bg-gradient-to-br from-slate-900 to-blue-950 text-white rounded-3xl shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold bg-blue-500/20 text-blue-300 px-3 py-1 rounded-full border border-blue-400/20">
            PDF स्टेटमेंट
          </span>
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
        </div>

        <div>
          <h3 className="text-lg font-black">{workerName || 'मज़दूर साथी'}</h3>
            <p className="text-sm text-slate-300 mt-1 leading-6">
            इसमें आपके बताए और पुष्टि किए गए रिकॉर्ड व हिसाब शामिल हैं। MazdoorMitra ने जानकारी की स्वतंत्र जाँच नहीं की है।
          </p>
        </div>

        <div className="pt-2">
          {latestConfirmed ? (
            <button
              type="button"
              onClick={() => void downloadPdf(latestConfirmed.id)}
              disabled={!!downloadingId}
              className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 text-base font-bold text-white shadow transition hover:bg-blue-700 disabled:opacity-60"
            >
              <Download className="w-4 h-4" />
              {downloadingId === latestConfirmed.id ? 'PDF तैयार हो रही है…' : 'पुष्टि की गई PDF पर्ची डाउनलोड करें'}
            </button>
          ) : (
            <div className="py-2 text-center text-sm text-slate-300">
              पुष्टि किया गया रिकॉर्ड बनने के बाद PDF यहाँ उपलब्ध होगी।
            </div>
          )}
          {pdfError && <p role="alert" className="text-sm text-red-200">{pdfError}</p>}
        </div>
      </div>

      {/* Legal Disclaimer */}
      <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl text-[11px] text-slate-500 leading-relaxed space-y-1">
        <span className="font-bold text-slate-700">कानूनी सूचना (Disclaimer):</span>
        <p className="text-sm leading-6">
          यह मज़दूर द्वारा बताई गई और उसकी पुष्टि की गई जानकारी का रिकॉर्ड है। काम, समय, मज़दूरी या भुगतान की स्वतंत्र जाँच नहीं हुई है। यह कानूनी सलाह नहीं है।
        </p>
      </div>

      {/* Voice Statements History */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
          दर्ज आवाज़ वक्तव्य (Voice Records)
        </h4>

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
                className="p-3.5 bg-white border border-slate-100 rounded-xl shadow-sm flex items-center justify-between"
              >
                <div>
                  <p className="text-xs font-semibold text-slate-800 line-clamp-1">
                    &ldquo;{s.transcript || 'रिकॉर्डिंग'}&rdquo;
                  </p>
                    <span className="block text-sm text-slate-600">
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
                    className="flex min-h-11 min-w-11 items-center justify-center rounded-lg text-blue-700 hover:bg-blue-50 disabled:opacity-50"
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
