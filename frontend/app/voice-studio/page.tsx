'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Check, ChevronDown, Clock3, Download, Heart, LoaderCircle, Mic2, Play, Sparkles, Trash2, Volume2, WandSparkles } from 'lucide-react';
import { api, SpeechVoice, VoiceCapabilities, VoiceHistoryItem } from '../../lib/api';
import { useAuth } from '../../lib/auth-context';

const LANGUAGES: Record<string, string> = {
  'auto': 'Auto detect', 'bn-IN': 'বাংলা · Bengali', 'en-IN': 'English', 'gu-IN': 'ગુજરાતી · Gujarati',
  'hi-IN': 'हिन्दी · Hindi', 'kn-IN': 'ಕನ್ನಡ · Kannada', 'ml-IN': 'മലയാളം · Malayalam',
  'mr-IN': 'मराठी · Marathi', 'pa-IN': 'ਪੰਜਾਬੀ · Punjabi', 'ta-IN': 'தமிழ் · Tamil', 'te-IN': 'తెలుగు · Telugu',
};

const SAMPLE = 'नमस्ते, आपका आज का काम और मज़दूरी का हिसाब तैयार है।';

export default function VoiceStudioPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [capabilities, setCapabilities] = useState<VoiceCapabilities | null>(null);
  const [history, setHistory] = useState<VoiceHistoryItem[]>([]);
  const [modelId, setModelId] = useState('timbre-v3.0');
  const [voiceId, setVoiceId] = useState('Shivani');
  const [language, setLanguage] = useState('hi-IN');
  const [speed, setSpeed] = useState(1);
  const [text, setText] = useState(SAMPLE);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [activeGeneration, setActiveGeneration] = useState<VoiceHistoryItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState('');
  const [loadingCapabilities, setLoadingCapabilities] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [favorites, setFavorites] = useState<string[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/auth');
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    let active = true;
    Promise.all([api.getVoiceCapabilities(), api.getVoiceHistory()])
      .then(([data, recent]) => {
        if (!active) return;
        setCapabilities(data);
        setHistory(recent);
      })
      .catch((error: unknown) => {
        if (active) setPageError(error instanceof Error ? error.message : 'आवाज़ स्टूडियो लोड नहीं हुआ।');
      })
      .finally(() => { if (active) setLoadingCapabilities(false); });
    const favoriteFrame = window.requestAnimationFrame(() => {
      try {
        const saved = localStorage.getItem('mazdoormitra_voice_favorites');
        if (active && saved) setFavorites(JSON.parse(saved) as string[]);
      } catch { /* Invalid local preferences are ignored. */ }
    });
    return () => { active = false; window.cancelAnimationFrame(favoriteFrame); };
  }, [isAuthenticated]);

  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl); }, [audioUrl]);

  const selectedModel = useMemo(
    () => capabilities?.timbre.models.find((model) => model.id === modelId),
    [capabilities, modelId],
  );
  const voices = selectedModel?.voices ?? [];
  const selectedVoice = voices.find((voice) => voice.id === voiceId) ?? voices[0];
  const tagsAvailable = selectedModel?.audio_tags ?? false;
  const availableLanguages = Array.isArray(selectedVoice?.languages)
    ? selectedVoice.languages
    : (selectedModel?.languages ?? []);
  const characterCount = text.length;

  const updateModel = (nextModel: string) => {
    const next = capabilities?.timbre.models.find((item) => item.id === nextModel);
    setModelId(nextModel);
    if (next?.voices[0]) {
      setVoiceId(next.voices[0].id);
      const preferred = next.voices[0].languages;
      if (Array.isArray(preferred) && preferred[0]) setLanguage(preferred[0]);
    }
    setAudioUrl((current) => { if (current) URL.revokeObjectURL(current); return null; });
  };

  const runGeneration = useCallback(async (inputText: string, selected = selectedVoice, selectedLanguage = language) => {
    if (!selected || !inputText.trim()) return;
    setLoading(true);
    setPageError('');
    try {
      const generated = await api.generateStudioSpeech({
        text: inputText,
        model_id: modelId,
        voice_id: selected.id,
        language: selectedLanguage,
        speed,
      });
      if (!generated.audio_base64) throw new Error('आवाज़ मिली, लेकिन चलाने योग्य ऑडियो नहीं मिला।');
      const bytes = Uint8Array.from(atob(generated.audio_base64), (character) => character.charCodeAt(0));
      const nextUrl = URL.createObjectURL(new Blob([bytes], { type: generated.audio_content_type || 'audio/wav' }));
      setAudioUrl((current) => { if (current) URL.revokeObjectURL(current); return nextUrl; });
      setActiveGeneration({
        id: generated.id, text_input: generated.text, language: generated.language,
        model_id: generated.model_id, voice_id: generated.voice_id, status: generated.status,
        latency_ms: generated.latency_ms, created_at: generated.created_at,
      });
      setHistory((current) => [{
        id: generated.id, text_input: generated.text, language: generated.language,
        model_id: generated.model_id, voice_id: generated.voice_id, status: generated.status,
        latency_ms: generated.latency_ms, created_at: generated.created_at,
      }, ...current.filter((item) => item.id !== generated.id)].slice(0, 30));
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'ऑडियो तैयार नहीं हुआ। फिर कोशिश करें।');
    } finally {
      setLoading(false);
    }
  }, [language, modelId, selectedVoice, speed]);

  const chooseVoice = (voice: SpeechVoice) => {
    setVoiceId(voice.id);
    if (Array.isArray(voice.languages) && voice.languages[0]) setLanguage(voice.languages[0]);
  };

  const setFavorite = (id: string) => {
    const next = favorites.includes(id) ? favorites.filter((item) => item !== id) : [...favorites, id];
    setFavorites(next);
    localStorage.setItem('mazdoormitra_voice_favorites', JSON.stringify(next));
  };

  const insertTag = (tag: string) => {
    const cursor = document.querySelector<HTMLTextAreaElement>('#studio-text')?.selectionStart ?? text.length;
    const next = `${text.slice(0, cursor)}${tag} ${text.slice(cursor)}`;
    setText(next);
    requestAnimationFrame(() => {
      const input = document.querySelector<HTMLTextAreaElement>('#studio-text');
      input?.focus();
      input?.setSelectionRange(cursor + tag.length + 1, cursor + tag.length + 1);
    });
  };

  const loadHistory = (item: VoiceHistoryItem) => {
    setText(item.text_input);
    setModelId(item.model_id);
    setVoiceId(item.voice_id);
    setLanguage(item.language);
    setActiveGeneration(item);
    setAudioUrl(null);
  };

  const deleteHistory = async (id: string) => {
    try {
      await api.deleteVoiceHistory(id);
      setHistory((items) => items.filter((item) => item.id !== id));
      if (activeGeneration?.id === id) {
        setActiveGeneration(null);
        setAudioUrl((current) => { if (current) URL.revokeObjectURL(current); return null; });
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : 'इतिहास हटाया नहीं जा सका।');
    }
  };

  const downloadAudio = () => {
    if (!audioUrl) return;
    const link = document.createElement('a');
    link.href = audioUrl;
    link.download = `mazdoormitra-${voiceId.toLowerCase()}.wav`;
    link.click();
  };

  if (authLoading || !isAuthenticated || loadingCapabilities) {
    return <div className="mx-auto flex min-h-[60vh] max-w-5xl items-center justify-center text-zinc-500" role="status"><LoaderCircle className="mr-2 h-5 w-5 animate-spin" /> स्टूडियो तैयार हो रहा है…</div>;
  }

  return (
    <div className="mx-auto w-full max-w-[1440px] px-4 pb-8 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-zinc-200 pb-5">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-zinc-500"><Mic2 className="h-4 w-4" /> आवाज़ कार्यशाला</div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-950 sm:text-4xl">Voice Studio</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-600">अपना संदेश लिखें, आवाज़ चुनें और असली Gnani Timbre ऑडियो सुनें।</p>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-600">
          <div className="flex items-center gap-2 font-semibold text-zinc-900"><span className={`h-2 w-2 rounded-full ${capabilities?.timbre.configured ? 'bg-emerald-600' : 'bg-zinc-400'}`} /> {capabilities?.timbre.configured ? 'Timbre access configured' : 'Timbre is not configured'}</div>
          <p className="mt-1">v3.0 · 13 प्रकाशित आवाज़ें · {capabilities?.timbre.v3_account_verification === 'previous_live_smoke_passed' ? 'real API smoke passed' : 'account smoke not verified'}</p>
        </div>
      </header>

      {pageError && <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900" role="alert">{pageError}</div>}

      <div className="grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)_280px]">
        <aside className="space-y-4" aria-label="आवाज़ चुनें">
          <section className="rounded-2xl border border-zinc-200 bg-white p-4">
            <label htmlFor="model-select" className="mb-2 block text-xs font-bold uppercase tracking-wide text-zinc-500">मॉडल</label>
            <div className="relative">
              <select id="model-select" value={modelId} onChange={(event) => updateModel(event.target.value)} className="h-11 w-full appearance-none rounded-lg border border-zinc-200 bg-zinc-50 px-3 pr-8 text-sm font-semibold text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-800">
                {capabilities?.timbre.models.map((model) => <option key={model.id} value={model.id}>{model.id.replace('timbre-', 'Timbre ')}</option>)}
              </select><ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-zinc-500" />
            </div>
            <div className="mt-4 flex items-center justify-between"><h2 className="text-sm font-semibold text-zinc-950">आवाज़ें</h2><span className="text-xs text-zinc-500">{voices.length} voices</span></div>
            <div className="mt-3 space-y-2">
              {voices.map((voice) => <VoiceCard key={voice.id} voice={voice} selected={voice.id === selectedVoice?.id} favorite={favorites.includes(voice.id)} onSelect={() => chooseVoice(voice)} onFavorite={() => setFavorite(voice.id)} onPreview={() => void runGeneration(SAMPLE, voice, Array.isArray(voice.languages) ? (voice.languages[0] ?? language) : language)} loading={loading && voice.id === voiceId} />)}
            </div>
          </section>
        </aside>

        <main className="min-w-0 space-y-4">
          <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="text-lg font-semibold text-zinc-950">अपना टेक्स्ट लिखें</h2><p className="mt-1 text-sm text-zinc-500">नंबर और रुपये को बोलचाल के शब्दों में लिखने से उच्चारण बेहतर रहता है।</p></div>
              <button type="button" onClick={() => setText(SAMPLE)} className="min-h-10 rounded-lg border border-zinc-200 px-3 text-sm font-semibold text-zinc-700 hover:bg-zinc-50">नमूना</button>
            </div>
            <label htmlFor="studio-text" className="sr-only">आवाज़ बनाने के लिए टेक्स्ट</label>
            <textarea id="studio-text" value={text} onChange={(event) => setText(event.target.value)} maxLength={4000} rows={10} placeholder="यहाँ वह संदेश लिखें जिसे सुनना चाहते हैं…" className="w-full resize-y rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-base leading-8 text-zinc-950 placeholder:text-zinc-400 focus-visible:ring-2 focus-visible:ring-zinc-800" />
            <div className="mt-2 flex items-center justify-between text-xs text-zinc-500"><span>यह टेक्स्ट आपके Voice Studio इतिहास में सेव होगा। आप उसे कभी भी हटा सकते हैं।</span><span>{characterCount}/4000</span></div>
            {tagsAvailable && <div className="mt-5 border-t border-zinc-100 pt-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-800"><Sparkles className="h-4 w-4" /> बोलने का अंदाज़ <span className="rounded bg-zinc-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-zinc-600">v3 only</span></div>
              <div className="flex flex-wrap gap-2">
                {capabilities?.timbre.audio_tags.map((tag) => <button key={tag} type="button" onClick={() => insertTag(tag)} className="min-h-9 rounded-lg border border-zinc-200 bg-white px-2.5 text-xs font-medium text-zinc-700 hover:bg-zinc-100" aria-label={`${tag} tag डालें`}>{tag}</button>)}
              </div>
            </div>}
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button type="button" disabled={loading || !text.trim()} onClick={() => void runGeneration(text)} className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-zinc-900 px-5 text-sm font-bold text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50">
                {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}{loading ? 'आवाज़ बन रही है…' : 'आवाज़ बनाएं'}
              </button>
              <button type="button" onClick={() => setText('')} disabled={!text} className="min-h-12 rounded-xl px-4 text-sm font-semibold text-zinc-600 hover:bg-zinc-100 disabled:opacity-40">टेक्स्ट मिटाएँ</button>
              {activeGeneration && <span className="inline-flex items-center gap-1.5 text-xs text-zinc-500"><Check className="h-4 w-4 text-emerald-700" /> {activeGeneration.latency_ms ?? '—'} ms में बनी</span>}
            </div>
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-5" aria-label="तैयार ऑडियो">
            <div className="mb-3 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-semibold text-zinc-900"><Volume2 className="h-4 w-4" /> तैयार ऑडियो</div>{audioUrl && <button type="button" onClick={downloadAudio} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-zinc-200 px-3 text-sm font-semibold text-zinc-700 hover:bg-zinc-50"><Download className="h-4 w-4" /> डाउनलोड</button>}</div>
            {audioUrl ? <audio ref={audioRef} controls src={audioUrl} className="w-full" aria-label={`${selectedVoice?.id ?? ''} द्वारा बनाया गया ऑडियो`} /> : <div className="flex min-h-20 items-center justify-center rounded-xl border border-dashed border-zinc-200 bg-zinc-50 text-center text-sm text-zinc-500">ऑडियो बनाने के बाद यहाँ सुनें।</div>}
            {activeGeneration && <p className="mt-3 text-xs text-zinc-500">{activeGeneration.model_id} · {activeGeneration.voice_id} · {LANGUAGES[activeGeneration.language] ?? activeGeneration.language}</p>}
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-white p-4 sm:p-5">
            <div className="mb-4 flex items-center justify-between"><div><h2 className="text-base font-semibold text-zinc-950">हाल की आवाज़ें</h2><p className="mt-1 text-xs text-zinc-500">आपके खाते में सेव किया गया टेक्स्ट रिकॉर्ड। ऑडियो फ़ाइल सर्वर पर नहीं रखी जाती।</p></div><Clock3 className="h-4 w-4 text-zinc-500" /></div>
            {history.length ? <ul className="divide-y divide-zinc-100">{history.slice(0, 5).map((item) => <li key={item.id} className="flex items-center gap-3 py-3">
              <button type="button" onClick={() => loadHistory(item)} className="min-w-0 flex-1 rounded-lg text-left hover:bg-zinc-50">
                <span className="block truncate text-sm font-medium text-zinc-900">{item.text_input}</span>
                <span className="mt-1 block text-xs text-zinc-500">{item.voice_id} · {item.model_id} · {new Date(item.created_at).toLocaleString('hi-IN')}</span>
              </button>
              <button type="button" onClick={() => loadHistory(item)} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-zinc-600 hover:bg-zinc-100" aria-label="इस टेक्स्ट को फिर से खोलें"><Play className="h-4 w-4" /></button>
              <button type="button" onClick={() => void deleteHistory(item.id)} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-zinc-500 hover:bg-red-50 hover:text-red-700" aria-label="इतिहास से हटाएँ"><Trash2 className="h-4 w-4" /></button>
            </li>)}</ul> : <p className="rounded-lg bg-zinc-50 px-4 py-5 text-sm text-zinc-500">आपकी बनाई हुई आवाज़ें यहाँ दिखेंगी।</p>}
          </section>
        </main>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-zinc-200 bg-white p-4">
            <button type="button" onClick={() => setSettingsOpen((open) => !open)} aria-expanded={settingsOpen} className="flex min-h-10 w-full items-center justify-between text-left xl:cursor-default">
              <span className="text-sm font-semibold text-zinc-950">आवाज़ सेटिंग</span><ChevronDown className={`h-4 w-4 text-zinc-500 transition xl:hidden ${settingsOpen ? 'rotate-180' : ''}`} />
            </button>
            <div className={`${settingsOpen ? 'block' : 'hidden'} mt-4 space-y-5 xl:block`}>
              <div>
                <label htmlFor="language-select" className="mb-2 block text-xs font-bold uppercase tracking-wide text-zinc-500">भाषा</label>
                <select id="language-select" value={language} onChange={(event) => setLanguage(event.target.value)} className="h-11 w-full rounded-lg border border-zinc-200 bg-white px-3 text-sm text-zinc-900 focus-visible:ring-2 focus-visible:ring-zinc-800">
                  {modelId === 'timbre-v3.0' && <option value="auto">Auto detect · mixed text</option>}
                  {availableLanguages.map((code) => <option key={code} value={code}>{LANGUAGES[code] ?? code}</option>)}
                </select>
                {language === 'auto' && <p className="mt-2 text-xs leading-5 text-zinc-500">यह सुविधा मिश्रित भाषा के लिए है; आवाज़ मॉडल लिपि देखकर भाषा पहचानता है।</p>}
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between"><label htmlFor="speed-range" className="text-xs font-bold uppercase tracking-wide text-zinc-500">बोलने की गति</label><span className="rounded-md bg-zinc-100 px-2 py-1 text-xs font-semibold tabular-nums text-zinc-700">{speed.toFixed(2)}×</span></div>
                <input id="speed-range" type="range" min={capabilities?.timbre.speed.min ?? 0.85} max={capabilities?.timbre.speed.max ?? 1.15} step="0.05" value={speed} onChange={(event) => setSpeed(Number(event.target.value))} className="w-full accent-zinc-900" />
                <div className="mt-1 flex justify-between text-[11px] text-zinc-500"><span>धीमी</span><span>सामान्य</span><span>तेज़</span></div>
              </div>
              <div className="border-t border-zinc-100 pt-4">
                <div className="text-xs font-bold uppercase tracking-wide text-zinc-500">चुनी आवाज़</div>
                <div className="mt-2 text-sm font-semibold text-zinc-950">{selectedVoice?.id ?? '—'}</div>
                <div className="mt-1 text-xs leading-5 text-zinc-600">{selectedVoice?.persona ?? ''}</div>
                <p className="mt-2 text-xs leading-5 text-zinc-500">{selectedVoice?.description ?? ''}</p>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900"><Sparkles className="h-4 w-4" /> असली AI, स्पष्ट हिसाब</div>
            <p className="mt-2 text-xs leading-5 text-zinc-600">हर ऑडियो अनुरोध Gnani Timbre को भेजा जाता है। विलंब समय इसी अनुरोध से मापा जाता है; कोई गुणवत्ता स्कोर नहीं बनाया जाता।</p>
            <p className="mt-3 border-t border-zinc-200 pt-3 text-xs leading-5 text-zinc-600">{capabilities?.evon.reason}</p>
          </section>
        </aside>
      </div>
    </div>
  );
}

function VoiceCard({ voice, selected, favorite, onSelect, onFavorite, onPreview, loading }: {
  voice: SpeechVoice; selected: boolean; favorite: boolean; onSelect: () => void; onFavorite: () => void; onPreview: () => void; loading: boolean;
}) {
  return <article className={`rounded-xl border p-3 transition ${selected ? 'border-zinc-900 bg-zinc-50 ring-1 ring-zinc-900' : 'border-zinc-200 bg-white hover:border-zinc-400'}`}>
    <button type="button" onClick={onSelect} aria-pressed={selected} className="w-full text-left">
      <span className="flex items-center justify-between"><span className="text-sm font-semibold text-zinc-950">{voice.id}</span>{selected && <Check className="h-4 w-4 text-zinc-800" />}</span>
      <span className="mt-1 block text-xs text-zinc-500">{voice.gender === 'female' ? 'महिला आवाज़' : 'पुरुष आवाज़'} · {voice.persona}</span>
      <span className="mt-2 block text-xs leading-5 text-zinc-600">{voice.description}</span>
    </button>
    <div className="mt-2 flex items-center justify-between border-t border-zinc-100 pt-2">
      <button type="button" onClick={onPreview} disabled={loading} className="inline-flex min-h-8 items-center gap-1.5 rounded-md px-2 text-xs font-semibold text-zinc-700 hover:bg-zinc-200 disabled:opacity-50" aria-label={`${voice.id} आवाज़ का वास्तविक नमूना सुनें`}>
        {loading ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />} सुनें
      </button>
      <button type="button" onClick={onFavorite} aria-pressed={favorite} aria-label={favorite ? `${voice.id} पसंद से हटाएँ` : `${voice.id} पसंद में जोड़ें`} className={`flex h-8 w-8 items-center justify-center rounded-md hover:bg-zinc-200 ${favorite ? 'text-red-700' : 'text-zinc-500'}`}><Heart className={`h-4 w-4 ${favorite ? 'fill-current' : ''}`} /></button>
    </div>
  </article>;
}
