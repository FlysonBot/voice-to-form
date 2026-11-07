import { useT } from '../../i18n/strings';

/** Talk → Choose form → Questions → Check → Sign */
export default function ProgressSteps({ current }: { current: 0 | 1 | 2 | 3 | 4 }) {
  const t = useT();
  const steps = [t('stepChat'), t('stepChoose'), t('stepQuestions'), t('stepReview'), t('stepSign')];
  return (
    <ol className="mb-6 flex gap-1.5 text-xs sm:text-sm">
      {steps.map((label, i) => (
        <li key={i} className="flex min-w-0 flex-1 flex-col gap-1" aria-current={i === current ? 'step' : undefined}>
          <span className={`h-1.5 rounded-full ${i <= current ? 'bg-teal-600' : 'bg-stone-200'}`} />
          <span className={`truncate ${i === current ? 'font-medium text-teal-800' : 'text-stone-500'}`}>{label}</span>
        </li>
      ))}
    </ol>
  );
}
