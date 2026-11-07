import type { KnownLang, LangCode } from '../types';

// Locale codes the browser's speech engines understand (BCP-47)
const PRESET: Record<KnownLang, string> = {
  en: 'en-US',
  es: 'es-US',
  vi: 'vi-VN',
  tl: 'fil-PH',
  zh: 'zh-CN',
  ar: 'ar-SA',
  fr: 'fr-FR',
};

// Names people might type into "Other", in English or their own script
const BY_NAME: [RegExp, string][] = [
  [/^(english|ingl[eé]s)$/, 'en-US'],
  [/^(spanish|espa[nñ]ol)$/, 'es-US'],
  [/^(vietnamese|ti[eế]ng vi[eệ]t)$/, 'vi-VN'],
  [/^(tagalog|filipino)$/, 'fil-PH'],
  [/^(chinese|mandarin|中文|普通话|國語|国语)$/, 'zh-CN'],
  [/^(cantonese|廣東話|广东话|粵語|粤语)$/, 'zh-HK'],
  [/^(taiwanese mandarin)$/, 'zh-TW'],
  [/^(arabic|العربية|عربي)$/, 'ar-SA'],
  [/^(french|fran[cç]ais)$/, 'fr-FR'],
  [/^(korean|한국어|조선말)$/, 'ko-KR'],
  [/^(japanese|日本語)$/, 'ja-JP'],
  [/^(russian|русский)$/, 'ru-RU'],
  [/^(ukrainian|українська)$/, 'uk-UA'],
  [/^(somali|soomaali)$/, 'so-SO'],
  [/^(farsi|persian|فارسی)$/, 'fa-IR'],
  [/^(dari|دری)$/, 'fa-AF'],
  [/^(pashto|پښتو)$/, 'ps-AF'],
  [/^(urdu|اردو)$/, 'ur-PK'],
  [/^(hindi|हिन्दी|हिंदी)$/, 'hi-IN'],
  [/^(punjabi|ਪੰਜਾਬੀ)$/, 'pa-IN'],
  [/^(gujarati|ગુજરાતી)$/, 'gu-IN'],
  [/^(bengali|bangla|বাংলা)$/, 'bn-BD'],
  [/^(nepali|नेपाली)$/, 'ne-NP'],
  [/^(portuguese|portugu[eê]s)$/, 'pt-BR'],
  [/^(german|deutsch)$/, 'de-DE'],
  [/^(italian|italiano)$/, 'it-IT'],
  [/^(polish|polski)$/, 'pl-PL'],
  [/^(turkish|t[uü]rk[cç]e)$/, 'tr-TR'],
  [/^(armenian|հայերեն)$/, 'hy-AM'],
  [/^(hebrew|עברית)$/, 'he-IL'],
  [/^(khmer|cambodian|ខ្មែរ)$/, 'km-KH'],
  [/^(lao|ລາວ)$/, 'lo-LA'],
  [/^(thai|ไทย)$/, 'th-TH'],
  [/^(burmese|myanmar|မြန်မာ)$/, 'my-MM'],
  [/^(indonesian|bahasa indonesia)$/, 'id-ID'],
  [/^(malay|bahasa melayu)$/, 'ms-MY'],
  [/^(amharic|አማርኛ)$/, 'am-ET'],
  [/^(tigrinya|ትግርኛ)$/, 'ti-ER'],
  [/^(swahili|kiswahili)$/, 'sw-KE'],
  [/^(haitian creole|krey[oò]l)$/, 'ht-HT'],
  [/^(kurdish|kurd[iî])$/, 'ku-TR'],
  [/^(hmong)$/, 'hmn'],
];

/** Converts an app language (preset code or typed-in name) into a speech locale, or undefined if unknown. */
export function toBcp47(lang: LangCode | undefined): string | undefined {
  if (!lang) return undefined;
  if (lang in PRESET) return PRESET[lang as KnownLang];
  const name = lang.trim().toLowerCase();
  for (const [re, code] of BY_NAME) if (re.test(name)) return code;
  // Someone typed a code directly, e.g. "ko" or "pt-BR"
  if (/^[a-z]{2,3}(-[a-z0-9]{2,4})?$/i.test(name)) return lang.trim();
  return undefined;
}

const base = (tag: string) => tag.replace('_', '-').toLowerCase().split('-')[0];
const ALIASES: Record<string, string[]> = { fil: ['fil', 'tl'], tl: ['tl', 'fil'] };

// Closest regional fallback when the exact locale has no voice (e.g. US Spanish → Mexican Spanish)
const NEAR: Record<string, string[]> = { 'es-us': ['es-mx', 'es-419'], 'fa-af': ['fa-ir'], 'zh-hk': ['yue-hk'] };
// macOS ships joke/novelty voices that sound wrong for a benefits assistant
const NOVELTY = /grandma|grandpa|rocko|bubbles|albert|bad news|good news|bells|boing|cellos|jester|organ|superstar|trinoids|whisper|wobble|zarvox|bahh|fred|junior|ralph|kathy|eddy|flo|reed|sandy|shelley/i;

/** Best voice for a locale: exact match, then nearby region, then same language; prefers natural-sounding voices. */
export function pickVoice(voices: SpeechSynthesisVoice[], bcp47: string): SpeechSynthesisVoice | undefined {
  const want = bcp47.toLowerCase();
  const norm = (v: SpeechSynthesisVoice) => v.lang.replace('_', '-').toLowerCase();
  const bases = ALIASES[base(want)] ?? [base(want)];
  const near = NEAR[want] ?? [];
  const score = (v: SpeechSynthesisVoice) => {
    const l = norm(v);
    if (l !== want && !near.includes(l) && !bases.includes(base(l))) return -Infinity; // wrong language
    let s = l === want ? 100 : near.includes(l) ? 60 : 20;
    if (/google|natural|premium|enhanced/i.test(v.name)) s += 10;
    if (NOVELTY.test(v.name)) s -= 15;
    return s;
  };
  let best: SpeechSynthesisVoice | undefined;
  for (const v of voices) if (score(v) > -Infinity && (!best || score(v) > score(best))) best = v;
  return best;
}
