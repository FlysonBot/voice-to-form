import { useT } from '../../i18n/strings';
import { SpeakerIcon, SpeakerOffIcon } from '../common/Icons';

export default function VoiceToggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  const t = useT();
  return (
    <button
      onClick={onToggle}
      aria-pressed={on}
      className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition ${
        on ? 'bg-teal-50 text-teal-800 ring-1 ring-teal-200' : 'bg-stone-100 text-stone-500 ring-1 ring-stone-200'
      }`}
    >
      {on ? <SpeakerIcon className="h-4 w-4" /> : <SpeakerOffIcon className="h-4 w-4" />}
      {on ? t('voiceOn') : t('voiceOff')}
    </button>
  );
}
