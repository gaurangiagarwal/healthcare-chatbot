# MediReach — Master Project Plan

**Document type:** Living product, architecture, development and team coordination plan.

**Purpose:** This document is the single source of truth for MediReach's agreed direction, implementation phases, responsibilities, constraints, technical decisions, acceptance criteria and progress.

Every team member and every AI coding agent must read this document before starting work.

Last planning baseline: 23 November 2026.

---

# 1. Project overview

## 1.1 What is MediReach?

MediReach is a healthcare assistance and care-coordination platform built using Django.

It aims to help users navigate healthcare needs through a connected system that includes emergency-first guidance, structured health assistance, provider discovery, patient information management, appointment requests, referrals and enquiries.

The platform is intended to reduce fragmentation between patients and healthcare services.

## 1.2 Problem being addressed

A person looking for healthcare support may need to:

- Understand whether a situation requires urgent medical attention.
- Find an appropriate doctor or healthcare facility.
- Identify nearby healthcare services.
- Determine whether a provider's information is trustworthy.
- Request an appointment.
- Contact a facility.
- Share relevant information.
- Keep track of appointments, referrals and enquiries.
- Maintain emergency contacts and personal healthcare records.

These activities are often handled through disconnected applications and communication channels.

MediReach aims to provide a unified navigation and coordination experience.

## 1.3 Product goals

1. Make emergency guidance clear and accessible.
2. Provide safe healthcare navigation.
3. Improve access to healthcare-provider information.
4. Make provider provenance and verification transparent.
5. Help users coordinate appointments and enquiries.
6. Organise patient-owned healthcare information.
7. Provide an assistant that supports navigation without replacing clinicians.
8. Build an extensible architecture for future integrations.
9. Keep the platform usable under a zero-paid-API constraint.

## 1.4 Non-goals

MediReach is not intended to:

- Replace hospitals or emergency services.
- Diagnose diseases autonomously.
- Prescribe medication.
- Guarantee the quality of an unverified provider.
- Claim real appointment availability without provider confirmation.
- Automatically dispatch ambulances without a verified authorised integration.
- Replace professional medical judgement.

---

# 2. Product scope

## 2.1 Patient-facing experience

The planned patient experience includes:

- Registration and authentication.
- Patient profile.
- Healthcare information.
- Emergency contacts.
- Chat assistant.
- Emergency assistance.
- Doctor and hospital discovery.
- Diagnostic-centre discovery.
- Location-aware maps.
- Appointment requests and tracking.
- Referrals and enquiries.
- Patient notes and history.
- Dashboard and activity overview.

## 2.2 Healthcare-provider experience

The planned provider experience includes:

- Provider profile management.
- Facility information management.
- Service information.
- Availability information where supported.
- Enquiry handling.
- Referral handling.
- Appointment request handling.
- Verification and provenance.
- Hospital-admin permissions and scoped management.

Do not assume all these capabilities currently exist.

## 2.3 Administrative experience

The longer-term administrative experience may include:

- Provider verification.
- Provider record moderation.
- Demo-data management.
- Facility-service management.
- Audit logs.
- Source and verification status management.
- Data-quality monitoring.

These capabilities require separate implementation and approval.

---

# 3. Approved technical direction

The following decisions are the current project baseline.

| Area | Decision |
|---|---|
| Backend | Existing Django application |
| Frontend | Existing Django templates and JavaScript |
| Local database | SQLite |
| Future database compatibility | PostgreSQL-compatible design |
| Map | Leaflet |
| Map tiles | OpenStreetMap |
| Geographic provider discovery | OpenStreetMap / Overpass, governed by usage policies |
| Geocoding | Nominatim only under its public usage policy |
| Official facility source | Future ABDM HFR adapter, subject to access approval |
| Professional verification | Authorised/public lookup or documented manual evidence; no unauthorised scraping |
| AI runtime | Optional local Ollama |
| AI safety | Deterministic emergency handling and fallback |
| Paid APIs | Not approved under current budget |
| Architecture strategy | Extend existing services; avoid duplicate systems |

## 3.1 Zero-budget constraint

The current project budget for paid APIs is zero.

Do not introduce paid services that require billing, paid API keys or usage charges without explicit team approval.

The project should prioritise:
- Existing Django functionality.
- Open data where legally and technically appropriate.
- Local AI where feasible.
- Caching and controlled external requests.
- Manual provider verification workflows where official access is unavailable.

## 3.2 Provider discovery strategy

The approved strategy is hybrid.

It consists of:

1. MediReach-managed provider records.
2. Open geographic discovery through suitable OpenStreetMap data.
3. Official provider/facility registry integrations when authorised access becomes available.
4. Transparent source and verification labels.

OpenStreetMap provides geographic data, not a guarantee of medical credentials or operational availability.

A mapped location must not automatically receive a verified-provider label.

## 3.3 Official registry integration

ABDM Health Facility Registry (HFR) is a planned future integration.

The project must not claim that HFR is already integrated.

Access, documentation, approval, authentication, permitted use and API availability must be verified before implementation.

Keep the provider-source architecture modular so an official registry can be added without replacing the entire directory.

Professional registration verification must similarly use authorised access or documented evidence. Do not scrape restricted systems or assume an unrestricted API exists.

## 3.4 AI architecture

The approved chatbot direction is hybrid:

- Deterministic emergency assessment.
- Structured symptom conversation.
- Reviewed medical information.
- Retrieval grounded in trusted sources.
- Optional local Ollama model.
- Deterministic fallback when AI is unavailable.

The LLM must never control:
- Emergency priority.
- Diagnosis.
- Prescriptions.
- Provider verification.
- Appointment confirmation.
- Emergency dispatch.
- Claims about actions that did not happen.

---

# 4. Existing technical baseline

## 4.1 Framework and structure

The existing application is Django-based.

The project includes:
- A Django project configuration.
- A `portal` application.
- Django models and migrations.
- Views and URL routes.
- Forms.
- Shared service modules.
- Templates.
- Static JavaScript.
- Django tests.

Exact module responsibilities must be documented in ARCHITECTURE.md and verified against the current source.

## 4.2 Existing feature areas

The audit and reported P1 work establish these application areas:

- Registration and authentication.
- Patient profiles.
- Chat conversations and messages.
- Rule-based chatbot.
- Emergency assessment.
- Doctors.
- Hospitals.
- Hospital services.
- Hospital map.
- Appointment slots and bookings.
- Referrals.
- Hospital enquiries.
- Emergency contacts.
- Patient notes.
- Patient history.
- Dashboard.
- Hospital-admin workflows.

## 4.3 Existing implementation limitations

The current implementation must not be mistaken for a complete production healthcare platform.

Known limitations include:

- Provider discovery is primarily based on existing local records.
- Demo providers are fictional and unverified.
- Live external provider discovery is not yet complete.
- Diagnostic-centre discovery is not implemented as a complete workflow.
- Browser map rendering and external tile loading are unverified.
- Local appointment records are not equivalent to provider-confirmed bookings.
- Referrals and enquiries are not necessarily delivered externally.
- Anonymous enquiries cannot be tracked by the submitter.
- Emergency contacts are stored but not automatically notified.
- Chatbot medical knowledge is not yet a complete reviewed knowledge system.
- Production-level privacy, security and retention controls require further work.

---

# 5. Critical database incident and recovery policy

## 5.1 Incident record

During preparation for a local map check, a temporary database-path expression failed.

Subsequently, `migrate` and `seed_demo` ran against the existing project `db.sqlite3`.

The reported outcome was:

- Migration reported no pending changes.
- `seed_demo` reported four fictional doctors created.
- `seed_demo` reported 168 new slots created.

The database was not inspected or restored afterward.

## 5.2 Current database status

**Status: MODIFIED — RECOVERY/VALIDATION PENDING**

Do not assume:
- The database is unchanged.
- The reported demo entries are the only changes.
- A known-good backup exists.
- The database has been restored.
- The database is safe for further migrations.

## 5.3 Required precautions

Until an approved recovery process is completed:

1. Do not run migrations against the project database.
2. Do not run seed commands.
3. Do not flush or reset it.
4. Do not delete or replace it.
5. Do not run tests against it.
6. Preserve `db.sqlite3` and associated WAL/SHM files together.
7. Identify a known-good backup.
8. Compare the backup and current database only through an approved recovery procedure.
9. Obtain explicit approval before restoration or cleanup.

No database operations are authorised by this documentation phase.

## 5.4 Future migration policy

Before every future schema change:

- Identify the target database.
- Confirm a known-good backup.
- Review migration operations.
- Review data migration behaviour.
- Check backward compatibility.
- Explain rollback limitations.
- Obtain approval.
- Test against an isolated disposable database first.

Never use destructive schema changes merely to make a test pass.

---

# 6. Development phases

The project will be developed in controlled phases.

Each phase must have:
- An objective.
- Defined scope.
- Dependencies.
- Acceptance criteria.
- Tests.
- Documentation updates.
- A review decision.

A phase must not be marked complete solely because an AI coding agent reports success.

## P0 — Emergency safety

**Status: Completed provisionally**

### Objective

Ensure emergency requests are identified before ordinary chatbot handling.

### Reported work

- Added deterministic emergency-assistance request detection.
- Added negation handling.
- Added regression tests.
- Preserved existing emergency call action and chatbot priority behaviour.

### Verification reported

- 98 tests passed.
- Django check passed.
- Migration drift check reported no changes.

### Remaining verification

- Browser-level execution of emergency interaction.
- Review emergency language coverage.
- Verify no false positives for negated or historical mentions.
- Confirm that emergency messaging does not imply automatic dispatch.

### Acceptance criteria

- Emergency requests are detected before normal chatbot intents.
- Emergency responses are not dependent on an LLM.
- Negated and historical mentions do not incorrectly trigger emergency handling.
- Emergency actions are transparent.
- No unsupported notification or dispatch claims are made.

## P1 — Core application workflow repair

**Status: Implementation reported complete; browser verification pending**

### Objective

Repair and clarify existing application functionality without introducing a new architecture.

### Reported work

- Doctor directory filtering and detail links.
- Hospital directory filtering and detail links.
- Demo labels and empty states.
- Coordinate validation.
- Map failure fallback.
- Appointment action messaging.
- Referral and enquiry messaging.
- Patient-owned contact and history access.
- Dashboard and navigation improvements.

### Verification reported

- 118 tests passed.
- Django check passed.
- Migration drift check reported no changes.
- Modified JavaScript passed `node --check`.
- Selected local HTTP checks returned HTTP 200 using an isolated temporary database.

### Remaining work

- Actual browser rendering verification.
- External tile-loading verification.
- Confirm all main user journeys manually or through browser automation.
- Verify responsive behaviour and error states.

### Acceptance criteria

- Existing directory workflows work.
- Filters and detail links behave correctly.
- Demo records are clearly labelled.
- Invalid coordinates are not used to render map markers.
- Map failures have a useful fallback.
- Appointment, referral and enquiry messaging is truthful.
- Patient-owned information remains properly scoped.

## P1.5 — Documentation and team readiness

**Status: In progress**

### Objective

Create complete documentation and a repeatable team workflow.

### Required outputs

- README.md.
- AGENTS.md.
- ARCHITECTURE.md.
- DATABASE_SCHEMA.md.
- API_REFERENCE.md.
- FEATURES.md.
- DEVELOPER_SETUP.md.
- TESTING.md.
- CONTRIBUTING.md.
- INTEGRATION_GUIDE.md.
- AI_CODING_GUIDE.md.
- SECURITY_AND_SAFETY.md.
- ROADMAP.md.
- MEDIREACH_PROJECT_MASTER_PLAN.md.
- TEAM_ONBOARDING.md.
- CODEX_TASK_TEMPLATE.md.
- FEATURE_OWNERSHIP.md.
- PHASE_COMPLETION_TEMPLATE.md.

### Acceptance criteria

- All documents are present.
- Documentation is internally consistent.
- Implemented and planned features are distinguished.
- The database incident is documented.
- Team members can understand their work boundaries.
- Codex instructions prevent database misuse and architectural duplication.
- The master plan provides clear future tasks and dependencies.
- Documentation is reviewed and approved by the project owner.

### Gate

P2 must not begin until P1.5 is reviewed and accepted.

## P2 — Backward-compatible provider data foundation

**Status: Review — provider model and migration source is present; database validation remains incomplete**

### Objective

Create a reliable provider data foundation that supports multiple data sources and verification states without breaking existing application functionality.

### Scope

- Review existing doctor, hospital and hospital-service models.
- Preserve existing primary keys and foreign-key relationships.
- Identify common provider fields.
- Define provider-source metadata.
- Define verification states.
- Define source timestamps and freshness.
- Define provider identifiers.
- Design support for clinics and diagnostic centres.
- Establish a shared provider search interface.
- Establish validation and deduplication rules.

### Design principles

Do not blindly replace existing models with a universal provider model.

Before implementation, compare:
- Existing doctor fields.
- Existing hospital fields.
- Existing service relationships.
- Existing appointment relationships.
- Existing admin relationships.
- Existing tests and templates.

Prefer a backward-compatible extension or adapter approach where possible.

### Proposed provider provenance fields

The final schema requires review, but the conceptual data requirements include:

- Source type.
- Source identifier.
- Source URL or evidence reference where permitted.
- Verification status.
- Verification method.
- Verified timestamp.
- Last updated timestamp.
- Expiry or review timestamp where appropriate.
- Record status.
- Duplicate or merge reference where required.

These are design requirements, not claims that the fields already exist.

### Acceptance criteria

- Existing workflows remain compatible.
- Existing doctor and hospital relationships are preserved.
- Provider provenance can be represented.
- Verification status is explicit.
- Demo data remains visibly separate from verified records.
- Shared provider search is available.
- Tests cover ownership, filtering, duplicate handling and provenance.
- Migration is reviewed and approved before application to any persistent database.

## P3 — Open provider discovery

**Status: Not started**

### Objective

Expand provider discovery beyond the current local directory while maintaining data quality and source transparency.

### Scope

- OpenStreetMap/Overpass discovery.
- Controlled geospatial queries.
- Caching.
- Rate limiting.
- Request timeouts.
- Source attribution.
- Duplicate handling.
- Coordinate validation.
- Provider category mapping.
- Nominatim geocoding under policy.
- Future official registry adapters.

### Important constraints

- OpenStreetMap map tiles are not a verified healthcare-provider database.
- Overpass public instances have usage and capacity limitations.
- Do not repeatedly query public endpoints for the same data.
- Cache suitable results.
- Use sensible timeouts.
- Respect attribution and licensing.
- Do not implement uncontrolled background scraping.
- Do not treat mapped facilities as medically credential-verified.

### Nominatim

Use only for explicit user-triggered geocoding in accordance with the public usage policy.

Do not use the public endpoint for autocomplete or bulk geocoding.

### ABDM HFR

Build a future adapter boundary.

Do not implement access-dependent functionality until approval and API details are available.

### Acceptance criteria

- Search works without paid APIs.
- Results identify their source.
- Unverified records are clearly labelled.
- Duplicate records are handled safely.
- Queries respect external usage policies.
- Failures do not break the local directory.
- Results are cached appropriately.

## P4 — Hybrid AI healthcare assistant

**Status: Not started**

### Objective

Develop a more capable assistant without sacrificing deterministic medical safety.

### Architecture

1. Emergency assessment.
2. Structured symptom conversation.
3. Medical safety rules.
4. Reviewed medical knowledge.
5. Retrieval grounded in trusted sources.
6. Optional local Ollama model.
7. Deterministic fallback.

### Scope

- Structured symptom intake.
- Follow-up questions.
- Basic first-aid guidance.
- Appropriate care-navigation suggestions.
- Healthcare facility discovery through the shared provider service.
- Context-aware responses based only on authorised patient information.
- Local model integration.
- Output validation.
- Uncertainty handling.
- Logging and evaluation.

### Safety requirements

- The LLM must not diagnose.
- The LLM must not prescribe.
- The LLM must not override emergency logic.
- The LLM must not invent provider information.
- The LLM must not fabricate citations.
- The LLM must not claim that external actions succeeded without evidence.
- Local AI failure must not make core application features unavailable.

### Acceptance criteria

- Emergency handling remains deterministic.
- Structured symptom flows are testable.
- Knowledge sources are traceable.
- Local model failures have safe fallback.
- Output is constrained and validated.
- Tests cover harmful or unsupported output patterns.

## P5 — Care coordination

**Status: Not started**

### Objective

Improve the connection between patients and healthcare providers through transparent request and response workflows.

### Scope

- Appointment request lifecycle.
- Provider response lifecycle.
- Referral lifecycle.
- Enquiry lifecycle.
- Provider-side handling.
- Status tracking.
- Patient notifications where a real notification mechanism is implemented.
- Audit trail.
- Clear delivery and acceptance states.

### Key distinction

A locally saved request is not a provider-confirmed action.

A provider response must be represented explicitly and supported by actual workflow evidence.

### Acceptance criteria

- Patients can see their own requests.
- Providers can access only requests they are authorised to handle.
- Status changes are traceable.
- Confirmation is based on an actual provider action.
- Failed delivery is visible.
- No misleading success messages are shown.

## P6 — Integration and release QA

**Status: Review — source audit and preparation completed; release validation remains incomplete**

### Objective

Verify the complete product and prepare a secure, reliable release.

### Scope

- End-to-end browser testing.
- Responsive design verification.
- Map and external tile verification.
- Provider search verification.
- Chatbot evaluation.
- Emergency workflow evaluation.
- Appointment lifecycle testing.
- Referral and enquiry lifecycle testing.
- Permission and ownership testing.
- Security review.
- Privacy review.
- Migration review.
- Deployment configuration.
- Performance and reliability checks.
- Accessibility review.
- Documentation review.

### Acceptance criteria

- Critical journeys pass.
- Security and ownership boundaries are tested.
- Emergency behaviour is safe.
- No misleading provider or booking claims remain.
- External integration policies are respected.
- Deployment secrets are configured securely.
- Database migration and backup strategy are approved.
- Known limitations are documented.

---

# 7. Feature status tracker

Statuses describe the reported implementation baseline and must be updated only after review.

| Feature | Current status | Next work |
|---|---|---|
| Authentication | Implemented | Security review |
| Patient profile | Implemented | Privacy and validation review |
| Chat persistence | Implemented | Integration improvements |
| Rule-based chatbot | Partially implemented | Structured assistant |
| Emergency detection | Implemented provisionally | Browser and safety verification |
| First-aid guidance | Partially implemented | Reviewed knowledge expansion |
| Doctor directory | Implemented locally | Provider data foundation |
| Hospital directory | Implemented locally | Provider data foundation |
| Hospital map | Needs browser verification | Diagnose rendering and tile loading |
| Nearby mapped provider discovery | Partially implemented through user-triggered OSM/Overpass search; not credential verification | Browser/network validation |
| Provider verification | Schema and labels present; authorized decision workflow unavailable | Configure reviewer permissions and verify evidence process |
| Diagnostic-centre discovery | Partial generic facility/OSM tag support; no dedicated complete workflow | Define reviewed service catalogue and data source |
| Local appointment workflows | Implemented | Provider confirmation lifecycle |
| Provider-confirmed appointments | Not implemented | P5 |
| Referrals | Implemented locally | Delivery and response lifecycle |
| Hospital enquiries | Implemented locally | Tracking and delivery |
| Emergency contacts | Implemented | Notification workflow |
| Patient notes | Implemented | Privacy and usability review |
| Patient history | Implemented | Privacy and completeness review |
| Dashboard | Implemented | Integration and usability |
| Local AI assistant | Optional Ollama and deterministic fallback implemented; clinical/runtime validation pending | Isolated runtime and safety evaluation |
| External official registry | Not implemented | Access and approval |
| Production release readiness | Not established | P6 |

---

# 8. Shared architecture requirements

## 8.1 Provider search

Provider search must have a shared implementation.

The chatbot, doctor directory, hospital directory and future discovery features must not each implement their own unrelated provider search logic.

## 8.2 Emergency assessment

Emergency assessment must remain centralised and deterministic.

Do not create an independent emergency detector inside the LLM prompt or frontend.

## 8.3 Patient information

Patient information access must be scoped by authenticated identity and role.

Never trust a patient ID supplied by the browser without verifying ownership.

## 8.4 Appointment workflow

Appointment state must distinguish local requests from provider-confirmed bookings.

## 8.5 Provider provenance

Every provider result must communicate its source and verification status.

## 8.6 AI integration

AI must consume shared application services rather than independently inventing or retrieving provider information.

---

# 9. API and integration roadmap

The current application uses internal Django routes and browser interactions.

Exact API contracts are maintained in docs/API_REFERENCE.md.

Future integrations must use dedicated adapters rather than placing external API calls directly inside templates or unrelated views.

Planned adapter boundaries:

- Geographic discovery adapter.
- Geocoding adapter.
- Official facility registry adapter.
- Professional verification adapter.
- Local AI adapter.
- Notification adapter.

Every adapter should define:
- Input and output contract.
- Error handling.
- Timeouts.
- Retry rules.
- Rate limits.
- Caching.
- Provenance.
- Privacy implications.
- Tests.
- Fallback behaviour.

No integration may claim success without an actual successful response.

---

# 10. Database and migration roadmap

## 10.1 Existing entities

The current application includes doctor, hospital, hospital-service, appointment-related, patient, chat, referral, enquiry and emergency-contact concepts.

Exact model definitions and relationships must be documented in DATABASE_SCHEMA.md.

## 10.2 Backward compatibility

Preserve existing relationships and workflows.

Do not remove or rename fields without analysing:
- Existing model usage.
- Foreign keys.
- Views.
- Forms.
- Templates.
- Admin configuration.
- Tests.
- Existing stored data.

## 10.3 Migration approval

Every migration must have:
- A documented reason.
- A reviewed schema diff.
- A data-impact explanation.
- A backup plan.
- A test on an isolated database.
- A rollback assessment.
- Explicit approval before persistent database execution.

## 10.4 Recovery incident

The project SQLite database has a reported modification incident.

Current status: modified, not inspected, not restored.

This remains an open operational issue.

---

# 11. Testing and quality gates

Every feature must include appropriate tests.

Minimum quality gates:

1. Focused regression tests.
2. Ownership and permission tests.
3. Validation tests.
4. Error-path tests.
5. Full application test suite where practical.
6. Django system checks where safe.
7. Migration review.
8. Browser testing for frontend behaviour.
9. Documentation updates.
10. Human review.

Do not confuse:
- JavaScript syntax checking with browser execution.
- HTTP 200 with correct application behaviour.
- A local database record with an external action.
- A mapped location with a verified provider.
- A passing test with production readiness.

---

# 12. Security and privacy requirements

Patient data must be treated as sensitive.

Mandatory principles:

- Least privilege.
- Owner-scoped queries.
- Hospital-admin scoping.
- Secure authentication.
- Input validation.
- Secret management.
- Minimal logging of personal data.
- Transparent data handling.
- Appropriate error messages.
- No patient data in public URLs or logs without justification.

Production readiness requires a separate security review.

---

# 13. Team ownership matrix

Final assignments are intentionally TBD.

| Workstream | Responsibilities | Owner |
|---|---|---|
| Provider data and discovery | Doctors, hospitals, diagnostic centres, data sources, verification, maps | TBD |
| Chatbot and emergency | Emergency safety, symptom navigation, first aid, local AI | TBD |
| Care coordination | Appointments, referrals, enquiries, provider responses | TBD |
| Platform integration | Shared services, APIs, frontend/backend coordination | TBD |
| Quality and security | Testing, privacy, permissions, release review | TBD |
| Documentation and coordination | Master plan, architecture, task tracking, onboarding | TBD |

One person may own multiple workstreams, but ownership must be agreed by the team.

## 13.1 Shared-file coordination

Shared files include:
- models.py.
- migrations.
- views.py.
- urls.py.
- Shared service modules.
- Base templates.
- Shared frontend JavaScript.
- Settings and dependencies.
- Master documentation.

Before changing shared files, contributors must communicate the planned change and coordinate ownership.

Do not allow multiple coding agents to independently rewrite the same shared file.

---

# 14. AI coding workflow

Every contributor using Codex must provide:

1. AGENTS.md.
2. This master plan.
3. Relevant architecture documentation.
4. Relevant API and database documentation.
5. Their assigned workstream.
6. The exact task scope.
7. Allowed files.
8. Forbidden files.
9. Acceptance criteria.
10. Testing requirements.

Each coding task must be small enough to review.

After completion, the contributor must report:
- What changed.
- Which files changed.
- What APIs or services were affected.
- Whether models or migrations changed.
- Whether the database was touched.
- Which tests ran.
- Which tests failed.
- Whether browser verification was performed.
- What remains incomplete.

A Codex response is not itself approval to merge or start the next phase.

---

# 15. Progress tracker

| Phase | Status | Evidence / notes |
|---|---|---|
| P0 Emergency safety | Review | Emergency implementation and regression tests are present; no P6 test or runtime execution was performed |
| P1 Core workflow repairs | Review | Core workflows are present; database and browser validation remain outstanding |
| P1.5 Documentation | Review | Documentation set exists; some linked documents referenced by README/AGENTS are absent |
| P2 Provider data foundation | Review | Provider models and migration 0004 are present; database compatibility is unverified |
| P3 Open provider discovery | Review | OSM and shared discovery source is present; live network and browser behavior are unverified |
| P4 Hybrid AI assistant | Review | Structured chat and optional Ollama source is present; runtime behavior is unverified |
| P5 Care coordination | Review | Local appointment/referral/enquiry workflows are present; provider delivery/confirmation is not implemented |
| P6 Integration and release QA | Review | Source audit and demo preparation completed; tests, Django checks, migration execution and browser validation were not run |

Statuses may only be updated after review.

Allowed statuses:
- Not started.
- In progress.
- Review.
- Completed.
- Blocked.

---

# 16. Known issues and unresolved questions

1. Existing project database requires an approved recovery assessment.
2. Browser map rendering has not been verified.
3. External OpenStreetMap tile loading has not been verified.
4. OSM nearby discovery is implemented in source, but provider verification and live directory completeness are absent and browser/network behavior is unverified.
5. Official facility-registry access remains subject to approval.
6. Professional verification source and process require finalisation.
7. Diagnostic-centre discovery needs implementation.
8. Provider-side appointment confirmation requires a defined workflow.
9. Referral and enquiry delivery tracking require a real communication mechanism.
10. Emergency-contact notification is not implemented.
11. Optional local Ollama support exists; clinical evaluation and broader reviewed medical knowledge remain incomplete.
12. Production security and privacy review remains necessary.
13. Team member ownership assignments are TBD.
14. Git repository and branch conventions must be confirmed by the team.

---

# 17. Next permitted task: approved final validation gate

Do not begin additional feature phases as part of P6. Database-dependent validation requires a separate approved recovery/isolation plan and must not target the unverified project database.

- Establish an explicitly isolated validation database and confirm the effective connection target before running Django commands.
- Review migration 0004 on an isolated database with the approved Django/backend versions.
- Run the full test suite and Django checks only after confirming isolation.
- Perform browser checks for emergency, chat, provider search, maps, request workflows, ownership, and mobile navigation.
- Complete deployment security, privacy, retention, and backup review.
- Obtain human release approval.

No database operation against the project database is authorized by this checklist or P6 source work.

---

# 18. Phase completion record

For every phase, append a completion record using docs/PHASE_COMPLETION_TEMPLATE.md.

Each record must include:
- Phase.
- Date.
- Objective.
- Implementation summary.
- Files changed.
- APIs and services affected.
- Model and migration impact.
- Database impact.
- Tests.
- Browser verification.
- Known limitations.
- Review decision.
- Next permitted phase.

Do not delete earlier records.

## 18.1 P6 source audit record — 23 November 2026

- **Phase:** P6 — Final source audit, validation planning and demo preparation.
- **Objective:** Review the existing implementation without accessing the unverified database; correct only clear source defects; prepare demo and validation documentation.
- **Implementation summary:** Repaired Python syntax in migration 0004; restricted serialized doctor contact routes to same-site paths or credential-free HTTP(S); restricted Ollama to loopback endpoints; validated chat coordinates and discovery API request types; returned controlled client errors for malformed facility status payloads; rejected the default development secret when DEBUG is disabled; corrected legacy product naming; added focused regression test source. Created demo script, known-limitations and final-validation checklist documents.
- **Files:** `config/settings.py`; `portal/migrations/0004_provider_data_foundation.py`; `portal/services/resources.py`; `portal/views.py`; `portal/test_p6_stabilization.py`; `docs/DEMO_SCRIPT.md`; `docs/KNOWN_LIMITATIONS.md`; `docs/FINAL_VALIDATION_CHECKLIST.md`; this master plan.
- **Database impact:** None. The existing SQLite database and WAL/SHM files were not accessed. Migration 0004 was inspected and statically parsed only; it was not imported or executed.
- **Tests and checks:** Added regression tests but did not run tests or Django commands. JavaScript syntax and Python source parsing were performed; they are not runtime validation.
- **Browser verification:** Not performed; no application server was started.
- **Review decision:** Remains in Review. Do not claim release readiness or database compatibility.
- **Next permitted work:** Obtain approval for a separate database recovery/isolation plan, then execute the checklist in `docs/FINAL_VALIDATION_CHECKLIST.md` only against an explicitly approved isolated environment.

---

# 19. Final project principle

MediReach must be built as one coherent platform, not as a collection of disconnected features.

Every new feature must fit the agreed architecture, protect patient data, preserve existing workflows, use trustworthy information, communicate limitations honestly and be testable.

The goal is not merely to make features appear in the interface.

The goal is to build a reliable, safe, maintainable healthcare assistance and care-coordination platform.
