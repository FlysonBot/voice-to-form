import type { Strings } from './en';

// Partial: missing keys fall back to English (see en.ts)
export const zh: Partial<Strings> = {
  appName: '福利助手',
  languageLabel: '语言',
  tagline: '用您的语言，获得您应得的帮助。',
  subtitle: '只需 5 分钟的对话，无需填写一大堆表格。我们为您找到适合的圣地亚哥福利项目，并帮您填写申请表。',
  chooseLanguage: '选择您的语言',
  otherLanguage: '其他',
  otherLanguageHint: '输入您的语言',
  otherLanguagePlaceholder: '例如：韩语、索马里语、俄语…',
  translating: '正在将网站翻译成您的语言…',
  start: '开始',
  trust: '签字前您会审阅所有内容。我们绝不会替您提交。',

  stepChat: '对话',

  chatPlaceholder: '输入您的回答…',
  send: '发送',
  chatError: '抱歉，出了点问题。请再试一次。',
  assistantTyping: '助手正在输入',
  listening: '正在聆听…',
  tapToStop: '点击停止',
  micLabel: '说出您的回答',
  voiceOn: '语音已开启',
  voiceOff: '语音已关闭',
  handsFree: '免提模式',
  replay: '再听一遍',
  noVoice: '此设备没有您所选语言的语音，回复将仅以文字显示。',
  micUnsupported: '此浏览器不支持语音输入。请使用 Chrome、Edge 或 Safari，或直接输入回答。',
  micBlocked: '麦克风已被阻止。请在浏览器设置中允许访问，或直接输入回答。',

  yourInfo: '已了解的信息',

  loading: '加载中…',

  continue: '继续',
  stepReview: '核对',
  stepChoose: '选择',
  edit: '编辑',
  save: '保存',
  cancel: '取消',
  whatNext: '您接下来想做什么？',
  findBenefitsTitle: '查找我符合条件的福利',
};
