import { useT } from '../../i18n/strings';
import type { ChatMessage } from '../../types';
import { SpeakerIcon } from '../common/Icons';

interface Props {
  message: Pick<ChatMessage, 'role' | 'text'>;
  /** Partial text while the reply is still typing out */
  displayText?: string;
  caret?: boolean;
  /** Live speech transcript that hasn't been sent yet */
  live?: boolean;
  onReplay?: () => void;
}

export default function MessageBubble({ message, displayText, caret, live, onReplay }: Props) {
  const t = useT();
  const mine = message.role === 'user';
  const text = displayText ?? message.text;
  return (
    <div className={`flex items-end gap-1.5 ${mine ? 'justify-end' : 'justify-start'}`}>
      <div
        dir="auto"
        className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed ${
          mine ? 'rounded-ee-sm bg-teal-700 text-white' : 'rounded-es-sm bg-white text-stone-900 shadow-sm ring-1 ring-stone-200'
        } ${live ? 'opacity-70' : ''}`}
      >
        {live && <span className="me-2 inline-block h-2 w-2 animate-pulse rounded-full bg-red-400 align-middle" aria-hidden />}
        {text}
        {caret && <span className="ms-0.5 inline-block h-4 w-0.5 animate-pulse bg-stone-400 align-middle" aria-hidden />}
      </div>
      {onReplay && (
        <button
          onClick={onReplay}
          aria-label={t('replay')}
          title={t('replay')}
          className="mb-1 rounded-full p-1.5 text-stone-400 hover:bg-stone-200 hover:text-stone-700"
        >
          <SpeakerIcon className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
