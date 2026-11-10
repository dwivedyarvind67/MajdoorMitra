'use client';

import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Loader2, Mic, Square, X } from 'lucide-react';

interface VoiceRecorderProps {
  onRecordingComplete: (blob: Blob) => void | Promise<void>;
  isProcessing?: boolean;
  isReady?: boolean;
}

const MAX_RECORDING_SECONDS = 60;
const TARGET_SAMPLE_RATE = 16000;

export default function VoiceRecorder({ onRecordingComplete, isProcessing, isReady = true }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const cancelledRef = useRef(false);
  const durationRef = useRef(0);

  const clearTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
  };

  const stopTracks = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  useEffect(() => () => {
    clearTimer();
    stopTracks();
  }, []);

  const startRecording = async () => {
    setError(null);
    chunksRef.current = [];
    cancelledRef.current = false;

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('इस ब्राउज़र में आवाज़ रिकॉर्ड नहीं हो सकती। कृपया आधुनिक ब्राउज़र इस्तेमाल करें।');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      streamRef.current = stream;
      const mimeOptions = [
        'audio/webm;codecs=opus',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        'audio/webm',
      ];
      const mimeType = mimeOptions.find((candidate) => MediaRecorder.isTypeSupported(candidate));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setError('रिकॉर्डिंग में समस्या हुई। कृपया फिर से कोशिश करें।');
        cancelledRef.current = true;
        clearTimer();
        stopTracks();
        setIsRecording(false);
      };
      recorder.onstop = async () => {
        clearTimer();
        stopTracks();
        setIsRecording(false);
        if (cancelledRef.current) return;
        const recorded = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
        if (!recorded.size) {
          setError('आवाज़ रिकॉर्ड नहीं हुई। माइक पास रखकर फिर से बोलें।');
          return;
        }
        try {
          const wav = await convertToWav(recorded);
          await onRecordingComplete(wav);
        } catch {
          setError('आवाज़ तैयार नहीं हो पाई। कृपया छोटी रिकॉर्डिंग लेकर फिर कोशिश करें।');
        }
      };

      recorder.start(200);
      durationRef.current = 0;
      setDuration(0);
      setIsRecording(true);
      timerRef.current = setInterval(() => {
        const nextDuration = durationRef.current + 1;
        durationRef.current = nextDuration;
        setDuration(nextDuration);
        if (nextDuration >= MAX_RECORDING_SECONDS) {
          const activeRecorder = recorderRef.current;
          if (activeRecorder && activeRecorder.state !== 'inactive') activeRecorder.stop();
        }
      }, 1000);
    } catch {
      stopTracks();
      setError('माइक की अनुमति नहीं मिली। ब्राउज़र सेटिंग में माइक चालू करके फिर कोशिश करें।');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    clearTimer();
  };

  const cancelRecording = () => {
    cancelledRef.current = true;
    chunksRef.current = [];
    clearTimer();
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    stopTracks();
    setIsRecording(false);
    setDuration(0);
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const remaining = seconds % 60;
    return `${mins}:${remaining.toString().padStart(2, '0')}`;
  };

  return (
    <section className="flex flex-col items-center rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-sm">
      {error && (
        <div role="alert" className="mb-4 flex w-full items-start gap-2 rounded-xl bg-red-50 p-3 text-left text-sm text-red-800">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      <div className="relative my-3">
        {isRecording && <div className="absolute -inset-3 animate-pulse rounded-full bg-red-100" aria-hidden="true" />}
        <button
          type="button"
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing || !isReady}
          aria-label={isRecording ? 'रिकॉर्डिंग रोकें' : 'आवाज़ रिकॉर्ड करें'}
          aria-pressed={isRecording}
          className={`relative z-10 flex h-32 w-32 flex-col items-center justify-center rounded-full shadow-lg transition-transform focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500 ${
            isRecording ? 'bg-red-700 text-white' : 'bg-blue-700 text-white hover:scale-105 active:scale-95'
          }`}
        >
          {isProcessing ? <Loader2 className="h-12 w-12 animate-spin" aria-hidden="true" /> : isRecording ? <Square className="h-10 w-10 fill-current" aria-hidden="true" /> : <Mic className="h-14 w-14" aria-hidden="true" />}
          <span className="mt-1 text-sm font-bold">{isProcessing ? 'जाँच रहे हैं' : isRecording ? 'रोकें' : 'बोलें'}</span>
        </button>
      </div>

      <div className="mt-2 min-h-12" role="status" aria-live="polite" aria-atomic="true">
        {isRecording ? (
          <div className="space-y-1">
            <div className="flex items-center justify-center gap-2 text-red-700">
              <span className="h-3 w-3 animate-pulse rounded-full bg-red-700" aria-hidden="true" />
              <span className="font-mono text-xl font-bold">{formatDuration(duration)}</span>
            </div>
            <p className="text-sm text-slate-700">बोलिए… अधिकतम 1 मिनट</p>
          </div>
        ) : isProcessing ? (
          <p className="text-base font-semibold text-blue-800">आवाज़ की जाँच हो रही है…</p>
        ) : !isReady ? (
          <p className="text-base font-semibold text-slate-600">सत्र तैयार हो रहा है…</p>
        ) : (
          <p className="text-base font-semibold text-slate-800">माइक दबाएँ और अपनी मज़दूरी बोलें</p>
        )}
      </div>

      {isRecording && (
        <button
          type="button"
          onClick={cancelRecording}
          className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-full border border-slate-300 bg-slate-50 px-5 text-sm font-bold text-slate-700 hover:bg-slate-100"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          रद्द करें
        </button>
      )}
    </section>
  );
}

async function convertToWav(blob: Blob): Promise<Blob> {
  const audioContext = new AudioContext();
  let decoded: AudioBuffer;
  try {
    decoded = await audioContext.decodeAudioData(await blob.arrayBuffer());
  } finally {
    await audioContext.close();
  }

  const outputLength = Math.max(1, Math.floor(decoded.length * TARGET_SAMPLE_RATE / decoded.sampleRate));
  const samples = new Int16Array(outputLength);
  const channels = Array.from({ length: decoded.numberOfChannels }, (_, index) => decoded.getChannelData(index));
  for (let index = 0; index < outputLength; index += 1) {
    const sourceIndex = Math.min(decoded.length - 1, Math.floor(index * decoded.sampleRate / TARGET_SAMPLE_RATE));
    let sample = 0;
    for (const channel of channels) sample += channel[sourceIndex] ?? 0;
    sample = Math.max(-1, Math.min(1, sample / channels.length));
    samples[index] = Math.round(sample < 0 ? sample * 0x8000 : sample * 0x7fff);
  }

  const dataBytes = samples.length * 2;
  const buffer = new ArrayBuffer(44 + dataBytes);
  const view = new DataView(buffer);
  const writeText = (offset: number, value: string) => {
    for (let index = 0; index < value.length; index += 1) view.setUint8(offset + index, value.charCodeAt(index));
  };
  writeText(0, 'RIFF');
  view.setUint32(4, 36 + dataBytes, true);
  writeText(8, 'WAVE');
  writeText(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, TARGET_SAMPLE_RATE, true);
  view.setUint32(28, TARGET_SAMPLE_RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeText(36, 'data');
  view.setUint32(40, dataBytes, true);
  samples.forEach((sample, index) => view.setInt16(44 + index * 2, sample, true));
  return new Blob([buffer], { type: 'audio/wav' });
}
