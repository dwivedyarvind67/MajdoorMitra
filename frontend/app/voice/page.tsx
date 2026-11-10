'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../lib/auth-context';
import { api, VoiceCorrections } from '../../lib/api';
import VoiceRecorder from '../../components/VoiceRecorder';
import TranscriptCard from '../../components/TranscriptCard';
import ConfirmationCard from '../../components/ConfirmationCard';
import LanguageSelector from '../../components/LanguageSelector';
import { ExtractionResult, StatementStatus } from '../../types';
import { ArrowLeft, CheckCircle, Volume2 } from 'lucide-react';

const EDITABLE_FIELDS: (keyof VoiceCorrections)[] = [
  'intent', 'days_worked', 'daily_wage', 'hours_worked', 'wage_basis',
  'hourly_rate', 'overtime_hours', 'overtime_multiplier', 'work_date',
  'amount_received', 'payment_type', 'employer_name', 'description',
];

export default function VoicePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [language, setLanguage] = useState('hi');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<StatementStatus>('INITIAL');
  const [transcript, setTranscript] = useState('');
  const [replyTranscript, setReplyTranscript] = useState<string | null>(null);
  const [extractedData, setExtractedData] = useState<ExtractionResult | null>(null);
  const [question, setQuestion] = useState<string | null>(null);
  const [replyInput, setReplyInput] = useState('');
  const [processing, setProcessing] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [confirmedMessage, setConfirmedMessage] = useState<string | null>(null);
  const [spokenText, setSpokenText] = useState<string | null>(null);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const requestRef = useRef(0);
  const initialSessionRequestRef = useRef<{
    language: string;
    promise: ReturnType<typeof api.createVoiceSession>;
  } | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/auth');
  }, [isAuthenticated, authLoading, router]);

  const initSession = useCallback(async () => {
    const requestId = ++requestRef.current;
    initialSessionRequestRef.current = null;
    try {
      const session = await api.createVoiceSession(language);
      if (requestId !== requestRef.current) return;
      setSessionId(session.id);
      setStatus(session.status as StatementStatus);
    } catch (error) {
      if (requestId === requestRef.current) {
        setPageError(error instanceof Error ? error.message : 'नया सत्र शुरू नहीं हो पाया। इंटरनेट जाँचकर फिर कोशिश करें।');
      }
    } finally {
      if (requestId === requestRef.current) setSessionLoading(false);
    }
  }, [language]);

  useEffect(() => {
    if (!isAuthenticated) return;
    let active = true;
    const requestId = ++requestRef.current;
    let pending = initialSessionRequestRef.current;
    if (!pending || pending.language !== language) {
      pending = { language, promise: api.createVoiceSession(language) };
      initialSessionRequestRef.current = pending;
    }

    void pending.promise
      .then((session) => {
        if (!active || requestId !== requestRef.current) return;
        setSessionId(session.id);
        setStatus(session.status as StatementStatus);
      })
      .catch((error: unknown) => {
        if (!active || requestId !== requestRef.current) return;
        setPageError(error instanceof Error ? error.message : 'नया सत्र शुरू नहीं हो पाया। इंटरनेट जाँचकर फिर कोशिश करें।');
      })
      .finally(() => {
        if (!active || requestId !== requestRef.current) return;
        setSessionLoading(false);
        if (initialSessionRequestRef.current === pending) initialSessionRequestRef.current = null;
      });

    return () => {
      active = false;
      if (requestRef.current === requestId) requestRef.current += 1;
    };
  }, [isAuthenticated, language]);

  useEffect(() => () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  useEffect(() => () => {
    requestRef.current += 1;
  }, []);

  const clearAudio = () => {
    setAudioUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return null;
    });
  };

  const handleAudioRecording = async (blob: Blob) => {
    if (!sessionId) return;
    setProcessing(true);
    setPageError(null);
    try {
      if (status === 'AWAITING_INFORMATION' || status === 'READY_FOR_CONFIRMATION' || status === 'EXTRACTED') {
        const response = await api.replyAudio(sessionId, blob);
        setReplyTranscript(response.transcript || null);
        setExtractedData(response.extracted_data || null);
        setStatus(response.status as StatementStatus);
        setQuestion(response.question || null);
      } else {
        const transcription = await api.uploadAudio(sessionId, blob);
        setTranscript(transcription.transcript);
        setReplyTranscript(null);
        setStatus(transcription.status as StatementStatus);
        const extraction = await api.extractData(sessionId);
        setExtractedData(extraction.extracted_data || null);
        setStatus(extraction.status as StatementStatus);
        setQuestion(extraction.question || null);
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'आवाज़ प्रोसेस नहीं हो पाई। आपकी पिछली जानकारी सुरक्षित है।');
    } finally {
      setProcessing(false);
    }
  };

  const handleReplySubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!sessionId || !replyInput.trim()) return;
    setProcessing(true);
    setPageError(null);
    try {
      const response = await api.replySession(sessionId, replyInput.trim());
      setReplyTranscript(null);
      setReplyInput('');
      setExtractedData(response.extracted_data || null);
      setStatus(response.status as StatementStatus);
      setQuestion(response.question || null);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'जवाब समझ नहीं आया। आपकी जानकारी सुरक्षित है; कृपया फिर कोशिश करें।');
    } finally {
      setProcessing(false);
    }
  };

  const handleReviewChanges = async (editedData: ExtractionResult) => {
    if (!sessionId || !extractedData) return;
    setProcessing(true);
    setPageError(null);
    try {
      const corrections: VoiceCorrections = {};
      for (const field of EDITABLE_FIELDS) {
        const before = extractedData[field];
        const after = editedData[field];
        if (String(before ?? '') !== String(after ?? '')) {
          (corrections as Record<string, unknown>)[field] = after === '' ? null : after;
        }
      }
      if (Object.keys(corrections).length) {
        const corrected = await api.correctSession(sessionId, corrections);
        setExtractedData(corrected.extracted_data || extractedData);
        setStatus(corrected.status as StatementStatus);
        setQuestion(corrected.question || null);
      } else {
        setPageError('कोई बदलाव नहीं मिला। बदले हुए अंकों को जाँचकर फिर कोशिश करें।');
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'बदली जानकारी जाँची नहीं जा सकी। पुराना रिकॉर्ड सुरक्षित है।');
    } finally {
      setProcessing(false);
    }
  };

  const handleConfirm = async () => {
    if (!sessionId) return;
    setProcessing(true);
    setPageError(null);
    clearAudio();
    try {
      const saved = await api.confirmSession(sessionId);
      setStatus('CONFIRMED');
      setConfirmedMessage(saved.message || 'आपकी पुष्टि के बाद रिकॉर्ड सेव हो गया है।');
      setSpeechError(null);
      await fetchSpokenReceipt(sessionId);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'रिकॉर्ड सेव नहीं हुआ। आपकी पुष्टि से पहले कोई नया हिसाब नहीं जोड़ा गया।');
    } finally {
      setProcessing(false);
    }
  };

  const fetchSpokenReceipt = async (id: string) => {
    try {
      const response = await api.speakSummary(id);
      setSpokenText(response.text);
      if (response.audio_base64) {
        const bytes = Uint8Array.from(atob(response.audio_base64), (character) => character.charCodeAt(0));
        const objectUrl = URL.createObjectURL(new Blob([bytes], { type: response.audio_content_type || 'audio/wav' }));
        setAudioUrl(objectUrl);
        setSpeechError(null);
      } else {
        setSpeechError('रसीद का ऑडियो नहीं मिला। आप बाद में फिर कोशिश कर सकते हैं।');
      }
    } catch (error) {
      setSpeechError(error instanceof Error ? error.message : 'रिकॉर्ड सेव है, लेकिन आवाज़ अभी तैयार नहीं हुई।');
    }
  };

  const handleReject = async () => {
    if (!sessionId) return;
    setProcessing(true);
    setPageError(null);
    try {
      if (status !== 'CONFIRMED') await api.rejectSession(sessionId);
      setTranscript('');
      setReplyTranscript(null);
      setExtractedData(null);
      setQuestion(null);
      setConfirmedMessage(null);
      setSpokenText(null);
      setSpeechError(null);
      clearAudio();
      setSessionLoading(true);
      setSessionId(null);
      setPageError(null);
      await initSession();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'ड्राफ़्ट रद्द नहीं हो पाया।');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-8rem)] w-full max-w-4xl flex-col px-5 py-3 sm:px-7 md:min-h-0 md:px-0 md:py-0">
      <div className="mb-5 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => router.push('/dashboard')}
          aria-label="डैशबोर्ड पर वापस जाएँ"
          className="flex min-h-11 min-w-11 items-center justify-center rounded-xl border border-[#e4e2da] bg-[#fffefa] text-slate-700 shadow-sm transition hover:bg-white"
        >
          <ArrowLeft className="h-5 w-5" aria-hidden="true" />
        </button>
        <LanguageSelector currentLanguage={language} onLanguageChange={(nextLanguage) => {
          if (nextLanguage !== language) {
            setTranscript('');
            setReplyTranscript(null);
            setExtractedData(null);
            setQuestion(null);
            setStatus('INITIAL');
            setSessionLoading(true);
            setSessionId(null);
            setPageError(null);
            setLanguage(nextLanguage);
          }
        }} />
      </div>

      <header className="mb-6 text-center">
        <span className="text-sm font-extrabold tracking-wide text-[#9a6a2b]">आपका हिसाब · आवाज़ से</span>
        <h1 className="mt-1 text-3xl font-black tracking-tight text-[#173b2f] sm:text-4xl">बोलकर रिकॉर्ड करें</h1>
        <p className="mt-2 text-base leading-7 text-slate-600 sm:text-lg">काम, दिहाड़ी या मिला हुआ पैसा अपनी भाषा में बताइए।</p>
      </header>

      <ol aria-label="रिकॉर्ड करने के चरण" className="mx-auto mb-6 grid w-full max-w-2xl grid-cols-3 gap-2">
        {[
          { label: 'बोलें', complete: ['TRANSCRIBED', 'EXTRACTED', 'AWAITING_INFORMATION', 'READY_FOR_CONFIRMATION', 'CONFIRMED'].includes(status) },
          { label: 'जाँचें', complete: ['READY_FOR_CONFIRMATION', 'CONFIRMED'].includes(status) },
          { label: 'पुष्टि करें', complete: status === 'CONFIRMED' },
        ].map((step, index) => (
          <li key={step.label} className={`flex items-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-bold ${step.complete ? 'border-[#cadfc9] bg-[#eaf2e7] text-[#285c3d]' : index === 0 ? 'border-[#173b2f] bg-[#173b2f] text-white' : 'border-[#e7e5dc] bg-[#fffefa] text-slate-500'}`}>
            <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${step.complete ? 'bg-[#28734e] text-white' : index === 0 ? 'bg-white/15 text-white' : 'bg-[#efeee8] text-slate-500'}`}>{index + 1}</span>
            <span className="truncate">{step.label}</span>
          </li>
        ))}
      </ol>

      {pageError && (
        <div role="alert" className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-base leading-6 text-red-900">
          {pageError}
        </div>
      )}

      {status === 'CONFIRMED' ? (
        <section className="my-auto space-y-4 rounded-3xl border border-emerald-300 bg-emerald-50 p-6 text-center" aria-labelledby="saved-heading">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-700 text-white">
            <CheckCircle className="h-10 w-10" aria-hidden="true" />
          </div>
          <h2 id="saved-heading" className="text-xl font-black text-emerald-950">आपकी पुष्टि के बाद रिकॉर्ड सेव हुआ</h2>
          <p className="text-base text-emerald-950">{confirmedMessage}</p>
          <div className="rounded-xl border border-emerald-200 bg-white p-4 text-left">
            <p className="mb-2 text-sm font-bold text-slate-700">मूल आवाज़ (आपका बताया हुआ विवरण)</p>
            <p className="text-base leading-7 text-slate-900">{transcript || 'मूल विवरण उपलब्ध नहीं है।'}</p>
          </div>
          {spokenText && (
            <div className="rounded-xl border border-emerald-200 bg-white p-4 text-left">
              <p className="mb-2 flex items-center gap-2 text-sm font-bold text-emerald-900">
                <Volume2 className="h-5 w-5" aria-hidden="true" /> सुनने योग्य रसीद
              </p>
              <p className="mb-3 text-base leading-7 text-slate-900">{spokenText}</p>
              {audioUrl ? <audio controls className="w-full" aria-label="बोली गई मज़दूरी रसीद" src={audioUrl} /> : null}
            </div>
          )}
          {speechError && (
            <div className="space-y-2 text-sm text-amber-900" role="status">
              <p>{speechError}</p>
              <button type="button" onClick={() => sessionId && void fetchSpokenReceipt(sessionId)} className="min-h-11 rounded-lg border border-amber-400 bg-white px-4 font-bold hover:bg-amber-50">
                रसीद फिर से बनाएं
              </button>
            </div>
          )}
          <div className="flex flex-col gap-3 pt-2">
            <button type="button" onClick={() => router.push('/dashboard')} className="min-h-12 rounded-xl bg-emerald-700 px-4 text-base font-bold text-white hover:bg-emerald-800">
              डैशबोर्ड पर जाएँ
            </button>
            <button type="button" onClick={handleReject} disabled={processing} className="min-h-12 rounded-xl px-4 text-base font-bold text-emerald-900 hover:bg-emerald-100 disabled:opacity-50">
              + एक और रिकॉर्ड जोड़ें
            </button>
          </div>
        </section>
      ) : (
        <div className="space-y-4">
          <VoiceRecorder onRecordingComplete={handleAudioRecording} isProcessing={processing} isReady={!!sessionId && !sessionLoading && isAuthenticated} />
          <p className="text-center text-sm leading-6 text-slate-600">
            उदाहरण: “मैंने 6 दिन काम किया, रोज़ 700 रुपये मिले।”
          </p>

          {transcript && <TranscriptCard transcript={transcript} language={language} />}
          {replyTranscript && (
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-4" role="status">
              <p className="text-sm font-bold text-blue-900">आपका जवाब</p>
              <p className="mt-1 text-base leading-6 text-slate-900">{replyTranscript}</p>
            </div>
          )}

          {question && status === 'AWAITING_INFORMATION' && (
            <section className="space-y-3 rounded-2xl border border-amber-300 bg-amber-50 p-4" aria-labelledby="follow-up-heading">
              <h2 id="follow-up-heading" className="text-base font-bold text-amber-950">एक छोटी जानकारी चाहिए</h2>
              <p className="text-base leading-6 text-amber-950">{question}</p>
              <p className="text-sm text-amber-900">आप ऊपर माइक से बोल सकते हैं या नीचे लिख सकते हैं।</p>
              <form onSubmit={handleReplySubmit} className="flex gap-2">
                <label className="sr-only" htmlFor="voice-reply">अपना जवाब लिखें</label>
                <input
                  id="voice-reply"
                  type="text"
                  value={replyInput}
                  onChange={(event) => setReplyInput(event.target.value)}
                  placeholder="जवाब लिखें"
                  className="min-h-12 min-w-0 flex-1 rounded-xl border border-amber-400 bg-white px-3 text-base text-slate-950 focus:outline-none focus:ring-2 focus:ring-amber-700"
                />
                <button type="submit" disabled={!replyInput.trim() || processing} className="min-h-12 rounded-xl bg-amber-700 px-5 text-base font-bold text-white disabled:opacity-50">
                  भेजें
                </button>
              </form>
            </section>
          )}

          {extractedData && status === 'READY_FOR_CONFIRMATION' && (
            <ConfirmationCard key={JSON.stringify(extractedData)} data={extractedData} onReviewChanges={handleReviewChanges} onConfirm={handleConfirm} onReject={handleReject} isConfirming={processing} />
          )}
        </div>
      )}
    </div>
  );
}
