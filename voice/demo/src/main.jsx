import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import VoiceDemo from "@voice/VoiceDemo";

createRoot(document.getElementById("root")).render(<StrictMode><VoiceDemo /></StrictMode>);
