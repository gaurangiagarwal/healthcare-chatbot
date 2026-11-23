# MediReach Known Limitations

This document describes limitations visible from source review. No Django checks, tests, migrations, database inspection, application startup, or browser session were run for the P6 review. Passing source/syntax checks is not runtime validation.

## Data and provider discovery

- MediReach-managed doctor and facility records come from the configured database. Its current `db.sqlite3` has a reported accidental modification and remains uninspected and unverified. Its schema, records, migration state, and compatibility must not be assumed.
- Demo records are fictional. A managed record, source record, or legacy status is not proof of real-world existence or credentials.
- OpenStreetMap/Overpass discovery is user-triggered, transient, dependent on network access and public service availability, and does not verify credentials, current operation, opening hours, capacity, or acceptance of patients. Overpass outages/rate limits can leave only managed results.
- Leaflet, map tile loading, layout, browser geolocation permissions, and external network behavior have not been verified in a browser as part of P6. The list is the fallback.
- Diagnostic-centre, pharmacy, and other facility coverage depends on the tags and local data present; it is not a complete provider directory.
- Verification decisions are intentionally unavailable until a dedicated authorized reviewer permission is configured. Verification labels depend on source records and verification records currently present.
- A provider contact route is now exposed only for a same-site path or credential-free HTTP(S) URL. Contact details remain dependent on the stored data and its verification labels; users should independently confirm them.

## Assistant and health guidance

- Emergency screening is deterministic and rule-based; pattern matching cannot identify every emergency or replace emergency services. Call 112 for an emergency in India and do not wait for a chatbot response.
- The symptom flow supports a limited set of symptoms and structured questions. It is not a diagnostic or triage service.
- First-aid guidance is a finite reviewed content set, not comprehensive medical advice.
- Ollama is optional and restricted to a loopback URL. It may be absent, unconfigured, unavailable, slow, or return output rejected by safety filters. The deterministic fallback remains available. Output filtering cannot guarantee clinical correctness.
- No AI output may make emergency, provider-verification, appointment-confirmation, or external-delivery decisions.

## Requests and care coordination

- Appointment slots and bookings are local records. A saved booking is not a provider-confirmed appointment. No provider communication integration is present.
- Referral and enquiry workflows save local requests and statuses. They do not deliver requests to a facility or prove receipt, acceptance, or resolution. Anonymous enquiries cannot be tracked in a patient account.
- Hospital service status is a stored report that expires to unknown; it is not live capacity or an admission guarantee.
- Appointment race protection includes a database uniqueness constraint. Locking behavior varies by database backend; concurrent behavior still needs validation on the approved target database.

## Security, privacy and deployment

- Patient records are owner-scoped in the inspected views, and facility administration is scoped to the administrator's assigned hospital. This source review is not a penetration test or a complete authorization assessment.
- The application stores sensitive health-related profile data, conversations, contacts, notes, handover summaries, and care requests. Retention, deletion, consent, access logging, incident response, and production data governance need a separate review.
- Production must provide a unique `SECRET_KEY`, correct `ALLOWED_HOSTS`, HTTPS configuration, and reviewed deployment settings. P6 adds a fail-fast check against the bundled development key when `DEBUG` is disabled; production configuration itself was not executed or verified.
- The existing CI workflow runs migrations and tests. It must not be used against the unverified project database; confirm CI uses its isolated ephemeral database before relying on it.
- No backup, recovery, restoration, or database validation was performed.

## P6 source fixes and verification boundary

- Fixed the unmatched parenthesis in `portal/migrations/0004_provider_data_foundation.py`. It had prevented Python from parsing the migration. The migration was not imported by Django, executed, or checked against a database.
- Restricted serialized doctor contact routes to same-site paths or credential-free HTTP(S) links; unsafe schemes are omitted.
- Restricted optional Ollama configuration to loopback hosts to avoid sending health prompts to a remote endpoint; added chat coordinate validation, strict provider-discovery filter shape validation, and controlled client errors for malformed referral/enquiry status JSON shapes.
- Added a production guard against the default development signing key.
- Added regression test source in `portal/test_p6_stabilization.py`; no tests were run.
- JavaScript syntax checks, Python AST parsing, and template/source inspection do not establish that the workflows work in a running application or browser.
