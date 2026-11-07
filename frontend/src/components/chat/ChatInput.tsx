import { useState } from 'react';
import { useT } from '../../i18n/strings';
import { MicIcon, StopIcon } from '../common/Icons';

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
  micAvailable: boolean;
  listening: boolean;
  onMic: () => void;
}

/** Voice first: a big mic button. Typing is a small fallback behind "Type instead". */
export default function ChatInput({ onSend, disabled, micAvailable, listening, onMic }: Props) {
  const t = useT();
  const [typing, setTyping] = useState(!micAvailable);
  const [text, setText] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
  };

  return (
    <div className="border-t border-stone-200 bg-white p-3">
      <div className="flex items-center gap-3">
        {micAvailable && (
          <button
            type="button"
            onClick={onMic}
            disabled={disabled && !listening}
            aria-label={listening ? t('tapToStop') : t('micLabel')}
            aria-pressed={listening}
            className={`relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full shadow-sm transition disabled:opacity-40 ${
              listening ? 'bg-red-500 text-white' : 'bg-teal-700 text-white hover:bg-teal-800'
            }`}
          >
            {listening && <span className="absolute inset-0 animate-ping rounded-full bg-red-400 opacity-40" aria-hidden />}
            {listening ? <StopIcon className="relative h-6 w-6" /> : <MicIcon className="h-8 w-8" />}
          </button>
        )}

        {typing && !listening ? (
          <form onSubmit={submit} className="flex min-w-0 flex-1 gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={t('chatPlaceholder')}
              dir="auto"
              autoFocus
              className="min-h-12 min-w-0 flex-1 rounded-xl border border-stone-300 px-4 text-base outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
            />
            <button type="submit" disabled={disabled || !text.trim()} className="min-h-12 rounded-xl bg-teal-700 px-5 font-medium text-white disabled:opacity-40">
              {t('send')}
            </button>
          </form>
        ) : (
          <p className="flex-1 text-lg font-medium text-stone-700">{listening ? `${t('listening')} ${t('tapToStop')}` : t('micLabel')}</p>
        )}

        {micAvailable && !listening && (
          <button type="button" onClick={() => setTyping((v) => !v)} className="shrink-0 rounded-lg px-2 py-1 text-sm text-stone-500 underline-offset-2 hover:underline">
            {typing ? '🎤' : `⌨ ${t('typeInstead')}`}
          </button>
        )}
      </div>
    </div>
  );
}
