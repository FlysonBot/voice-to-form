import type { Strings } from './en';

// Partial: missing keys fall back to English (see en.ts)
export const fr: Partial<Strings> = {
  appName: 'Aide aux Prestations',
  languageLabel: 'Langue',
  tagline: 'Obtenez l’aide à laquelle vous avez droit — dans votre langue.',
  subtitle: 'Une conversation de 5 minutes au lieu d’une pile de formulaires. Nous trouvons les programmes de San Diego qui vous correspondent et remplissons les demandes.',
  chooseLanguage: 'Choisissez votre langue',
  otherLanguage: 'Autre',
  otherLanguageHint: 'Saisissez votre langue',
  otherLanguagePlaceholder: 'ex. coréen, somali, russe…',
  translating: 'Traduction du site dans votre langue…',
  start: 'Commencer',
  trust: 'Vous vérifiez tout avant de signer. Nous ne soumettons jamais rien à votre place.',

  stepChat: 'Conversation',

  chatPlaceholder: 'Saisissez votre réponse…',
  send: 'Envoyer',
  chatError: 'Désolé, une erreur s’est produite. Veuillez réessayer.',
  assistantTyping: 'L’assistant écrit',
  listening: 'À l’écoute…',
  tapToStop: 'Touchez pour arrêter',
  micLabel: 'Dites votre réponse',
  voiceOn: 'Voix activée',
  voiceOff: 'Voix désactivée',
  handsFree: 'Mains libres',
  replay: 'Réécouter',
  noVoice: 'Cet appareil n’a pas de voix pour votre langue ; les réponses seront affichées en texte uniquement.',
  micUnsupported: 'La saisie vocale n’est pas disponible dans ce navigateur. Essayez Chrome, Edge ou Safari, ou tapez vos réponses.',
  micBlocked: 'Le micro est bloqué. Autorisez-le dans les paramètres du navigateur, ou tapez vos réponses.',

  yourInfo: 'Ce que nous savons',

  loading: 'Chargement…',

  continue: 'Continuer',
  stepReview: 'Vérifier',
  stepChoose: 'Choisir',
  edit: 'Modifier',
  save: 'Enregistrer',
  cancel: 'Annuler',
  whatNext: 'Que souhaitez-vous faire ?',
  findBenefitsTitle: 'Trouver les aides auxquelles j’ai droit',
};
