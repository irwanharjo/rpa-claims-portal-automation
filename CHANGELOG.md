# Changelog

The public `robot_aps.py` is the July 2026 snapshot. The production robot kept evolving
(it grew roughly 4x in size); the code itself stays private because it is tightly bound to a
real client portal, but the engineering lessons are generic and are summarised here.

## 2026-08 → 2026-11 — Production hardening (summary, code not published)

- **Explicit waits instead of fixed `sleep()`** — clicks wait for the element to be ready, and
  dropdowns wait until their options have actually loaded before a value is chosen.
- **Auto-submit with gates** — an on-screen toggle (applies immediately, no restart) lets the
  robot submit on its own. Each document passes three independent gates first — attachments
  present, stamp-duty rule satisfied, entered total equals the source amount — and any failing
  gate turns auto-submit off for that document and hands it back to the operator.
- **Submission verified, not assumed** — after submitting, the robot looks the document up again
  and only marks it done when the portal shows it as sent.
- **Duplicate-submission dialog** — the portal's "already submitted" dialog is handled by one
  dedicated routine; generic popup handling is forbidden from clicking it.
- **End-of-queue retry pass** — when the main queue is empty, failed documents get one more
  pass, checking the portal's claim history first so nothing is submitted twice.
- **Stale ticks cleared** — rows left ticked from the previous document are unticked before new
  rows are selected.
- **Tolerant name matching** — the portal masks part of participant names, so names are compared
  with a normaliser (titles, punctuation, masked characters) on top of ID + date + amount.
- **Plausible-date window** — an invoice date read from the PDF must fall inside a window that
  respects the contractual billing limit; otherwise it is only offered as a suggestion in the
  human confirmation popup.
- **Browser popup suppression** — Chrome's password-leak dialog is prevented at launch (see
  `browser_hardening.py` in the `rpa-invoice-journal-print-automation` repo).

## 2026-07 — Initial public version

- Excel → portal claim entry with triple-lock verification (ID + date + amount), dual-track
  flow, dual-ID support, human-in-the-loop date confirmation, archive-on-success.
