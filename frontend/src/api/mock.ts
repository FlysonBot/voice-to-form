// In-browser stand-in for the backend (VITE_API_MODE=local), FAKE DATA ONLY.
// Deliberately rigid: fixed questions in a fixed order. Gemini makes the real one conversational.
// A few values come back with confidence < 0.8 on purpose so the yellow "please confirm" UI shows.
import type {
  AnswerResponse,
  ChatMessage,
  ExtractResponse,
  FieldSource,
  GapsResponse,
  LangCode,
  OnboardingTurnResponse,
  Profile,
  ProfileField,
  ProgramsResponse,
  QuestionResponse,
  RecapResponse,
  Session,
} from '../types';

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
type L = Partial<Record<LangCode, string>> & { en: string };
const say = (t: L, l: LangCode) => t[l] ?? t.en;
const field = (value: unknown, confidence: number, source: FieldSource = 'onboarding_voice'): ProfileField => ({ value, confidence, source });

const WORDS: Record<string, number> = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  uno: 1, una: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9, diez: 10,
  'một': 1, hai: 2, ba: 3, 'bốn': 4, 'năm': 5, 'sáu': 6, 'bảy': 7, 'tám': 8, 'chín': 9, 'mười': 10,
};
function num(s: string): number | undefined {
  const m = s.replace(/,/g, '').match(/\d+(\.\d+)?/);
  if (m) return Number(m[0]);
  for (const w of s.toLowerCase().split(/[^\p{L}]+/u)) if (w in WORDS) return WORDS[w];
  return undefined;
}
const isSkip = (s: string) => /\b(skip|saltar|omitir|paso|bỏ qua|laktawan)\b/i.test(s);

// ─── Onboarding ──────────────────────────────────────────────────────────────
interface Step { key: string; q: L; parse: (a: string) => ProfileField | null; optional?: boolean }
const STEPS: Step[] = [
  {
    key: 'full_name',
    q: { en: 'What is your full legal name?', es: '¿Cuál es su nombre legal completo?', vi: 'Họ và tên đầy đủ của bạn là gì?' },
    // Names heard by voice are hard to spell: low confidence → user confirms in the recap
    parse: (a) => (a.trim().length > 1 ? field(a.trim().replace(/^(me llamo|soy|my name is|i'm|tôi tên là)\s+/i, ''), 0.7) : null),
  },
  {
    key: 'household_size',
    q: {
      en: 'Who lives with you? How many people in total, including you?',
      es: '¿Quién vive con usted? ¿Cuántas personas en total, contándose usted?',
      vi: 'Ai sống cùng bạn? Tổng cộng bao nhiêu người, kể cả bạn?',
    },
    parse: (a) => (num(a) ? field(num(a), 0.95) : null),
  },
  {
    key: 'address',
    q: { en: 'What is your home address?', es: '¿Cuál es la dirección de su casa?', vi: 'Địa chỉ nhà của bạn là gì?' },
    parse: (a) => (a.trim().length > 4 ? field(a.trim(), 0.85) : null),
  },
  {
    key: 'phone',
    q: { en: 'What is a good phone number for you?', es: '¿A qué número de teléfono le podemos llamar?', vi: 'Số điện thoại của bạn là gì?' },
    parse: (a) => {
      const d = a.replace(/\D/g, '');
      return d.length >= 7 ? field(d.replace(/^(\d{3})(\d{3})(\d{4})$/, '($1) $2-$3'), 0.9) : null;
    },
  },
  {
    key: 'monthly_income',
    optional: true,
    q: {
      en: 'About how much does your household earn per month, before taxes? You can say "skip".',
      es: '¿Aproximadamente cuánto gana su hogar al mes, antes de impuestos? Puede decir "saltar".',
      vi: 'Hộ gia đình bạn kiếm khoảng bao nhiêu mỗi tháng, trước thuế? Bạn có thể nói "bỏ qua".',
    },
    parse: (a) => (num(a) !== undefined ? field(num(a), 0.9) : null),
  },
  {
    key: 'current_benefits',
    q: {
      en: 'Do you already get CalFresh, Medi-Cal, WIC, or SSI?',
      es: '¿Ya recibe CalFresh, Medi-Cal, WIC o SSI?',
      vi: 'Bạn có đang nhận CalFresh, Medi-Cal, WIC hoặc SSI không?',
    },
    parse: (a) => {
      const s = a.toLowerCase().replace(/[\s-]/g, '');
      return field(['calfresh', 'medi-cal', 'wic', 'ssi'].filter((b) => s.includes(b.replace('-', ''))), 0.9);
    },
  },
];

const GREETING: L = {
  en: 'Hi! I’ll ask you a few questions, one at a time. You only have to tell us once. ',
  es: '¡Hola! Le haré unas preguntas, una a la vez. Solo tiene que decírnoslo una vez. ',
  vi: 'Xin chào! Tôi sẽ hỏi bạn vài câu, từng câu một. Bạn chỉ cần nói một lần. ',
};
const RETRY: L = { en: 'Sorry, I didn’t catch that. ', es: 'Perdón, no le entendí. ', vi: 'Xin lỗi, tôi chưa nghe rõ. ' };
const DONE: L = {
  en: 'Thank you! That’s everything I need for now.',
  es: '¡Gracias! Eso es todo lo que necesito por ahora.',
  vi: 'Cảm ơn bạn! Vậy là đủ thông tin rồi.',
};

export async function onboardingTurn(session: Session, messages: ChatMessage[], text: string | null): Promise<OnboardingTurnResponse> {
  await delay(700);
  const lang = session.language;
  if (!messages.some((m) => m.role === 'user') && !text) {
    return { reply: say(GREETING, lang) + say(STEPS[0].q, lang), done: false };
  }
  // Ask about the first field we haven't heard about (a scanned ID may have filled some)
  const pending = STEPS.filter((s) => !(s.key in session.profile));
  const current = pending[0];
  if (!current) return { reply: say(DONE, lang), done: true };

  const answer = text ?? '';
  let update: ProfileField | null = null;
  if (current.optional && isSkip(answer)) update = field('', 1);
  else update = current.parse(answer);
  if (!update) return { reply: say(RETRY, lang) + say(current.q, lang), transcript: text, done: false };

  const next = pending[1];
  return {
    transcript: text,
    profile_updates: { [current.key]: update },
    reply: next ? say(next.q, lang) : say(DONE, lang),
    done: !next,
  };
}

// ─── Document photo (fake ID / pay stub / bill) ──────────────────────────────
export async function extract(docType: 'id' | 'pay_stub' | 'bill'): Promise<ExtractResponse> {
  await delay(1500);
  if (docType === 'id') {
    return {
      fields: {
        full_name: field('MARIA ELENA LOPEZ', 0.95, 'id_photo'),
        date_of_birth: field('1988-04-12', 0.9, 'id_photo'),
        address: field('4021 University Ave Apt 3, San Diego, CA 92105', 0.72, 'id_photo'),
      },
    };
  }
  if (docType === 'pay_stub') {
    return {
      fields: {
        monthly_income: field(2850, 0.85, 'document'),
        pay_frequency: field('every 2 weeks', 0.9, 'document'),
        income_sources: field(['job'], 0.9, 'document'),
      },
    };
  }
  return { fields: { address: field('4021 University Ave Apt 3, San Diego, CA 92105', 0.9, 'document') } };
}

// ─── Path B: programs ───────────────────────────────────────────────────────
export async function findPrograms(session: Session): Promise<ProgramsResponse> {
  await delay(1200);
  const lang = session.language;
  return {
    suggested_programs: [
      {
        name: 'SDG&E CARE',
        form_id: 'sdge_care',
        source_url: 'https://www.sdge.com/care',
        why: say({
          en: 'A monthly discount on your SDG&E energy bill. Based on your household size and income, you may qualify. SDG&E makes the final decision.',
          es: 'Un descuento mensual en su factura de SDG&E. Según el tamaño de su hogar y sus ingresos, podría calificar. SDG&E toma la decisión final.',
          vi: 'Giảm giá hằng tháng cho hóa đơn điện SDG&E. Dựa trên số người và thu nhập, bạn có thể đủ điều kiện. SDG&E quyết định cuối cùng.',
        }, lang),
      },
      {
        name: 'CalFresh',
        form_id: null,
        source_url: 'https://www.cdss.ca.gov/calfresh',
        why: say({
          en: 'Monthly money for groceries on an EBT card. You may qualify; the county decides.',
          es: 'Dinero mensual para comida en una tarjeta EBT. Podría calificar; el condado decide.',
          vi: 'Tiền mua thực phẩm hằng tháng qua thẻ EBT. Bạn có thể đủ điều kiện; quận sẽ quyết định.',
        }, lang),
      },
    ],
  };
}

// ─── Gap filling ────────────────────────────────────────────────────────────
// Fields the CARE form needs (placeholder until P1 publishes the real field list)
const FORM_NEEDS: Record<string, string[]> = {
  sdge_care: ['full_name', 'address', 'phone', 'household_size', 'monthly_income', 'sdge_account_number'],
};

export async function formGaps(session: Session, formId: string): Promise<GapsResponse> {
  await delay(500);
  const p = session.profile;
  return { missing_fields: (FORM_NEEDS[formId] ?? []).filter((k) => p[k]?.value == null || p[k]?.value === '') };
}

const QUESTIONS: Record<string, L> = {
  sdge_account_number: {
    en: 'What is your SDG&E account number? It’s at the top of your bill. You can also say "leave it blank".',
    es: '¿Cuál es su número de cuenta de SDG&E? Está arriba en su factura. También puede decir "déjelo en blanco".',
    vi: 'Số tài khoản SDG&E của bạn là gì? Số này ở phía trên hóa đơn. Bạn cũng có thể nói "để trống".',
  },
  monthly_income: {
    en: 'About how much does your household earn per month, before taxes?',
    es: '¿Aproximadamente cuánto gana su hogar al mes, antes de impuestos?',
    vi: 'Hộ gia đình bạn kiếm khoảng bao nhiêu mỗi tháng, trước thuế?',
  },
};

export async function voiceQuestion(session: Session, fieldKey: string): Promise<QuestionResponse> {
  await delay(400);
  const step = STEPS.find((s) => s.key === fieldKey);
  const q = QUESTIONS[fieldKey] ?? step?.q ?? { en: `What is your ${fieldKey.replace(/_/g, ' ')}?` };
  return { text: say(q, session.language) };
}

export async function voiceAnswer(fieldKey: string, text: string | null): Promise<AnswerResponse> {
  await delay(600);
  const a = (text ?? '').trim();
  if (fieldKey === 'sdge_account_number') {
    const d = a.replace(/\D/g, '');
    return { value: d || null, confidence: 0.7, transcript: a }; // long numbers by voice: confirm
  }
  if (['household_size', 'monthly_income'].includes(fieldKey)) return { value: num(a) ?? null, confidence: 0.85, transcript: a };
  return { value: a || null, confidence: 0.85, transcript: a };
}

// ─── Recap ──────────────────────────────────────────────────────────────────
export async function recap(session: Session): Promise<RecapResponse> {
  await delay(500);
  const p: Profile = session.profile;
  const items = Object.entries(p)
    .filter(([, f]) => f.value !== null && f.value !== '')
    .map(([k, f]) => ({ field: k, label: k, value: f.value, needs_confirm: f.confidence < 0.8 }));
  const intro: L = {
    en: 'Let’s check your form together. Fields in yellow need your OK.',
    es: 'Revisemos su formulario juntos. Los campos en amarillo necesitan su confirmación.',
    vi: 'Hãy cùng kiểm tra đơn. Những ô màu vàng cần bạn xác nhận.',
  };
  return { items, text: say(intro, session.language) };
}

// ─── Filled PDF (placeholder: a plain one-page PDF listing the values) ───────
export async function fillForm(session: Session, formId: string): Promise<Blob> {
  await delay(800);
  const lines = [
    `${formId.toUpperCase()} - MOCK PREVIEW (fake data, not the real form)`,
    '',
    ...Object.entries(session.profile)
      .filter(([, f]) => f.value !== null && f.value !== '')
      .map(([k, f]) => `${k}: ${typeof f.value === 'object' ? JSON.stringify(f.value) : String(f.value)}`),
    '',
    session.signature_png ? 'Signature: [captured]' : 'Signature: (none)',
  ];
  return simplePdf(lines);
}

/** Minimal valid one-page PDF with Helvetica text (Latin-1 only; other characters become "?") */
function simplePdf(lines: string[]): Blob {
  const esc = (s: string) => s.replace(/[^\x20-\xff]/g, '?').replace(/([\\()])/g, '\\$1');
  const content = ['BT', '/F1 11 Tf', '50 760 Td', '14 TL', ...lines.map((l) => `(${esc(l)}) '`), 'ET'].join('\n');
  const objs = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
  ];
  let out = '%PDF-1.4\n';
  const offsets: number[] = [];
  objs.forEach((o, i) => {
    offsets.push(out.length);
    out += `${i + 1} 0 obj\n${o}\nendobj\n`;
  });
  const xref = out.length;
  out += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n${offsets.map((o) => `${String(o).padStart(10, '0')} 00000 n \n`).join('')}`;
  out += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return new Blob([Uint8Array.from(out, (c) => c.charCodeAt(0) & 0xff)], { type: 'application/pdf' });
}
