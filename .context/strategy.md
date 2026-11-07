# Strategy (inference, not from the pages)

- Seven hours total: one narrow, demo-able project on a real community problem, built with Gemini, with visible Copilot use. May target all three prizes if stacking is allowed (unconfirmed).
- Write a one-sentence pitch early; keep notes on how Copilot helped; working demo ~1 hour before end; rehearse.
- Ask at check-in: submission cutoff/format, rubric, track stacking.

## Open
- Decided: Tracks 1 + 2 (Overall + Gemini). Copilot track skipped.

## Candidate ideas (brainstormed 2026-11-07, all unverified/unchosen)
1. Parent Voice-to-Form: parent speaks in their language, Gemini fills an English school form. (recommended)
2. Pantry Bag: photo of food-pantry items -> meals using only what's there + user's equipment.
3. Scam Voicemail Decoder: upload suspicious voicemail/screenshot, Gemini explains tactics + safe next step.
4. Curb Check: photo of sidewalk/ramp barrier -> classified accessibility report drafted for the city.
5. Mold-to-Letter: photo of housing problem -> code-cited repair letter.
Fallback: medical paperwork helper (overdone per user).

## Past-submissions research (subagent, 3 standard searches, thin; 2026-11-07)
- No earlier edition of this event found. "Hack for Humanity" is a first-year global AI Collective civic hackathon (Sep 1-Oct 31, 2026, ~120 chapters). No winner recaps found.
- Crowded: scam detectors (Phish Eye, GOTCHA, Scammune, TrustGuard; Gemini itself is adding scam-call alerts). Moderate: tenant/housing (closest: OPSLY, voice+photo property management, not a code-cited letter). Nothing found for parent-language form filler or sidewalk/ramp report (thin search). Medical/document explainers: not searched, inferred common.
- Inference: photo-to-action ideas look least duplicated. ShorECheck-style clones likely.

## Round 2 ideas (San Diego-specific, unverified; 2026-11-07)
6. Paystub Wage Check: photo of paystub/schedule -> underpayment check vs CA/SD min wage rules + draft wage claim.
7. Street Vendor Check: photo of cart/stand -> compliance checklist vs CA street-vending/retail food rules.
8. Border Crossing Planner: Spanish voice question + CBP wait-time data -> when/where to cross.
9. Evac Plan: household details -> personalized wildfire evacuation plan from county zone data.
10. 211 Voice Navigator (Spanish): spoken need -> nearest resources.
Leaning: Mold-to-Letter (3.5 hours, strong SD fit); Paystub Wage Check is its same-shape sibling.

## TEAM PLAN (from teammates, 2026-11-07) - supersedes ideas list: voice-to-form for **SDG&E CARE** application
- Shared JSON contract agreed first (language, profile{field:{value,confidence,source}}, forms, missing_fields, confirmed, signature_png). Start with one form (SDG&E CARE); second form is stretch.
- 4 roles: (1) Form Engine: fillable CARE PDF, pypdf, field_map.json, fill_pdf(), Flask/FastAPI /fill /download. (2) Gemini: vision extraction of ID/paystub/bill with confidence, gap finder, answer parsing, structured output, <0.8 confidence -> user confirms. (3) Voice & language: picker/auto-detect, Gemini-written questions + TTS, browser audio -> Gemini transcribe -> parser, spoken recap. (4) Frontend + demo: screens (language > scan > voice questions > review > sign > download), big buttons, yellow low-confidence, signature pad, pitch ("12-year-old translator in City Heights"), fake ID/paystub, backup video.
- Claude's notes: SD fit solved (SDG&E + CARE). Verify FIRST: is the CARE form a fillable PDF? Is Gemini TTS available (docs checked only covered audio input -> text)? Compute missing_fields in code from the form's required list, not via Gemini. Tier the scope: must = voice -> JSON -> review -> filled PDF; should = language recap, doc scan; could = TTS, signature pad, 2nd form.
