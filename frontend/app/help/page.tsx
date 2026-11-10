'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, BookOpenText, Copy, ExternalLink, HandCoins, ShieldQuestion } from 'lucide-react';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth-context';
import type { AssistanceFaq, AssistanceResource, Employer, PaymentRequestDraft } from '../../types';

export default function HelpPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [resources, setResources] = useState<AssistanceResource[]>([]);
  const [faqs, setFaqs] = useState<AssistanceFaq[]>([]);
  const [employers, setEmployers] = useState<Employer[]>([]);
  const [employerId, setEmployerId] = useState('');
  const [language, setLanguage] = useState<'hi' | 'en'>('hi');
  const [draft, setDraft] = useState<PaymentRequestDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) { router.push('/auth'); return; }
    if (!isAuthenticated) return;
    let active = true;
    Promise.all([api.getAssistanceResources(), api.getAssistanceFaqs(), api.getEmployers()])
      .then(([resourceData, faqData, employerData]) => {
        if (!active) return;
        setResources(resourceData);
        setFaqs(faqData.items);
        setEmployers(employerData);
      })
      .catch(() => { if (active) setError('सहायता की जानकारी अभी नहीं खुल पाई।'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isAuthenticated, authLoading, router]);

  const prepareDraft = async () => {
    setError(''); setCopied(false); setBusy(true);
    try { setDraft(await api.createPaymentRequestDraft(employerId || undefined, language)); }
    catch (cause) { setDraft(null); setError(cause instanceof Error ? cause.message : 'अनुरोध तैयार नहीं हुआ।'); }
    finally { setBusy(false); }
  };

  const copyDraft = async () => {
    if (!draft) return;
    try { await navigator.clipboard.writeText(draft.message); setCopied(true); }
    catch { setError('कॉपी नहीं हो पाया। संदेश चुनकर कॉपी करें।'); }
  };

  if (authLoading || (!isAuthenticated && typeof window !== 'undefined')) return <div className="flex min-h-[50vh] items-center justify-center" role="status"><div className="h-9 w-9 animate-spin rounded-full border-4 border-zinc-500 border-t-transparent" /></div>;

  return <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 pb-5 sm:px-6 md:gap-7 md:px-0">
    <header className="rounded-[1.6rem] border border-zinc-200 bg-white p-5 shadow-sm sm:p-7"><div className="flex items-start gap-3"><button onClick={() => router.push('/dashboard')} aria-label="डैशबोर्ड पर जाएँ" className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-zinc-200 text-zinc-600 hover:bg-zinc-100"><ArrowLeft className="h-4 w-4" /></button><div><p className="text-sm font-bold text-zinc-500">साफ़ जानकारी, आपके फैसले</p><h1 className="mt-1 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl">मदद और जानकारी</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600">यहाँ सामान्य रिकॉर्ड-रखने की जानकारी और सरकारी सहायता लिंक हैं। MazdoorMitra कोई शिकायत दर्ज नहीं करता और कानूनी सलाह नहीं देता।</p></div></div></header>
    {error && <p role="alert" className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-950">{error}</p>}

    <section className="grid items-start gap-5 lg:grid-cols-[0.9fr_1.1fr]">
      <section className="rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="help-resources-title"><div className="flex items-start gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700"><ExternalLink className="h-4 w-4" /></span><div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">सरकारी संसाधन</p><h2 id="help-resources-title" className="mt-1 font-black text-zinc-900">आधिकारिक सहायता</h2></div></div>
        {loading ? <p role="status" className="mt-4 text-sm text-zinc-500">जानकारी लोड हो रही है…</p> : <ul className="mt-3 divide-y divide-zinc-100">{resources.map((resource) => <li key={resource.id} className="py-3 first:pt-0 last:pb-0"><a href={resource.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm font-extrabold text-zinc-900 underline decoration-zinc-300 underline-offset-4 hover:decoration-zinc-700">{resource.title}<ExternalLink className="h-3.5 w-3.5" /></a><p className="mt-1 text-xs leading-5 text-zinc-600">{resource.description}</p>{resource.phone && <p className="mt-1 text-sm font-black text-zinc-800">{resource.phone}</p>}{resource.availability && <p className="mt-0.5 text-xs text-zinc-500">{resource.availability}</p>}<p className="mt-1 text-[11px] text-zinc-500">स्रोत: {resource.source}</p></li>)}</ul>}
      </section>

      <section className="rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="payment-request-title"><div className="flex items-start gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700"><HandCoins className="h-4 w-4" /></span><div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">आपके दर्ज balance से</p><h2 id="payment-request-title" className="mt-1 font-black text-zinc-900">भुगतान का विनम्र संदेश</h2><p className="mt-1 text-xs leading-5 text-zinc-500">संदेश सिर्फ़ कॉपी होगा। यह आपके अपने रिकॉर्ड का अनुरोध है, किसी बकाया की स्वतंत्र पुष्टि नहीं।</p></div></div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2"><label className="text-sm font-bold text-zinc-700">मालिक<select value={employerId} onChange={(event) => { setEmployerId(event.target.value); setDraft(null); }} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 bg-white px-3 text-sm font-medium"><option value="">सभी मालिकों का हिसाब</option>{employers.map((employer) => <option key={employer.id} value={employer.id}>{employer.name}</option>)}</select></label><label className="text-sm font-bold text-zinc-700">भाषा<select value={language} onChange={(event) => { setLanguage(event.target.value as 'hi' | 'en'); setDraft(null); }} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 bg-white px-3 text-sm font-medium"><option value="hi">हिंदी</option><option value="en">English</option></select></label></div>
        <button onClick={() => void prepareDraft()} disabled={busy} className="mt-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-zinc-900 px-4 text-sm font-extrabold text-white hover:bg-zinc-700 disabled:opacity-50">{busy ? 'आपका दर्ज हिसाब देख रहे हैं…' : 'संदेश तैयार करें'}</button>
        {draft && <div className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50 p-3"><p className="text-[11px] font-bold uppercase tracking-wide text-zinc-500">दर्ज बकाया: ₹{Number(draft.amount_in_recorded_balance).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p><textarea readOnly value={draft.message} aria-label="भुगतान अनुरोध संदेश" rows={4} className="mt-2 w-full resize-y rounded-lg border border-zinc-200 bg-white p-3 text-sm leading-6 text-zinc-800" /><button onClick={() => void copyDraft()} className="mt-2 inline-flex min-h-10 items-center gap-2 rounded-lg border border-zinc-300 bg-white px-3 text-sm font-bold text-zinc-800 hover:bg-zinc-100"><Copy className="h-4 w-4" />{copied ? 'कॉपी हो गया' : 'संदेश कॉपी करें'}</button></div>}
      </section>
    </section>

    <section className="rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="help-faq-title"><div className="flex items-start gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-700"><BookOpenText className="h-4 w-4" /></span><div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">सामान्य जानकारी</p><h2 id="help-faq-title" className="mt-1 font-black text-zinc-900">काम के रिकॉर्ड से जुड़े सवाल</h2></div></div>
      {faqs.length ? <div className="mt-3 divide-y divide-zinc-100">{faqs.map((faq) => <details key={faq.id} className="py-3"><summary className="cursor-pointer text-sm font-extrabold text-zinc-800">{language === 'hi' ? faq.question_hi : faq.question_en}</summary><p className="mt-2 text-sm leading-6 text-zinc-600">{language === 'hi' ? faq.answer_hi : faq.answer_en}</p></details>)}</div> : loading ? <p role="status" className="mt-3 text-sm text-zinc-500">जानकारी लोड हो रही है…</p> : null}
      <p className="mt-3 flex items-start gap-2 rounded-xl bg-zinc-50 p-3 text-xs leading-5 text-zinc-600"><ShieldQuestion className="mt-0.5 h-4 w-4 shrink-0" />सामान्य जानकारी भर है। किसी कानून, पात्रता या नतीजे पर व्यक्तिगत सलाह के लिए योग्य सहायता लें। सरकारी पोर्टल की ताज़ा शर्तें वहीं देखें।</p>
    </section>
  </div>;
}
