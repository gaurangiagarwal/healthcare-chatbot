# MediReach Final Validation Checklist

**Status: NOT VALIDATED FOR RELEASE.** The project's `db.sqlite3` is unverified. This checklist is a plan for a separately approved validation effort; do not run it against that file. No item below should be marked complete based only on source inspection.

## 0. Approval and isolation gate

- [ ] Agree on a database recovery/retention plan with the data owner. Do not inspect, copy, restore, or migrate the current database until that plan is approved.
- [ ] Identify a known-good backup if one exists; do not assume one exists or restore one without approval.
- [ ] Establish an isolated disposable database and verify the effective database URL before any Django command. Ensure tests, local runs, and CI cannot target the protected project database.
- [ ] Confirm the target database backend and version. Review migration support for conditional unique constraints, check constraints, JSON fields, and `select_for_update` behavior.
- [ ] Configure a unique secret, allowed hosts, HTTPS, secure cookies, static-file handling, and production environment settings without exposing secrets.

## 1. Static source and migration review

- [x] Parse migration `0004_provider_data_foundation.py` as Python source; repair its affiliation date-constraint syntax.
- [ ] On an approved isolated environment, compare migration state with current model declarations using Django's migration tooling.
- [ ] Review migration operation order, dependencies, generated SQL, constraint/index names, reverse operations, and backend behavior.
- [ ] Confirm the six provider models and additive Doctor/Hospital fields, owner constraints, verification constraints, indexes, and through relationships.
- [ ] Review deployment settings, secret handling, debug mode, host configuration, logging, and static asset configuration.

## 2. Automated tests — isolated database only

- [ ] Run the full Django test suite with the isolated disposable database and capture the command, database target, and complete results.
- [ ] Run `python manage.py check` with explicit approved settings.
- [ ] Run `python manage.py makemigrations --check --dry-run` only after verifying the command cannot connect to or alter the protected project database.
- [ ] Confirm Ollama tests mock local HTTP calls and Overpass tests mock network calls. Tests must not depend on live local or public services.
- [ ] Review failures; do not remove tests or relax safety, ownership, or validation assertions to obtain a passing result.
- [ ] Exercise appointment conflict behavior against the target backend, including concurrent attempts for one slot.

## 3. Emergency and assistant browser checks

- [ ] Verify the welcome **Emergency medical assistance** prompt produces an emergency warning and visible `tel:112` action.
- [ ] Verify urgent warning signs bypass intent routing and Ollama; confirm the assistant says not to wait and does not claim to have contacted anyone.
- [ ] Check negated, historical, hypothetical, and ordinary requests against the intended screening behavior.
- [ ] Walk through the symptom questions one at a time, confirm answered details are not repeated, and test stopping the flow.
- [ ] Test Ollama configured, unavailable, timed out, malformed, and rejected-output paths without sending provider facts, booking status, coordinates, or emergency decisions as authority.
- [ ] Confirm chat history remains isolated by patient, and browser coordinates are not persisted in conversation state or messages.

## 4. Provider discovery and map browser checks

- [ ] Verify doctor search, structured and legacy specialties, current-only affiliations, detail links, trust labels, and empty states against known records.
- [ ] Verify facility search and filters against known records, including invalid and missing coordinates.
- [ ] Verify exact `/api/providers/discover` request/response shapes and managed-versus-OSM source separation.
- [ ] With explicit user action, test nearby discovery success, empty results, invalid coordinates/radius, timeout, HTTP errors, and rate limiting.
- [ ] Inspect browser console and network panel for Leaflet, CSS/JS, tile requests, API responses, and initialization errors.
- [ ] Verify OSM attribution is present for OSM-derived results, external links are safe, and a usable list remains when Leaflet, tiles, or Overpass fails.
- [ ] Confirm no mapped result appears verified, open, available, or accepting patients without supported current data.

## 5. Care workflows, ownership and administrator checks

- [ ] Book a future local slot, try an expired slot, try another doctor's slot ID, and submit duplicate active bookings. Verify clear messages and no provider-confirmation claim.
- [ ] Verify appointment listing/cancellation and cross-patient denial.
- [ ] Submit a referral and enquiry; confirm selected facility retention, validation, local status, and explicit no-delivery wording.
- [ ] Verify one patient's dashboard, chat, notes, contacts, summaries, appointments, referrals, and enquiries never expose another patient's records.
- [ ] Verify anonymous enquiries cannot be tracked by a user account and are not described as delivered.
- [ ] Verify a facility administrator cannot read or update another facility's services, enquiries, referrals, or audit records.
- [ ] Verify valid status changes create audit records and malformed JSON/IDs return controlled client errors.

## 6. Responsive and accessible browser checks

- [ ] Test mobile and desktop navigation, active-page state, keyboard focus, Escape/backdrop close, and sign-in/sign-out/admin links.
- [ ] Test touch-sized controls, form labels/errors, disabled/loading/success states, and prevention of accidental repeat submissions.
- [ ] Test doctor cards, facility list/map fallback, chatbot messages and emergency CTA, request forms, dashboard, and administrator inbox at narrow viewport widths.
- [ ] Confirm chatbot model text is rendered as text, not interpreted as markup.

## 7. Release gate

- [ ] Review test, check, migration, browser, security, and privacy evidence with the team.
- [ ] Resolve all critical/high-severity findings and document accepted residual risks.
- [ ] Confirm database disposition and migration plan with the data owner.
- [ ] Confirm deployment does not enable debug mode or use the default secret and that patient-data retention/backup/incident policies exist.
- [ ] Obtain human approval before describing MediReach as ready for real patient use.
