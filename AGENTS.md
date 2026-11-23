# MediReach — AI Coding Agent Instructions

This file defines mandatory instructions for Codex and every other AI coding agent working on MediReach.

These rules apply to all tasks, regardless of who requests the change.

## 1. Project identity and vision

MediReach is a Django-based healthcare assistance and care-coordination platform.

Its long-term purpose is to combine:

- Emergency-first assistance.
- Structured symptom navigation.
- Basic first-aid information.
- Healthcare provider discovery.
- Location-aware facility search.
- Patient profiles and personal healthcare records.
- Appointment requests.
- Referrals and enquiries.
- Trustworthy provider information.
- A hybrid assistant with deterministic safety rules and optional local AI.

Do not confuse the long-term vision with the currently implemented application.

Read:
- README.md
- docs/MEDIREACH_PROJECT_MASTER_PLAN.md
- docs/ARCHITECTURE.md
- docs/FEATURES.md
- docs/API_REFERENCE.md
- docs/DATABASE_SCHEMA.md

Read relevant existing source files before changing anything.

## 2. Task scope

Work only on the task explicitly assigned.

Before editing:

1. Identify the requested phase.
2. Read its acceptance criteria.
3. Inspect existing implementation.
4. Identify shared files and dependencies.
5. List intended changes.
6. Identify database and security impact.
7. Avoid unrelated refactoring.

Do not independently expand the task.

Do not implement multiple future phases in one task.

If the task requires an architectural decision, explain the decision and wait for approval rather than inventing a new architecture.

## 3. Database protection

The project has an existing SQLite database with a reported modification incident.

A previous operation ran migrations and the demo seed command against the project database. Four fictional doctors and 168 slots were reported created. The database has not been inspected or restored.

Treat the database as modified and potentially containing important existing data.

NEVER run any of the following against the project database without explicit approval:

- `python manage.py migrate`
- `python manage.py makemigrations`
- `python manage.py flush`
- `python manage.py seed_demo`
- `python manage.py loaddata`
- Database deletion or replacement.
- Database reset or recreation.
- Direct SQL modification.
- Data cleanup scripts.
- Commands that silently initialize or alter a database.

Never assume that a command is safe because it is normally used during development.

Never delete db.sqlite3.

Never delete SQLite WAL or SHM files.

Never restore a backup without verifying the source backup and obtaining approval.

Before any approved database change:

1. Identify the exact database path.
2. Confirm whether it is the project database or a disposable test database.
3. Identify a known-good backup.
4. Explain the expected schema or data impact.
5. Review the migration.
6. Obtain explicit approval.
7. Verify the result using an isolated and controlled procedure.

If a database operation is not necessary for the task, do not run it.

Use a separate disposable database for tests. Do not allow test commands to target the project database accidentally.

## 4. Architecture preservation

MediReach already has an established Django application.

Do not rewrite the project from scratch.

Do not introduce:
- A second provider directory architecture.
- Duplicate doctor or hospital models.
- Separate competing appointment systems.
- Duplicate emergency detection systems.
- Multiple independent provider search implementations.
- Parallel chatbot pipelines that bypass existing safety logic.

Extend existing services and models wherever appropriate.

Preserve existing relationships, permissions, templates and URLs unless the assigned task explicitly requires a reviewed change.

Do not replace a working implementation merely because another library or framework seems more convenient.

## 5. Medical and emergency safety

Healthcare-related behaviour must be conservative and transparent.

### Emergency priority

Emergency detection must happen before ordinary chatbot intent processing.

Emergency guidance must not depend on a local LLM.

Do not allow an LLM to override deterministic emergency rules.

Do not delay emergency guidance to collect unnecessary details.

Do not claim that MediReach has:
- Contacted emergency services.
- Dispatched an ambulance.
- Notified emergency contacts.
- Confirmed an emergency response.

Unless a real, authorised integration has been implemented and verified, such claims are prohibited.

### Medical information

The assistant must not:
- Diagnose conditions.
- Prescribe medication.
- Invent treatment instructions.
- Claim certainty without evidence.
- Replace qualified medical advice.

Use reviewed and trustworthy medical knowledge.

When uncertainty exists, state it clearly and direct users to qualified healthcare professionals.

## 6. Provider information integrity

Never fabricate:

- Doctor names.
- Qualifications.
- Registration numbers.
- Specialties.
- Hospitals.
- Addresses.
- Phone numbers.
- Consultation prices.
- Availability.
- Appointment confirmation.
- Provider responses.

Every provider record should communicate its provenance and verification status.

Distinguish:

1. Official registry source.
2. Credential verified.
3. Mapped location, not credential verified.
4. MediReach demo record.
5. Verification pending.
6. Verification failed or expired, where applicable.

A map result is not automatically a verified doctor or healthcare provider.

Fictional demo records must be visibly labelled.

## 7. Approved technology direction

Current constraints and decisions:

- Zero paid API budget.
- Existing Django architecture remains.
- SQLite is used for local development.
- Design should remain compatible with future PostgreSQL use.
- Leaflet and OpenStreetMap are the map foundation.
- OpenStreetMap/Overpass may be used for governed geographic discovery.
- Nominatim may be used only in accordance with its public usage policy.
- ABDM HFR is a future official facility-registry adapter, subject to access approval.
- Do not assume unrestricted public NMC/NMR API access.
- Ollama may provide optional local AI.
- A deterministic fallback must remain available.

Do not add commercial paid APIs without explicit approval.

## 8. Shared services and business logic

Before adding a service, inspect whether an equivalent already exists.

Shared behaviour should have one authoritative implementation.

Examples:

- Provider search should be shared across directories and chatbot.
- Emergency assessment should remain centralised.
- Appointment validation should not be duplicated in multiple views.
- Ownership and permission checks should be reusable.
- Provider provenance and verification rules should be consistent.

Do not put complex business logic directly into templates or frontend JavaScript.

Frontend code must not become the authority for medical or security decisions.

## 9. Privacy and permissions

Healthcare information is sensitive.

Always preserve:

- Patient ownership checks.
- Hospital-admin scoping.
- Authentication requirements.
- Permission checks.
- Input validation.
- Appropriate data minimisation.

Never expose another patient's:
- Chat history.
- Notes.
- Medical history.
- Emergency contacts.
- Appointments.
- Referrals.
- Personal information.

Do not log sensitive patient data unnecessarily.

Never put secrets in source code, tests, prompts, documentation or commits.

## 10. Appointment and care-coordination truthfulness

Keep these states separate:

- Appointment request created.
- Appointment request submitted.
- Provider received request.
- Provider accepted request.
- Appointment confirmed.
- Appointment completed.
- Appointment cancelled.

Do not claim a provider-confirmed booking when only a local database record exists.

Likewise, distinguish:
- Referral created.
- Referral sent.
- Referral received.
- Referral accepted.
- Referral completed.

And:
- Enquiry created.
- Enquiry delivered.
- Enquiry acknowledged.
- Enquiry resolved.

Never imply delivery or provider action without evidence.

## 11. Frontend and browser behaviour

Do not claim browser functionality is verified merely because a JavaScript file passes syntax checking.

For map changes, inspect:
- Browser console errors.
- Network failures.
- Tile requests.
- Map container dimensions.
- Leaflet initialization.
- API response format.
- Coordinate validation.
- Attribution display.
- Fallback behaviour.

Preserve a useful list or text fallback when a map cannot load.

Never remove OpenStreetMap attribution.

## 12. Testing requirements

For every implementation task:

- Add regression tests for the behaviour changed.
- Preserve existing tests.
- Run the appropriate focused tests using an isolated test database.
- Run the full suite where practical.
- Run Django system checks where safe.
- Check migration drift without allowing accidental database changes.
- Test permissions and ownership boundaries.
- Report browser testing separately.

Never report a test as passed unless it was actually run.

Never conceal failed tests.

## 13. Documentation requirements

Update relevant documentation whenever a task changes:

- Architecture.
- Models or relationships.
- API routes.
- Permissions.
- Provider discovery.
- Medical behaviour.
- Security.
- Setup.
- Dependencies.
- Feature status.

Update docs/MEDIREACH_PROJECT_MASTER_PLAN.md after every reviewed phase.

A feature is not COMPLETED merely because the coding agent says it is done.

Completion requires:
- Acceptance criteria met.
- Relevant tests passed.
- Database impact reviewed.
- Security and ownership checked.
- Outstanding limitations documented.
- Human review completed.

## 14. Required completion report

Every coding task must finish with:

1. Objective.
2. Implementation summary.
3. Files created.
4. Files modified.
5. Existing functionality affected.
6. APIs and services affected.
7. Models and migrations affected.
8. Database impact.
9. Tests run.
10. Test results.
11. Browser verification.
12. Security and privacy considerations.
13. Known limitations.
14. Incomplete work.
15. Recommended next task.

If the database was not touched, explicitly say so.

If browser verification was unavailable, explicitly say so.

## 15. Team workflow

Work on one assigned task at a time.

Do not change another member's assigned files without coordination.

Before changing shared files, explain the conflict risk.

Do not merge or overwrite another contributor's work without review.

Do not push directly to the main branch unless explicitly authorised by the team.

The master plan is the central source of truth for development status.
