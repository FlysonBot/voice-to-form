# Form engine backlog (P1)

Goal: `POST /form/fill` takes a confirmed profile + `form_id` + signature and returns the filled SDG&E CARE PDF.
Form facts (checked 1:25 PM): `sdge_care.pdf` is **not fillable** (0 fields, no XFA, 1 page, 612x792), so we draw text with `reportlab` and merge with `pypdf`.

Implementation is split into subagent tickets in `tickets/` (see `README.md`, `00-contract.md`). This checklist is the owner's human view; items below map to tickets: 2=FE-01, 3-4=FE-02, 5=FE-03+FE-05+FE-08, 6=FE-06, 7=FE-04, 8=FE-07, 14=FE-09.

Status: [ ] todo, [~] doing, [x] done. Mark the date/time when you finish something.

## Must have, by Checkpoint 1 (2:00 PM): a filled PDF downloads from a fake profile

- [x] **1. Get the blank form.** `form_engine/sdge_care.pdf` (Form 142-740, rev 0326). *Done: file exists.*
- [ ] **2. Field list for P2** (~1:40). `form_engine/sdge_care.fields.json`: the profile keys the form needs. Push, then message P2 with the path.
  - Contact: name, home phone, mobile phone, address (street/apt, city, ZIP), email, SDG&E account number
  - Household: adults, children, total
  - Section 2A benefit checkboxes: CalFresh, CalWORKs/TANF, LIHEAP, Medi-Cal, NSLP, SSI, WIC, Tribal TANF, Head Start, BIA General Assistance
  - Section 2B income-source checkboxes (12) and total annual household income
  - Contact preference (email or mail), signature, date
  - *Done when:* P2 confirms they can read it.
- [ ] **3. Find coordinates for every box.** Render the page (`pdftoppm`) or read text positions with `pypdf`, and note x/y for each text field and checkbox. *Done when:* every key in item 2 has a position.
- [ ] **4. Field map.** `form_engine/sdge_care.field_map.json`: profile key -> page, x, y, kind (text/checkbox), font size, optional transform. *Done when:* every key from item 2 is in it.
- [ ] **5. Fill function.** `fill_form(session, form_id, signature_png) -> bytes`: overlay with `reportlab`, merge onto the blank with `pypdf`. Read only `.value`; leave missing blank. *Done when:* the output opens and text sits inside the boxes (check by eye).
- [ ] **6. Fake profile + mock.** One fake profile (fake name/address) used by tests and by `?mock=true`. No real data.
- [ ] **7. Signature stamping.** Decode the base64 PNG, scale to the signature line, draw it. *Done when:* a test PNG appears on the line.
- [ ] **8. `POST /form/fill`.** Request: `{session, form_id, signature_png}`. Response: `application/pdf`. Supports `?mock=true`. Written as a router inside `form_engine/` so wiring into the app is one line. *Done when:* a request returns a PDF that opens.

## Should have, by Checkpoint 2 (2:45 PM): works with the real flow

- [ ] **9. Data transforms.** Adults/children from household members (by date of birth); monthly income x 12 to annual; phone formatting; today's date; English/Latin characters only.
- [ ] **10. Checkbox logic.** Map benefits flags and income sources from the profile to the right boxes. Unknown means unchecked.
- [ ] **11. Rules.** Leave immigration/citizenship fields blank (this form has none). Never invent a value.
- [ ] **12. Edge cases.** Long text shrinks or truncates to fit the box; missing values leave blank without crashing.
- [ ] **13. Errors.** Unknown `form_id` or bad base64 returns the shared error shape. Never return a half-filled file.
- [ ] **14. Test.** `pytest` fills from the fake profile and checks the PDF opens and has one page. No personal info in logs.
- [ ] **15. Confirm with others.** P4: base64 signature in, file download out. P2: they can use the field list. Mark `/form/fill` as AGREED in `API.md`.

## Could have, only if ahead of schedule

- [ ] **16. Preview without signature** (`signature_png` null).
- [ ] **17. Second form** (CalFresh) using the same field-map format. Needs its own PDF and fillable check first.
- [ ] **18. Help others** (wire the entry file, demo run, fake documents, backup video) after 2:45.

## Needs a decision from the team (not yours alone)

- Profile key names and who writes the schema. Item 2 is the draft.
- Entry file that wires all routers together.
- Whether the upload option is cut (supported forms only).

## Cut order if behind

Items 16-18 first, then 12, then 9-10 simplified (hardcode demo values). Never cut 5, 7, 8.
