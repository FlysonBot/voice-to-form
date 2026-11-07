// Fixed UI strings for the voice screens. Gemini writes everything else in the user's language.
const STRINGS = {
  en: {
    start: "Start", tapToTalk: "Tap to talk", listening: "Listening…", thinking: "One moment…",
    speaking: "Tap to answer now", repeat: "Repeat", skip: "Skip", scan: "Scan a document",
    didntHear: "I didn't hear anything. Tap the microphone and try again.", tryAgain: "Try again",
    micBlocked: "Please allow the microphone so we can talk.", youSaid: "You said",
    goBack: "That's wrong — go back", allCorrect: "Everything is correct", isCorrect: "Correct",
    edit: "Edit", save: "Save", notSure: "Please check this", noStore: "We don't store your information.",
    leftBlank: "Left blank — you can write it on the paper form", question: "Question",
  },
  es: {
    start: "Empezar", tapToTalk: "Toque para hablar", listening: "Escuchando…", thinking: "Un momento…",
    speaking: "Toque para contestar ya", repeat: "Repetir", skip: "Saltar", scan: "Escanear un documento",
    didntHear: "No escuché nada. Toque el micrófono e intente otra vez.", tryAgain: "Intentar otra vez",
    micBlocked: "Por favor permita el micrófono para poder hablar.", youSaid: "Usted dijo",
    goBack: "Eso está mal — regresar", allCorrect: "Todo está correcto", isCorrect: "Correcto",
    edit: "Editar", save: "Guardar", notSure: "Por favor revise esto", noStore: "No guardamos su información.",
    leftBlank: "En blanco — puede escribirlo en el formulario de papel", question: "Pregunta",
  },
  zh: {
    start: "开始", tapToTalk: "点击说话", listening: "正在听…", thinking: "请稍等…",
    speaking: "点击立即回答", repeat: "重复", skip: "跳过", scan: "扫描证件",
    didntHear: "我没有听到声音。请点击麦克风再试一次。", tryAgain: "再试一次",
    micBlocked: "请允许使用麦克风。", youSaid: "您说",
    goBack: "说错了 — 返回", allCorrect: "全部正确", isCorrect: "正确",
    edit: "修改", save: "保存", notSure: "请检查这一项", noStore: "我们不会保存您的信息。",
    leftBlank: "留空 — 您可以在纸质表格上填写", question: "问题",
  },
  vi: {
    start: "Bắt đầu", tapToTalk: "Chạm để nói", listening: "Đang nghe…", thinking: "Xin chờ một chút…",
    speaking: "Chạm để trả lời ngay", repeat: "Nhắc lại", skip: "Bỏ qua", scan: "Quét giấy tờ",
    didntHear: "Tôi không nghe thấy gì. Hãy chạm vào micro và thử lại.", tryAgain: "Thử lại",
    micBlocked: "Vui lòng cho phép dùng micro.", youSaid: "Bạn đã nói",
    goBack: "Sai rồi — quay lại", allCorrect: "Tất cả đều đúng", isCorrect: "Đúng",
    edit: "Sửa", save: "Lưu", notSure: "Vui lòng kiểm tra mục này", noStore: "Chúng tôi không lưu thông tin của bạn.",
    leftBlank: "Để trống — bạn có thể viết vào mẫu giấy", question: "Câu hỏi",
  },
};

export const ui = (lang) => STRINGS[lang] || STRINGS.en;
