'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, BadgeCheck, FileText, Mic, ShieldCheck, Users } from 'lucide-react';
import { useAuth } from '../lib/auth-context';
import { api } from '../lib/api';
import WageSummary from '../components/WageSummary';
import { LedgerSummary } from '../types';

export default function HomePage() {
  const { isAuthenticated, workerName } = useAuth();
  const [summary, setSummary] = useState<LedgerSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) return;
    let active = true;
    api.getLedgerSummary().then((data) => { if (active) setSummary(data); })
      .catch(() => { if (active) setSummary(null); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isAuthenticated]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-7 px-5 pb-4 sm:px-7 md:gap-9 md:px-0">
      <section className="relative isolate overflow-hidden rounded-[2rem] bg-[#173b2f] px-6 py-8 text-white shadow-[0_24px_60px_rgba(23,59,47,0.18)] sm:px-9 sm:py-10 md:px-12 md:py-12">
        <div className="absolute -right-14 -top-24 -z-10 h-80 w-80 rounded-full border-[1px] border-white/10" />
        <div className="absolute -right-3 -top-12 -z-10 h-60 w-60 rounded-full border-[1px] border-white/10" />
        <div className="absolute -bottom-32 right-[22%] -z-10 h-72 w-72 rounded-full bg-[#e3a84e]/10 blur-3xl" />
        <div className="grid items-center gap-8 md:grid-cols-[1fr_auto] md:gap-12">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold text-[#f5deb1]">
              <span className="h-2 w-2 rounded-full bg-[#e7b257]" /> रोज़ की मेहनत का साफ़ हिसाब
            </div>
            <h1 className="mt-5 text-[2rem] font-black leading-[1.2] tracking-tight sm:text-4xl md:text-[3.25rem]">
              {isAuthenticated ? <>{workerName || 'नमस्ते'} जी,<br className="hidden sm:block" /> आपका हिसाब तैयार है।</> : <>आपकी मेहनत।<br className="hidden sm:block" /> आपका पूरा हिसाब।</>}
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-[#e0e9df] sm:text-lg sm:leading-8">
              काम या मिला हुआ पैसा अपनी भाषा में बोलिए। रिकॉर्ड जाँचें, खुद पुष्टि करें, फिर आपका हिसाब सुरक्षित होगा।
            </p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Link href={isAuthenticated ? '/voice' : '/auth'} className="inline-flex min-h-14 items-center justify-center gap-3 rounded-2xl bg-[#f1bf68] px-6 text-base font-extrabold text-[#2c321e] shadow-[0_8px_24px_rgba(6,21,14,0.25)] transition hover:-translate-y-0.5 hover:bg-[#f8cf83]">
                <Mic className="h-5 w-5" aria-hidden="true" /> {isAuthenticated ? 'आवाज़ से रिकॉर्ड करें' : 'शुरू करें'} <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              {isAuthenticated && <Link href="/dashboard" className="inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl border border-white/20 bg-white/5 px-5 text-base font-bold text-white transition hover:bg-white/10">पूरा हिसाब देखें</Link>}
            </div>
          </div>
          <Link href={isAuthenticated ? '/voice' : '/auth'} aria-label="आवाज़ से काम या भुगतान रिकॉर्ड करें" className="group mx-auto hidden aspect-square w-40 items-center justify-center rounded-full border border-white/20 bg-white/[0.07] p-3 shadow-inner transition duration-300 hover:scale-[1.03] md:mr-3 md:flex md:w-56">
            <span className="flex h-full w-full flex-col items-center justify-center gap-2 rounded-full bg-[#f1bf68] text-[#193d30] shadow-[0_12px_42px_rgba(0,0,0,0.22)] transition group-hover:bg-[#f8cf83]">
              <Mic className="h-11 w-11 sm:h-14 sm:w-14" strokeWidth={2.2} aria-hidden="true" />
              <span className="text-sm font-black sm:text-base">बोलकर बताइए</span>
            </span>
          </Link>
        </div>
        <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 border-t border-white/15 pt-5 text-sm font-semibold text-[#d7e2d8]">
          <span className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#f1bf68]" /> आपकी पुष्टि के बाद ही सेव</span>
          <span className="inline-flex items-center gap-2"><BadgeCheck className="h-4 w-4 text-[#f1bf68]" /> साफ़ और समय सहित रिकॉर्ड</span>
        </div>
      </section>

      {isAuthenticated ? (
        <section className="grid items-start gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <div className="mb-4 flex items-end justify-between gap-3">
              <div><p className="text-sm font-bold text-[#9a6a2b]">आपकी कमाई और भुगतान</p><h2 className="mt-1 text-2xl font-black tracking-tight text-[#173b2f] sm:text-3xl">एक नज़र में हिसाब</h2></div>
              <Link href="/dashboard" className="mb-1 inline-flex items-center gap-1 text-sm font-extrabold text-[#28734e] hover:underline">विस्तार <ArrowRight className="h-4 w-4" /></Link>
            </div>
            <WageSummary summary={summary} isLoading={loading} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <Link href="/employers" className="group flex items-center gap-4 rounded-3xl border border-[#e7e5dc] bg-[#fffefa] p-5 shadow-[0_8px_28px_rgba(40,54,43,0.04)] transition hover:-translate-y-0.5 hover:shadow-lg">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#e8efe6] text-[#28734e]"><Users className="h-6 w-6" /></span>
              <span className="flex-1"><span className="block text-base font-extrabold text-[#173b2f]">मालिक के हिसाब से</span><span className="mt-1 block text-sm text-slate-600">हर ठेकेदार का अलग बकाया देखें</span></span><ArrowRight className="h-5 w-5 text-slate-400 transition group-hover:translate-x-1" />
            </Link>
            <Link href="/statements" className="group flex items-center gap-4 rounded-3xl border border-[#e7e5dc] bg-[#fffefa] p-5 shadow-[0_8px_28px_rgba(40,54,43,0.04)] transition hover:-translate-y-0.5 hover:shadow-lg">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f6ecdc] text-[#9a6326]"><FileText className="h-6 w-6" /></span>
              <span className="flex-1"><span className="block text-base font-extrabold text-[#173b2f]">आपकी मज़दूरी पर्ची</span><span className="mt-1 block text-sm text-slate-600">पुष्टि किए रिकॉर्ड की PDF पाएँ</span></span><ArrowRight className="h-5 w-5 text-slate-400 transition group-hover:translate-x-1" />
            </Link>
          </div>
        </section>
      ) : (
        <section className="grid gap-4 sm:grid-cols-3">
          {[
            { n: '01', title: 'अपनी भाषा में बोलें', body: 'काम, दिहाड़ी या मिला हुआ पैसा रिकॉर्ड करें।', icon: Mic },
            { n: '02', title: 'पहले खुद जाँचें', body: 'नाम, तारीख और रकम ठीक करें या बोलकर सुधारें।', icon: ShieldCheck },
            { n: '03', title: 'अपना हिसाब देखें', body: 'कमाई, भुगतान और बाकी रकम एक जगह पाएँ।', icon: FileText },
          ].map((item) => { const Icon = item.icon; return (
            <article key={item.n} className="rounded-3xl border border-[#e7e5dc] bg-[#fffefa] p-5 shadow-[0_8px_28px_rgba(40,54,43,0.04)] sm:p-6">
              <div className="flex items-center justify-between"><span className="text-sm font-black tracking-[0.18em] text-[#bb7b32]">{item.n}</span><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#e8efe6] text-[#28734e]"><Icon className="h-5 w-5" /></span></div>
              <h2 className="mt-4 text-lg font-black text-[#173b2f]">{item.title}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{item.body}</p>
            </article>
          ); })}
        </section>
      )}
      <footer className="flex flex-col gap-1 border-t border-[#dfddd4] py-4 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <span>मेहनत का हिसाब, आपकी भाषा में।</span><span>रिकॉर्ड तभी जुड़ता है जब आप उसकी पुष्टि करें।</span>
      </footer>
    </div>
  );
}
