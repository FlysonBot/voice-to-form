# FE-09: End-to-end test and visual QA (`tests/test_e2e.py`)
Wave 2 (after FE-08 and FE-07) · Depends on: all · Size: medium · Read first: `../00-contract.md`

**Goal:** prove the whole engine works through HTTP and that the filled PDF looks right.

**Write only:** `form_engine/tests/test_e2e.py` (scratch PNGs in the scratchpad/temp dir)

**Do**
1. Test through a throwaway `FastAPI()` app including `form_engine.routes.router`: `POST /form/fill` with `mock_session.json` + `test_signature.png` (base64) returns a PDF; also with `?mock=true`; also with a sparse session (only `full_name`) returns a valid PDF with no crash.
2. Assert on text: the PDF text contains the fake name, address, account number, `38,400`, today's date; a benefit not in the profile is not marked. Assert page count 1.
3. **Visual QA (required):** render the filled PDF to PNG (`pdftoppm -r 110 -png`) and **look at it** with the Read tool. Check each filled value sits on its line, check marks are inside the right boxes (CalFresh and NSLP in 2A, wages in 2B, Email contact), the signature sits on the signature line and does not cover printed text, no text overlaps printed text. Also view the sparse-session output.
4. If something is misplaced: do NOT edit other tickets' files. Report the key, what is wrong, the current coordinates (from `sdge_care.layout.json`) and your suggested correction.

**Acceptance:** `uv run pytest form_engine/tests/test_e2e.py` passes. Final report lists: tests run, PNG paths viewed, and a defect list (or "none").
