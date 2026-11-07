# Event facts (from the MLH pages)

- **Name:** AIC at UC San Diego Hack for Humanity; host: The AI Collective at UCSD (student-led chapter of a global nonprofit); registration via MLH Organizer HQ.
- **When:** Sat 2026-11-07, 11:00 AM-6:00 PM PST (single day). Page showed "1 day left" to register.
- **Where:** UCSD Price Center Theater, 3135 Matthews Ln, La Jolla, CA 92093. In person.
- **Format:** Beginner-friendly AI hackathon; solo or teams (no stated size limit); build an AI solution to a community challenge; ends with showcase to judging panel.
- **Steps:** Register -> Check in -> Submit Project.
- **Eligibility:** Aimed at university students; "requirements can vary". No experience needed. Cost not stated (appears free).

## Tracks
1. **Best Overall Project - Hack for Humanity** (event prize): social impact (healthcare, education, essential resources, accessibility/inclusion, climate/sustainability). AI encouraged, not required.
2. **Best Use of the Google Gemini API** (Google): e.g. personalized-advice chatbot, paper summarizer, creative content generator.
3. **Best Use of GitHub Copilot** (event prize): judged on "how they used Copilot creatively and effectively throughout development"; must show what was built and how Copilot was used.

## Unknown / not published
- Judging rubric (except Copilot line), prize amounts, submission cutoff and format, demo length, whether one project can enter multiple tracks, rules on pre-existing code, team-size limit, Devpost/Discord (none found).
- Whether registration is still open.

## Corrections from kickoff slides (photos in ~/Data/Downloads/LocalSend, taken 2026-11-07 ~11:30-11:40; supersede the web pages)
- **Solo not allowed: teams of min 3.** User joined a team of 4.
- **Schedule:** 11:00 opening, 11:30 hacking begins, **3:30 PM projects due**, 4:00-5:30 demos + judging (demo + Q&A per team), 5:30 awards, 6:00 cleanup. (Web pages implied 6 PM; wrong.)
- **Published rubric (5 criteria):** Impact (does it matter for **San Diego**?), Technical (does it actually work?), Creativity (fresh idea?), Use of AI (is AI doing real work?), Demo (can you explain it clearly?). "A live demo beats slides. Lead with the problem."
- **Judges (roles only):** an entrepreneur affiliated with UCSD's MRSEC; two SAP staff (a solutions advisor and a principal technical service manager); a growth intern at VoiceOS.
- **Organizers' example "ShorECheck":** pick a SD beach, plain-English safety answer grounded in county water-quality advisories; "hits all 3 tracks". Likely to be cloned by other teams -> avoid.
- **Good-problem checklist:** real nameable person; pain showable in 30s; data you can get today; AI does something a form can't; core buildable in ~4 hours. "One user. One core flow. One strong demo."
- **Architecture hint:** Streamlit UI -> code adds data + instructions -> Gemini API -> JSON (status, reason, source). Ground in real data; ask for JSON.
- **Toolkit:** Gemini API (free key, Google AI Studio), Antigravity + Gemini CLI, GitHub Copilot, Streamlit/Gradio, San Diego open data, Vercel/Render (deploy before demo).
