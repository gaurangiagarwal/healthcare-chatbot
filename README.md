# MediReach

**A healthcare assistance and care-coordination platform**

MediReach is a Django-based healthcare assistance platform intended to help people navigate healthcare services, access basic health guidance, find healthcare facilities, and coordinate care through a single application.

The project combines patient-facing features with a longer-term plan for trustworthy provider discovery, emergency-first assistance, and care coordination.

> **Project status:** Under active development. Some features are implemented, some are partial, and several capabilities in the product vision are still planned. This README distinguishes the current implementation from future goals.

## 1. Product vision

Finding the right healthcare service can involve several disconnected steps: understanding where to seek help, locating a suitable doctor or facility, contacting providers, arranging appointments, and keeping track of personal healthcare information.

MediReach aims to bring these activities together in one platform.

The long-term product vision includes:

- Emergency-first assistance and clear escalation guidance.
- Structured symptom navigation and basic first-aid information.
- Discovery of doctors, hospitals, clinics, diagnostic centres and other healthcare resources.
- Location-aware healthcare facility discovery and maps.
- Patient profiles, emergency contacts, notes and healthcare history.
- Appointment requests and appointment-status tracking.
- Referrals and enquiries between patients and healthcare facilities.
- A hybrid healthcare assistant using deterministic safety rules, reviewed medical knowledge and optional local AI.
- Trust indicators that communicate where provider information came from and whether it has been verified.

MediReach is intended to support healthcare navigation and coordination. It is not a replacement for qualified medical professionals or emergency services.

## 2. Medical and service limitations

MediReach must not be presented as a medical diagnostic or treatment system.

- The chatbot must not claim to diagnose a disease.
- It must not prescribe medicines or replace professional medical advice.
- Emergency guidance must take priority over ordinary chatbot responses.
- A telephone link to an emergency number does not mean an emergency call was placed.
- Saving an appointment request does not mean a provider confirmed an appointment.
- Saving a referral or enquiry does not prove that it was delivered, accepted or acted upon.
- A mapped healthcare location is not automatically a verified provider.
- Demo records must never be presented as real, verified healthcare professionals or facilities.

In India, the emergency number 112 is used by the application for its emergency call action. The application must not claim that it automatically dispatches emergency services.

## 3. Technology stack

The existing project uses:

| Area | Technology |
|---|---|
| Backend | Python, Django |
| Local development database | SQLite |
| Frontend | Django templates, HTML, CSS and JavaScript |
| Interactive map | Leaflet |
| Map tiles | OpenStreetMap |
| Testing | Django test framework |
| Optional future local AI | Ollama |
| Nearby mapped facility discovery | OpenStreetMap / Overpass (transient, coordinate-based) |
| Text location resolution | OpenStreetMap Nominatim, user-triggered, cached |
| Planned official facility registry adapter | ABDM HFR, subject to access approval |

Exact versions must be taken from requirements.txt and project configuration.

The project currently follows a zero-paid-API budget constraint. Do not introduce paid APIs without explicit team approval.

## 4. Current implementation

The following status reflects the previous project audit and reported P0/P1 work. It is not a claim that every workflow has been independently browser-tested.

Existing application areas include:

- User registration and authentication.
- Patient profiles and patient-specific information.
- Chat conversations and persisted chat messages.
- Rule-based chatbot intent handling.
- Deterministic emergency-assistance detection and emergency call action.
- Doctor directory and doctor detail pages.
- Hospital directory and hospital detail pages.
- Hospital map using Leaflet and OpenStreetMap tile configuration.
- Local appointment and slot workflows.
- Referral and hospital enquiry workflows.
- Patient emergency contacts.
- Patient notes and healthcare history.
- Patient dashboard and navigation.
- Hospital-admin functionality with hospital-scoped access.

Important current limitations:

- Provider search is not a complete live or officially verified healthcare directory. Text location lookup is best-effort and public-service based.
- Demo doctors and facilities are fictional and unverified.
- Map rendering and external tile loading still require browser verification in the isolated validation instance.
- A successful local appointment operation does not confirm an appointment with a real provider.
- Referral and enquiry records do not prove that an external provider received or accepted them.
- Anonymous enquiries cannot be tracked by the submitter.
- Diagnostic-centre discovery is not yet implemented as a complete feature.
- Nominatim lookup is subject to its public usage policy, limited to one request per second per application, and must not be used for autocomplete or bulk geocoding. The current limiter coordinates workers on one host; multi-host deployments need shared rate limiting or a different provider. Set `MEDIREACH_GEOCODER_URL` only to a compatible HTTPS Nominatim endpoint; the default is the public Nominatim search service.
- Leaflet 1.9.4 does not set a tile image referrer policy by default. The OSM tile layer explicitly uses `strict-origin-when-cross-origin` so the browser sends the page origin as the tile Referer; verify the actual request and response in the target browser because browser privacy tools or deployment proxies can still remove it.
- Location failures distinguish invalid or unrecognized place input, rate limiting, timeout, malformed responses and service/network errors. The visible “map service busy” response originates from the Overpass facility search, not Nominatim.
- Nominatim lookup uses a 10-second request timeout and caches successful lookups for 24 hours and empty results for 10 minutes. A returned 429 triggers a temporary per-process cooldown and same-query negative cache; no automatic retry is performed.
- Emergency contacts are stored, but automatic emergency-contact notification is not implemented.
- The existing chatbot is not a fully integrated, medically reviewed AI assistant.
- Production-level privacy, security, retention and deployment readiness have not been established.

See docs/FEATURES.md for the detailed feature matrix.

## 5. Project structure

The application follows a Django project structure.

Conceptual structure:

MediReach/
    manage.py
    requirements.txt
    README.md
    AGENTS.md
    <django_project_package>/
        settings.py
        urls.py
    portal/
        models.py
        views.py
        forms.py
        urls.py
        services/
        migrations/
    templates/
        portal/
    static/
        portal/
    docs/
    db.sqlite3

This is an illustrative structure, not a replacement for the actual repository tree.

## 6. Windows development setup

Prerequisites:

- Windows 10 or later.
- A Python version compatible with the installed dependencies.
- Visual Studio Code or another Python-compatible editor.
- Git, if working from a Git repository.

Check Python:

    python --version

Create a virtual environment:

    python -m venv .venv

Activate in PowerShell:

    .\.venv\Scripts\Activate.ps1

Or in Command Prompt:

    .venv\Scripts\activate.bat

Install dependencies:

    python -m pip install --upgrade pip
    pip install -r requirements.txt

Inspect the project's settings and environment-variable usage before creating a local environment file.

Never commit secrets, credentials, API keys, private patient information, local database files or private environment files.

## 7. Critical database safety notice

A previous local `migrate` and `seed_demo` operation ran against the existing project db.sqlite3.

The operation reported:
- Four fictional doctors created.
- 168 new slots created.

The database was not inspected or restored afterward.

Therefore:

- Treat the existing database as modified.
- Do not assume that it is clean or unchanged.
- Do not run migrations, seed commands, database resets or cleanup commands against it.
- Preserve the database and any associated SQLite WAL/SHM files before approved recovery activity.
- Identify a known-good backup before attempting restoration.
- Obtain explicit approval before database operations.
- Use a separate disposable development database for approved tests and development.

Do not claim that a backup exists or that restoration has occurred.

## 8. Development and testing

Before running any application or database command, consult AGENTS.md and the safety gates in docs/FINAL_VALIDATION_CHECKLIST.md. Do not use the unverified project database.

The reported P1 verification included:

- 118 Django tests passed.
- `python manage.py check` passed.
- `python manage.py makemigrations --check --dry-run` reported no changes.
- Modified JavaScript files passed `node --check`.
- Local HTTP checks against an isolated temporary database returned HTTP 200 for selected hospital-related resources.

Browser rendering and external tile loading were not verified.

These are historical reported results, not tests performed by this documentation task.

## 9. Documentation index

- AGENTS.md — mandatory AI coding instructions.
- docs/MEDIREACH_PROJECT_MASTER_PLAN.md — central project plan and phase tracker.
- docs/ARCHITECTURE.md — technical architecture.
- docs/DATABASE_SCHEMA.md — database design.
- docs/API_REFERENCE.md — application endpoints.
- docs/FEATURES.md — feature status.
- docs/product-backlog.md — product backlog.
- docs/project-report.md — project report.
- docs/capacity-planning.md — capacity planning.
- docs/planning-poker.md — estimation guidance.
- docs/report-templates.md — report templates.
- docs/scrum-board.csv — project board.
- docs/sprint-plans.md — sprint planning.
- docs/tdd-atdd.md — test-driven development notes.
- docs/DEMO_SCRIPT.md — controlled patient-journey demonstration.
- docs/KNOWN_LIMITATIONS.md — source-reviewed limitations and release constraints.
- docs/FINAL_VALIDATION_CHECKLIST.md — isolated validation plan and release gates.

## 10. Project contribution principles

Every contribution must:

1. Preserve existing functionality.
2. Follow the documented architecture.
3. Avoid duplicate models, services and business logic.
4. Protect patient data and ownership boundaries.
5. Avoid fabricated healthcare information.
6. Include appropriate tests.
7. Document API, schema and behaviour changes.
8. Explain database and migration impact.
9. Update the project master plan.
10. Be reviewed before being treated as complete.

MediReach is developed phase by phase. Do not begin a future phase until its dependencies and acceptance criteria have been reviewed.
