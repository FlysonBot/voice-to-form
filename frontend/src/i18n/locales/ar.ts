import type { Strings } from './en';

// Partial: missing keys fall back to English (see en.ts)
export const ar: Partial<Strings> = {
  appName: 'مساعد المزايا',
  languageLabel: 'اللغة',
  tagline: 'احصل على المساعدة التي تستحقها — بلغتك.',
  subtitle: 'محادثة مدتها 5 دقائق بدلًا من كومة من النماذج. نجد لك برامج سان دييغو المناسبة ونملأ الطلبات نيابةً عنك.',
  chooseLanguage: 'اختر لغتك',
  otherLanguage: 'لغة أخرى',
  otherLanguageHint: 'اكتب لغتك',
  otherLanguagePlaceholder: 'مثلًا: الكورية، الصومالية، الروسية…',
  translating: 'جارٍ ترجمة الموقع إلى لغتك…',
  start: 'ابدأ',
  trust: 'ستراجع كل شيء قبل التوقيع. لن نقدّم أي طلب نيابةً عنك أبدًا.',

  stepChat: 'المحادثة',

  chatPlaceholder: 'اكتب إجابتك…',
  send: 'إرسال',
  chatError: 'عذرًا، حدث خطأ ما. يُرجى المحاولة مرة أخرى.',
  assistantTyping: 'المساعد يكتب',
  listening: 'جارٍ الاستماع…',
  tapToStop: 'اضغط للإيقاف',
  micLabel: 'قل إجابتك',
  voiceOn: 'الصوت مفعّل',
  voiceOff: 'الصوت متوقف',
  handsFree: 'بدون استخدام اليدين',
  replay: 'استمع مرة أخرى',
  noVoice: 'لا يتوفر صوت للغتك على هذا الجهاز، لذا ستظهر الردود كنص فقط.',
  micUnsupported: 'الإدخال الصوتي غير متاح في هذا المتصفح. جرّب Chrome أو Edge أو Safari، أو اكتب إجاباتك.',
  micBlocked: 'الميكروفون محظور. اسمح بالوصول إليه من إعدادات المتصفح، أو اكتب إجاباتك.',

  yourInfo: 'ما عرفناه عنك',

  loading: 'جارٍ التحميل…',

  continue: 'متابعة',
  stepReview: 'المراجعة',
  stepChoose: 'الاختيار',
  edit: 'تعديل',
  save: 'حفظ',
  cancel: 'إلغاء',
  whatNext: 'ماذا تريد أن تفعل؟',
  findBenefitsTitle: 'ابحث عن المزايا التي أستحقها',
};
