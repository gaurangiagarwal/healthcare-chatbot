<<<<<<< HEAD
# CareBridge — Healthcare Chatbot and Patient Assistance System

CareBridge is a college Agile mini project built with Django. It gives patients a protected dashboard, private profile and notes, educational rule-based health chat, and a fictional doctor directory with appointment booking. The chatbot is not a medical device and does not diagnose or prescribe.

## Problem statement and objectives

Patients benefit from a single simple place to explore general health information, keep track of their interactions, and find appointment options. This project demonstrates authentication, patient-owned records, safe rule-based responses, transactional booking, responsive UI, test-driven feature development, and a four-sprint Agile plan.

## Features

- Django registration/login/logout, hashed passwords, profile editing, protected routes.
- AJAX chat for fever, cough, headache, stomach pain, sore throat, prevention, unknown questions, and emergency warning terms. Conversations are saved per account.
- Searchable fictional doctor directory, seeded future slots, booking/cancellation, unique active booking constraint.
- Patient-only chat history search, appointment history, notes, and activity dashboard.
- Bootstrap responsive layout, SQLite local database, PostgreSQL-compatible production database URL, WhiteNoise static files, CI workflow.

## Technology stack

Python 3.12+; Django 5.x; SQLite locally; PostgreSQL in production; HTML/CSS, Bootstrap 5, JavaScript Fetch API; Django TestCase; Git and GitHub Actions. Bootstrap is loaded from its public CDN; for offline deployment, vendor the assets locally.

## Local installation

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000/. Register a patient account through the site. There are no seeded patient passwords. Create a Django admin account if desired with `python manage.py createsuperuser`.

The chatbot keeps a separate context for each patient's conversation. Use **New conversation** in the chat page to start with empty context. Bot replies appear after a short three-second typing indicator.

Settings load the optional `.env` file from the project root. Keep its generated secret private; `.gitignore` excludes it.

## Checks and tests

```powershell
python manage.py check
python manage.py makemigrations portal  # only if model changes have no migration yet
python manage.py migrate
python manage.py test
```

The tests use Django's isolated test database and fictional fixtures. They do not verify production deployment or an actual team Agile ceremony. CI runs check, migration, and tests on pushes and pull requests.

## Project structure

```text
config/                 settings, URLs, WSGI
portal/                 models, views, forms, chatbot, tests, seed command
templates/portal/       responsive pages
static/portal/          styles
docs/                   Agile planning, estimation, reports, project report
.github/workflows/       CI
```

## Agile sprint breakdown

1. US-01/02: authentication, patient profile, dashboard.
2. US-03/04: safe rule-based assistant, AJAX, saved messages.
3. US-05/06: clinician search and transactional appointments.
4. US-07/08: chat/appointment history, private notes, dashboard improvements.

The docs contain a product backlog, sample planning poker, 10-day sprint plans, ATDD scenarios, Definition of Done, sample capacity, reporting templates, and Jira/Trello-ready CSV. Names, points, capacity, and sprint outcomes are planning examples. Have the actual team review estimates and record real ceremony outcomes. Do not mark the sample board Done based on this README.

## Demonstration checklist

- **Sprint 1:** register; verify duplicate email and invalid login behavior; edit profile; confirm dashboard redirects signed-out visitors.
- **Sprint 2:** send supported symptom, unknown question, and emergency term; inspect dynamic responses; refresh and review saved conversation.
- **Sprint 3:** run `seed_demo`; search a specialty; book an open future slot; confirm same slot cannot be booked twice; cancel and book again.
- **Sprint 4:** inspect and search own chat history; add personal note; review upcoming/history status and dashboard counts; sign in as another account and verify records are isolated.

## Git / GitHub

Recommended branches: `main`, `develop`, and `feature/sprint1-authentication`, `feature/sprint2-chatbot`, `feature/sprint3-appointments`, `feature/sprint4-history`. Use pull requests and review against the Definition of Done. This workspace does not assert a remote GitHub repository exists.

```powershell
git init
git add .
git commit -m "Build CareBridge healthcare assistance system"
gh repo create healthcare-chatbot-patient-assistance --public --source=. --remote=origin --push
```

The last command requires GitHub CLI authentication and a deliberate choice of public/private visibility. Review patient data and repository visibility before publishing. Do not commit `.env` or real patient information.

## Deployment (Render or similar)

Use a Python web service with build command `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`, start command `gunicorn config.wsgi:application`. Configure `SECRET_KEY` to a generated secret, `DEBUG=False`, `ALLOWED_HOSTS` to the service hostname, `DATABASE_URL` to a persistent PostgreSQL instance, and `SECURE_SSL_REDIRECT=True`. Run migrations as a release/pre-deploy command where supported. Then run `python manage.py seed_demo` if fictional demo data is wanted. Never use SQLite on ephemeral production disk for persistent patient records.

Before production: use HTTPS; restrict hosts; rotate secrets; verify backups and retention; configure database access and monitoring; review privacy/legal obligations for health data; use a real secure healthcare system for actual patient information. The sample app is educational and not certified for clinical use. No deployment URL is claimed.

## Screenshots

Add your own screenshots after running the application. Do not use fabricated screenshots as evidence of a deployment or team review.
=======
# healthcare-chatbot
Healthcare Chatbot developed using Django and Agile Scrum methodology
>>>>>>> 609fc60b4060c96c9e045369310bf9cfb704ce79
