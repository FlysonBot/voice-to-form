import { useEffect, useRef } from 'react';
import type { ReplyAnim } from '../../hooks/useReplyPlayer';
import { useT } from '../../i18n/strings';
import type { ChatMessage } from '../../types';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

interface Props {
  messages: ChatMessage[];
  typing: boolean;
  anim: ReplyAnim | null;
  listening: boolean;
  liveUserText: string;
  onReplay?: (text: string) => void;
}

export default function ChatWindow({ messages, typing, anim, listening, liveUserText, onReplay }: Props) {
  const t = useT();
  const box = useRef<HTMLDivElement>(null);

  // Instant scroll: smooth scrolling stutters while text types out
  useEffect(() => {
    if (box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [messages.length, typing, anim?.shown, liveUserText, listening]);

  return (
    <div ref={box} className="flex flex-1 flex-col gap-3 overflow-y-auto p-4" aria-live="polite">
      {messages.map((m) => {
        const playing = anim?.id === m.id;
        return (
          <MessageBubble
            key={m.id}
            message={m}
            displayText={playing ? m.text.slice(0, anim.shown) : undefined}
            caret={playing}
            onReplay={m.role === 'assistant' && !playing && onReplay ? () => onReplay(m.text) : undefined}
          />
        );
      })}
      {typing && <TypingIndicator />}
      {listening && (
        <MessageBubble live message={{ role: 'user', text: liveUserText || t('listening') }} />
      )}
    </div>
  );
}
