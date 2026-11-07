import type { Key } from './i18n/locales/en';
import type { HouseholdMember, Profile } from './types';

export const CONFIDENCE_THRESHOLD = 0.8;

/**
 * Labels for profile keys we know about. The backend owns the schema, so unknown keys
 * still display (humanized). Order here is the order they show in the sidebar.
 */
export const FIELD_LABELS: Record<string, Key> = {
  // Keys agreed in API.md (gemini/profile_fields.py): names and addresses are split.
  first_name: 'f_first_name',
  middle_name: 'f_middle_name',
  last_name: 'f_last_name',
  full_name: 'f_full_name',
  date_of_birth: 'f_date_of_birth',
  phone: 'f_phone',
  email: 'f_email',
  address_street: 'f_address_street',
  address_unit: 'f_address_unit',
  address_city: 'f_address_city',
  address_zip: 'f_address_zip',
  address: 'f_address',
  mailing_address: 'f_mailing_address',
  housing_status: 'f_rent_or_own',
  rent_or_own: 'f_rent_or_own',
  monthly_housing_cost: 'f_housing_cost',
  housing_cost: 'f_housing_cost',
  household_size: 'f_household_size',
  household_members: 'f_household_members',
  income_amount: 'f_income_amount',
  income_frequency: 'f_pay_frequency',
  pay_frequency: 'f_pay_frequency',
  monthly_income: 'f_monthly_income',
  income_sources: 'f_income_sources',
  benefits_calfresh: 'f_benefits_calfresh',
  benefits_medi_cal: 'f_benefits_medi_cal',
  benefits_wic: 'f_benefits_wic',
  benefits_ssi: 'f_benefits_ssi',
  benefits_school_meals: 'f_benefits_school_meals',
  current_benefits: 'f_current_benefits',
  sdge_account_number: 'f_sdge_account_number',
};

/** What the onboarding sidebar tracks (the core of "tell us once") */
export const ONBOARDING_KEYS = [
  'first_name', 'last_name', 'date_of_birth', 'phone', 'address_street', 'address_city', 'address_zip',
  'household_size', 'household_members', 'monthly_income',
];

export const humanize = (key: string) => key.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

export function labelFor(key: string, t: (k: Key) => string) {
  const k = FIELD_LABELS[key];
  return k ? t(k) : humanize(key);
}

/** Turn any field value (string, number, list, members…) into one readable line. */
export function formatValue(v: unknown): string {
  if (v === null || v === undefined || v === '') return '';
  if (Array.isArray(v)) {
    return v
      .map((item) => {
        if (item && typeof item === 'object' && 'first_name' in item) {
          const m = item as HouseholdMember;
          return [m.first_name, m.relationship && `(${m.relationship})`].filter(Boolean).join(' ');
        }
        return formatValue(item);
      })
      .filter(Boolean)
      .join(', ');
  }
  if (typeof v === 'boolean') return v ? '✓' : '✗';
  if (typeof v === 'object') {
    return Object.values(v as Record<string, unknown>).map(formatValue).filter(Boolean).join(', ');
  }
  return String(v);
}

export const isFilled = (p: Profile, key: string) => {
  const v = p[key]?.value;
  return v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && v.length === 0 && key !== 'current_benefits');
};

export const needsConfirm = (p: Profile, key: string) => isFilled(p, key) && (p[key]?.confidence ?? 0) < CONFIDENCE_THRESHOLD;

/** Only plain text/number values can be edited by typing on the review screen. */
export const isEditable = (v: unknown) => v === null || v === undefined || typeof v === 'string' || typeof v === 'number';
