// Forms the form engine (P1) can fill. Only SDG&E CARE is real today; the rest are stretch goals.
export interface SupportedForm {
  id: string;
  name: string;
  agency: string;
  ready: boolean;
}

export const SUPPORTED_FORMS: SupportedForm[] = [
  { id: 'sdge_care', name: 'SDG&E CARE', agency: 'SDG&E', ready: true },
  { id: 'calfresh', name: 'CalFresh', agency: 'County of San Diego', ready: false },
  { id: 'sdusd_meals', name: 'Free / reduced-price school meals', agency: 'San Diego Unified', ready: false },
  { id: 'mts_pronto_life', name: 'MTS PRONTO reduced fare', agency: 'MTS', ready: false },
];

export const formName = (id: string | null | undefined) => SUPPORTED_FORMS.find((f) => f.id === id)?.name ?? id ?? '';
export const isFormReady = (id: string | null | undefined) => !!SUPPORTED_FORMS.find((f) => f.id === id)?.ready;
