# Success criteria (best guess, simulated judge; nothing published)

**One line:** the winner is the project a tired judge can retell in one sentence after seeing one unforgettable moment.

Fixed by user: criteria may be inferred; medical-paperwork helper is a *fallback only* (user thinks it is overdone); look for a more unique idea.

## Minimum (earns nothing, most serious entries pass)
- Live demo works on a real input; real problem; Gemini is used; submitted on time and on both tracks.

## What decides between good entries
- **The Moment:** one demo instant that gets a visible reaction.
- **The Retell Line:** a sentence a judge could say to another judge without notes.
- **A Named Person:** a specific user, not "people who struggle with X".
- **Can't Remove Gemini:** the idea breaks without Gemini's specific strength (image/audio/long context/structured output).

## Unknown
- Real rubric, number of judges, who they are, demo length, whether a Google rep judges Track 2.

## Comparison (simulated judge)
- Polished/interchangeable "CalmCampus" (wellness chat) vs rougher/memorable "Mold-to-Letter" (photo of housing problem -> Gemini drafts code-cited repair letter). Memorable one wins: has a Moment, a short retell line, a named person, and breaks without Gemini.
- Recipe: find the situation; messy real input; output is an action; deletion test; retell line <=15 words with a person.
- Deliverable: open on the person, Moment within 30s, real ugly input, retell line as title, Gemini role in one caption, name both tracks.
- Tests: hallway test (repeat it a minute later); deletion test (remove Gemini / remove the Moment).

## UPDATE 2026-11-07: rubric is now published (see event.md). Inferred criteria above are superseded where they differ.
- Impact is **San Diego-specific**; data grounding and a source citation are expected; ~3h45 of build time; judges include an entrepreneur, two SAP staff (practical/technical lens) and a startup growth intern (voice company; inference: voice ideas may resonate).

## Judges research (subagent, thin; 2026-11-07). Mostly inference from titles.
- Individuals could not be confidently identified online, so this is inference from roles only. Entrepreneur: likely values a real market and a believable user. SAP solutions/technical-service roles: likely value a clear customer problem, business value, reliability, and deployment/security thinking. Startup growth intern: likely values a clear user story and a message grasped in seconds.
- Inference: lead with SD user + live demo; be ready for "how would this be deployed/secured?"; keep wording plain for non-specialists.
