'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, BadgeCheck, FileText, Mic, ShieldCheck, Users } from 'lucide-react';
import { useAuth } from '../lib/auth-context';
import { useLanguage } from '../lib/language-context';
import { api } from '../lib/api';
import WageSummary from '../components/WageSummary';
import { LedgerSummary } from '../types';

export default function HomePage() {
  const { isAuthenticated, workerName } = useAuth();
  const { t, language } = useLanguage();
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
      <section className="relative isolate overflow-hidden rounded-[2rem] bg-[#27272a] px-6 py-8 text-white shadow-[0_24px_60px_rgba(24,24,27,0.18)] sm:px-9 sm:py-10 md:px-12 md:py-12">
        <div className="absolute -right-14 -top-24 -z-10 h-80 w-80 rounded-full border-[1px] border-white/10" />
        <div className="absolute -right-3 -top-12 -z-10 h-60 w-60 rounded-full border-[1px] border-white/10" />
        <div className="absolute -bottom-32 right-[22%] -z-10 h-72 w-72 rounded-full bg-[#a1a1aa]/10 blur-3xl" />
        <div className="grid items-center gap-8 md:grid-cols-[1fr_auto] md:gap-12">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold text-[#d4d4d8]">
              <span className="h-2 w-2 rounded-full bg-[#a1a1aa]" /> {t.heroBadge}
            </div>
            <h1 className="mt-5 text-[2rem] font-black leading-[1.2] tracking-tight sm:text-4xl md:text-[3.25rem]">
              {isAuthenticated ? (
                <>
                  {workerName || (language === 'hi' ? 'नमस्ते' : 'Hello')}
                  {t.greetingReady}
                </>
              ) : (
                <>{t.guestTitle}</>
              )}
            </h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-[#e4e4e7] sm:text-lg sm:leading-8">
              {t.heroDescription}
            </p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Link href={isAuthenticated ? '/voice' : '/auth'} className="inline-flex min-h-14 items-center justify-center gap-3 rounded-2xl bg-[#d4d4d8] px-6 text-base font-extrabold text-[#27272a] shadow-[0_8px_24px_rgba(6,21,14,0.25)] transition hover:-translate-y-0.5 hover:bg-[#e4e4e7]">
                <Mic className="h-5 w-5" aria-hidden="true" /> {isAuthenticated ? t.recordVoiceBtn : t.startBtn} <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              {isAuthenticated && <Link href="/dashboard" className="inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl border border-white/20 bg-white/5 px-5 text-base font-bold text-white transition hover:bg-white/10">{t.viewFullDashboardBtn}</Link>}
            </div>
          </div>
          <Link href={isAuthenticated ? '/voice' : '/auth'} aria-label={t.speakToRecord} className="group mx-auto hidden aspect-square w-40 items-center justify-center rounded-full border border-white/20 bg-white/[0.07] p-3 shadow-inner transition duration-300 hover:scale-[1.03] md:mr-3 md:flex md:w-56">
            <span className="flex h-full w-full flex-col items-center justify-center gap-2 rounded-full bg-[#d4d4d8] text-[#27272a] shadow-[0_12px_42px_rgba(0,0,0,0.22)] transition group-hover:bg-[#e4e4e7]">
              <Mic className="h-11 w-11 sm:h-14 sm:w-14" strokeWidth={2.2} aria-hidden="true" />
              <span className="text-sm font-black sm:text-base">{t.speakToRecord}</span>
            </span>
          </Link>
        </div>
        <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 border-t border-white/15 pt-5 text-sm font-semibold text-[#e4e4e7]">
          <span className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-[#d4d4d8]" /> {t.badgeConfirmFirst}</span>
          <span className="inline-flex items-center gap-2"><BadgeCheck className="h-4 w-4 text-[#d4d4d8]" /> {t.badgeTimestamped}</span>
        </div>
      </section>

      {isAuthenticated ? (
        <section className="grid items-start gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <div className="mb-4 flex items-end justify-between gap-3">
              <div><p className="text-sm font-bold text-[#71717a]">{t.earningsAndPayments}</p><h2 className="mt-1 text-2xl font-black tracking-tight text-[#27272a] sm:text-3xl">{t.summaryAtAGlance}</h2></div>
              <Link href="/dashboard" className="mb-1 inline-flex items-center gap-1 text-sm font-extrabold text-[#52525b] hover:underline">{t.details} <ArrowRight className="h-4 w-4" /></Link>
            </div>
            <WageSummary summary={summary} isLoading={loading} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <Link href="/employers" className="group flex items-center gap-4 rounded-3xl border border-[#e4e4e7] bg-[#ffffff] p-5 shadow-[0_8px_28px_rgba(24,24,27,0.04)] transition hover:-translate-y-0.5 hover:shadow-lg">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f4f4f5] text-[#52525b]"><Users className="h-6 w-6" /></span>
              <span className="flex-1"><span className="block text-base font-extrabold text-[#27272a]">{t.byEmployer}</span><span className="mt-1 block text-sm text-slate-600">{t.byEmployerSub}</span></span><ArrowRight className="h-5 w-5 text-slate-400 transition group-hover:translate-x-1" />
            </Link>
            <Link href="/statements" className="group flex items-center gap-4 rounded-3xl border border-[#e4e4e7] bg-[#ffffff] p-5 shadow-[0_8px_28px_rgba(24,24,27,0.04)] transition hover:-translate-y-0.5 hover:shadow-lg">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f4f4f5] text-[#71717a]"><FileText className="h-6 w-6" /></span>
              <span className="flex-1"><span className="block text-base font-extrabold text-[#27272a]">{t.wageSlips}</span><span className="mt-1 block text-sm text-slate-600">{t.wageSlipsSub}</span></span><ArrowRight className="h-5 w-5 text-slate-400 transition group-hover:translate-x-1" />
            </Link>
          </div>
        </section>
      ) : (
        <section className="grid gap-4 sm:grid-cols-3">
          {[
            { n: '01', title: t.step1Title, body: t.step1Desc, icon: Mic },
            { n: '02', title: t.step2Title, body: t.step2Desc, icon: ShieldCheck },
            { n: '03', title: t.step3Title, body: t.step3Desc, icon: FileText },
          ].map((item) => { const Icon = item.icon; return (
            <article key={item.n} className="rounded-3xl border border-[#e4e4e7] bg-[#ffffff] p-5 shadow-[0_8px_28px_rgba(24,24,27,0.04)] sm:p-6">
              <div className="flex items-center justify-between"><span className="text-sm font-black tracking-[0.18em] text-[#71717a]">{item.n}</span><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[#f4f4f5] text-[#52525b]"><Icon className="h-5 w-5" /></span></div>
              <h2 className="mt-4 text-lg font-black text-[#27272a]">{item.title}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{item.body}</p>
            </article>
          ); })}
        </section>
      )}
      <footer className="flex flex-col gap-1 border-t border-[#e4e4e7] py-4 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <span>{language === 'hi' ? 'मेहनत का हिसाब, आपकी भाषा में।' : 'Your hard work ledger, in your language.'}</span>
        <span>{language === 'hi' ? 'रिकॉर्ड तभी जुड़ता है जब आप उसकी पुष्टि करें।' : 'Records are saved only when you confirm them.'}</span>
      </footer>
    </div>
  );
}
