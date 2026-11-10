'use client';

import { useEffect, useMemo, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { ArrowDownToLine, FileCheck2, FileText, Image as ImageIcon, Music2, ShieldCheck, Trash2, Upload, X } from 'lucide-react';
import { api } from '../../lib/api';
import { useAuth } from '../../lib/auth-context';
import type { EvidenceFileRecord, Payment, StatementListItem, WorkEntry } from '../../types';

type DocumentType = 'payment_receipt' | 'wage_agreement' | 'work_document' | 'audio' | 'other';
type Association = { kind: 'work' | 'payment' | 'statement'; id: string } | null;
type PreviewState = { url: string; contentType: string; name: string };

const KIND_LABELS: Record<string, string> = {
  payment_receipt: 'भुगतान की रसीद', wage_agreement: 'मज़दूरी समझौता',
  work_document: 'काम का दस्तावेज़', audio: 'ऑडियो', other: 'अन्य दस्तावेज़',
};
const sizeLabel = (bytes?: number | null) => bytes == null ? 'आकार उपलब्ध नहीं' : bytes < 1024 * 1024
  ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;

export default function EvidencePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [files, setFiles] = useState<EvidenceFileRecord[]>([]);
  const [workEntries, setWorkEntries] = useState<WorkEntry[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [statements, setStatements] = useState<StatementListItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState<DocumentType>('payment_receipt');
  const [associationValue, setAssociationValue] = useState('');
  const [consent, setConsent] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewState | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) { router.push('/auth'); return; }
    if (!isAuthenticated) return;
    let active = true;
    Promise.all([api.getEvidence(), api.getWorkEntries(), api.getPayments(), api.getStatements()])
      .then(([evidence, work, payment, statement]) => {
        if (!active) return;
        setFiles(evidence);
        setWorkEntries(work);
        setPayments(payment);
        setStatements(statement);
        setError('');
      })
      .catch(() => { if (active) setError('सुरक्षित दस्तावेज़ अभी नहीं खुल पाए। फिर कोशिश करें।'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isAuthenticated, authLoading, router]);

  const associatedRecord = useMemo<Association>(() => {
    if (!associationValue) return null;
    const [kind, id] = associationValue.split(':');
    if ((kind === 'work' || kind === 'payment' || kind === 'statement') && id) return { kind, id };
    return null;
  }, [associationValue]);

  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(event.target.files?.[0] || null);
    setError('');
    setNotice('');
  };

  const upload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(''); setNotice('');
    if (!selectedFile) { setError('पहले एक दस्तावेज़ चुनें।'); return; }
    if (!consent) { setError('दस्तावेज़ निजी तौर पर सुरक्षित करने की अनुमति दें।'); return; }
    if (selectedFile.size > 12 * 1024 * 1024) { setError('फ़ाइल 12 MB या उससे छोटी होनी चाहिए।'); return; }
    try {
      setUploading(true);
      const saved = await api.uploadEvidence({
        file: selectedFile,
        document_type: documentType,
        ...(associatedRecord?.kind === 'work' ? { work_entry_id: associatedRecord.id } : {}),
        ...(associatedRecord?.kind === 'payment' ? { payment_id: associatedRecord.id } : {}),
        ...(associatedRecord?.kind === 'statement' ? { statement_id: associatedRecord.id } : {}),
      });
      setFiles((current) => [saved, ...current]);
      setSelectedFile(null); setAssociationValue(''); setConsent(false);
      setNotice('दस्तावेज़ निजी तौर पर सुरक्षित हुआ।');
      const input = document.getElementById('evidence-file') as HTMLInputElement | null;
      if (input) input.value = '';
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'दस्तावेज़ सुरक्षित नहीं हुआ। दोबारा कोशिश करें।');
    } finally { setUploading(false); }
  };

  const openPreview = async (item: EvidenceFileRecord) => {
    setError('');
    try {
      const blob = await api.getEvidencePreview(item.id);
      const url = URL.createObjectURL(blob);
      setPreview({ url, contentType: item.content_type || blob.type, name: item.file_name || 'दस्तावेज़' });
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'पूर्वावलोकन नहीं खुल पाया।'); }
  };

  const download = async (item: EvidenceFileRecord) => {
    setError('');
    try {
      const blob = await api.downloadEvidence(item.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = item.file_name || 'mazdoor-mitra-evidence';
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'डाउनलोड नहीं हो पाया।'); }
  };

  const confirmDelete = async (item: EvidenceFileRecord) => {
    setError('');
    try {
      await api.deleteEvidence(item.id);
      setFiles((current) => current.filter((record) => record.id !== item.id));
      setDeleteTarget(null);
      setNotice('दस्तावेज़ और उसकी निजी फ़ाइल मिटा दी गई।');
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'दस्तावेज़ नहीं मिट पाया।'); }
  };

  const closePreview = () => {
    if (preview) URL.revokeObjectURL(preview.url);
    setPreview(null);
  };

  if (authLoading || (!isAuthenticated && typeof window !== 'undefined')) return <div className="flex min-h-[50vh] items-center justify-center" role="status"><div className="h-9 w-9 animate-spin rounded-full border-4 border-zinc-500 border-t-transparent" /></div>;

  return <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 pb-5 sm:px-6 md:gap-7 md:px-0">
    <header className="rounded-[1.6rem] border border-zinc-200 bg-white p-5 shadow-sm sm:p-7">
      <div className="flex items-start gap-3"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-zinc-100 text-zinc-700"><ShieldCheck className="h-5 w-5" /></span><div><p className="text-sm font-bold text-zinc-500">आपके दस्तावेज़, आपकी अनुमति से</p><h1 className="mt-1 text-2xl font-black tracking-tight text-zinc-900 sm:text-3xl">सुरक्षित दस्तावेज़</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600">रसीद, मज़दूरी समझौता या काम का दस्तावेज़ निजी रूप से जोड़ें। फ़ाइल का नाम और जानकारी दिखेगी; सामग्री सार्वजनिक लिंक से उपलब्ध नहीं है।</p></div></div>
    </header>

    {error && <div role="alert" className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-950">{error}</div>}
    {notice && <div role="status" className="rounded-xl border border-zinc-200 bg-zinc-100 px-4 py-3 text-sm font-semibold text-zinc-800">{notice}</div>}

    <section className="grid items-start gap-5 lg:grid-cols-[0.9fr_1.1fr]">
      <form onSubmit={upload} className="space-y-4 rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5">
        <div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">नया दस्तावेज़</p><h2 className="mt-1 text-lg font-black text-zinc-900">फ़ाइल सुरक्षित करें</h2></div>
        <label className="block text-sm font-bold text-zinc-700">दस्तावेज़ का प्रकार<select value={documentType} onChange={(event) => setDocumentType(event.target.value as DocumentType)} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 bg-white px-3 font-medium"><option value="payment_receipt">भुगतान की रसीद</option><option value="wage_agreement">मज़दूरी समझौता</option><option value="work_document">काम का दस्तावेज़</option><option value="audio">ऑडियो रिकॉर्डिंग</option><option value="other">अन्य</option></select></label>
        <label className="block text-sm font-bold text-zinc-700">रिकॉर्ड से जोड़ें <span className="font-normal text-zinc-500">(वैकल्पिक)</span><select value={associationValue} onChange={(event) => setAssociationValue(event.target.value)} className="mt-1.5 min-h-11 w-full rounded-xl border border-zinc-200 bg-white px-3 text-sm font-medium"><option value="">किसी रिकॉर्ड से न जोड़ें</option>{workEntries.map((entry) => <option key={`work-${entry.id}`} value={`work:${entry.id}`}>काम · {entry.employer_name || 'मालिक दर्ज नहीं'} · {new Date(entry.work_date).toLocaleDateString('hi-IN')}</option>)}{payments.map((payment) => <option key={`pay-${payment.id}`} value={`payment:${payment.id}`}>भुगतान · {payment.employer_name || 'मालिक दर्ज नहीं'} · {new Date(payment.payment_date).toLocaleDateString('hi-IN')}</option>)}{statements.map((statement) => <option key={`statement-${statement.id}`} value={`statement:${statement.id}`}>आवाज़ रिकॉर्ड · {new Date(statement.created_at).toLocaleDateString('hi-IN')}</option>)}</select></label>
        <label htmlFor="evidence-file" className="flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-zinc-300 bg-zinc-50 px-4 text-center transition hover:bg-zinc-100"><Upload className="h-5 w-5 text-zinc-500" /><span className="mt-2 text-sm font-bold text-zinc-800">{selectedFile ? selectedFile.name : 'फ़ाइल चुनें या यहाँ छोड़ें'}</span><span className="mt-1 text-xs text-zinc-500">PDF, JPEG, PNG, WebP, WAV या WebM · अधिकतम 12 MB</span><input id="evidence-file" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,.wav,.webm,application/pdf,image/jpeg,image/png,image/webp,audio/wav,audio/webm" onChange={chooseFile} className="sr-only" /></label>
        <label className="flex items-start gap-3 rounded-xl border border-zinc-200 p-3 text-sm leading-5 text-zinc-700"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-0.5 h-4 w-4 accent-zinc-900" /><span>मैं इस फ़ाइल को अपने खाते में निजी रूप से सुरक्षित करने की अनुमति देता/देती हूँ। मैं इसे कभी भी मिटा सकता/सकती हूँ।</span></label>
        <button type="submit" disabled={uploading || !selectedFile} className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-zinc-900 px-4 text-sm font-extrabold text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50">{uploading ? <><span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />फ़ाइल सुरक्षित हो रही है…</> : <><Upload className="h-4 w-4" />दस्तावेज़ सुरक्षित करें</>}</button>
      </form>

      <section className="rounded-[1.5rem] border border-zinc-200 bg-white p-4 shadow-sm sm:p-5" aria-labelledby="evidence-list-title">
        <div className="flex items-end justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-zinc-500">निजी संग्रह</p><h2 id="evidence-list-title" className="mt-1 text-lg font-black text-zinc-900">मेरे दस्तावेज़</h2></div><span className="rounded-lg bg-zinc-100 px-3 py-1.5 text-xs font-bold text-zinc-700">{files.length} फ़ाइलें</span></div>
        {loading ? <div role="status" className="mt-4 space-y-2"><div className="h-16 animate-pulse rounded-xl bg-zinc-100" /><div className="h-16 animate-pulse rounded-xl bg-zinc-100" /></div> : files.length === 0 ? <div className="mt-4 rounded-xl border border-dashed border-zinc-300 bg-zinc-50 px-4 py-8 text-center"><FileText className="mx-auto h-6 w-6 text-zinc-500" /><p className="mt-2 text-sm font-bold text-zinc-800">अभी कोई दस्तावेज़ नहीं</p><p className="mt-1 text-xs text-zinc-500">रसीद या समझौते को अपने रिकॉर्ड के साथ रख सकते हैं।</p></div> : <ul className="mt-4 divide-y divide-zinc-100">{files.map((item) => {
          const icon = item.content_type?.startsWith('image/') ? <ImageIcon className="h-4 w-4" /> : item.content_type?.startsWith('audio/') ? <Music2 className="h-4 w-4" /> : <FileCheck2 className="h-4 w-4" />;
          return <li key={item.id} className="py-3 first:pt-0 last:pb-0"><div className="flex items-start gap-3"><span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-zinc-600">{icon}</span><div className="min-w-0 flex-1"><p className="break-words text-sm font-extrabold text-zinc-900">{item.file_name || 'दस्तावेज़'}</p><p className="mt-0.5 text-xs text-zinc-500">{KIND_LABELS[item.document_type || 'other']} · {sizeLabel(item.size_bytes)} · {new Date(item.created_at).toLocaleDateString('hi-IN')}</p><p className="mt-1 text-[11px] font-medium text-zinc-500">निजी · आपकी अनुमति से सुरक्षित</p>{deleteTarget === item.id && <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-2"><span className="mr-auto text-xs font-semibold text-red-900">फ़ाइल हमेशा के लिए मिटाएँ?</span><button type="button" onClick={() => void confirmDelete(item)} className="min-h-8 rounded-md bg-red-700 px-2.5 text-xs font-bold text-white">हाँ, मिटाएँ</button><button type="button" onClick={() => setDeleteTarget(null)} className="min-h-8 rounded-md border border-red-200 bg-white px-2.5 text-xs font-bold text-red-800">रद्द</button></div>}</div><div className="flex shrink-0 items-center gap-1"><button type="button" onClick={() => void openPreview(item)} aria-label={`${item.file_name || 'दस्तावेज़'} का पूर्वावलोकन`} className="flex h-9 w-9 items-center justify-center rounded-lg text-zinc-600 hover:bg-zinc-100"><ImageIcon aria-hidden="true" className="h-4 w-4" /></button><button type="button" onClick={() => void download(item)} aria-label={`${item.file_name || 'दस्तावेज़'} डाउनलोड करें`} className="flex h-9 w-9 items-center justify-center rounded-lg text-zinc-600 hover:bg-zinc-100"><ArrowDownToLine className="h-4 w-4" /></button><button type="button" onClick={() => setDeleteTarget(deleteTarget === item.id ? null : item.id)} aria-label={`${item.file_name || 'दस्तावेज़'} मिटाएँ`} className="flex h-9 w-9 items-center justify-center rounded-lg text-zinc-600 hover:bg-red-50 hover:text-red-700"><Trash2 className="h-4 w-4" /></button></div></div></li>;
        })}</ul>}
      </section>
    </section>

    {preview && <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-3 sm:p-6" role="presentation" onClick={(event) => { if (event.target === event.currentTarget) closePreview(); }}><section className="flex max-h-[90dvh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="preview-title"><div className="flex items-center justify-between gap-3 border-b border-zinc-200 px-4 py-3"><h2 id="preview-title" className="min-w-0 truncate text-sm font-extrabold text-zinc-900">{preview.name}</h2><button type="button" onClick={closePreview} aria-label="पूर्वावलोकन बंद करें" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg hover:bg-zinc-100"><X className="h-4 w-4" /></button></div><div className="flex min-h-64 flex-1 items-center justify-center overflow-auto bg-zinc-100 p-3">{preview.contentType.startsWith('image/') ? <Image src={preview.url} alt={preview.name} width={1600} height={1200} unoptimized className="max-h-[72dvh] max-w-full object-contain" /> : preview.contentType === 'application/pdf' ? <iframe title={preview.name} src={preview.url} className="h-[72dvh] w-full rounded-lg bg-white" /> : preview.contentType.startsWith('audio/') ? <audio controls src={preview.url} className="w-full max-w-lg" /> : <p className="text-sm text-zinc-600">इस फ़ाइल का पूर्वावलोकन उपलब्ध नहीं है।</p>}</div></section></div>}
  </div>;
}
