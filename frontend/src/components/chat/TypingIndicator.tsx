import { useT } from '../../i18n/strings';

export default function TypingIndicator() {
  const t = useT();
  return (
    <div className="flex justify-start" aria-label={t('assistantTyping')}>
      <div className="flex gap-1 rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-stone-200">
        {[0, 150, 300].map((d) => (
          <span key={d} className="h-2 w-2 animate-bounce rounded-full bg-stone-400" style={{ animationDelay: `${d}ms` }} />
        ))}
      </div>
    </div>
  );
}
