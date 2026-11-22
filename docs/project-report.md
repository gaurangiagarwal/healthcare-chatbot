# Healthcare Chatbot and Patient Assistance System

**Agile Software Development Mini Project**  
Student: _[Your name]_ · Institution: _[College]_ · Guide: _[Faculty guide]_ · Submission date: _[Date]_

## 1. Title Page

Customize the fields above to match the college's prescribed cover page.

## 2. Abstract

CareBridge is a Django web application for patient account/profile management, general rule-based health guidance, fictional doctor search, appointment booking, and personal history. Four incremental sprint plans demonstrate an Agile approach. Automated tests cover core workflows and privacy boundaries. The assistant is educational only and does not diagnose or prescribe.

## 3. Introduction

Digital patient support can bring common self-service activities into one accessible interface. This project combines account access, educational information, appointment discovery, and personal activity tracking in a small demonstrable web system.

## 4. Problem Statement

Patients may need a straightforward way to find general symptom information and keep their own appointment and health activity details together. A student-scale solution should demonstrate these workflows while limiting unsafe medical claims and preventing access to other users' records.

## 5. Objectives

1. Provide secure patient registration, login, and profile management.
2. Give safe general guidance for a small set of common health topics.
3. Support doctor search and prevention of duplicate appointment slot booking.
4. Keep chatbot history, appointment data, and notes scoped to their owner.
5. Demonstrate four-sprint Agile planning, acceptance tests, CI, and deployment preparation.

## 6. Agile Methodology

Work is organized into four proposed 10-working-day sprints, with a demonstrable increment per sprint. Backlog priority and story points are examples for team refinement. Actual planning, reviews, retrospectives, capacity, and velocity must be completed and recorded by the student team.

## 7. Team Roles

Suggested roles: Product Owner (prioritizes value), Scrum Master (facilitates and removes blockers), Developer(s) (design and implementation), QA/UX (acceptance, testing, usability). The sample capacity sheet uses fictional Member A–E placeholders; replace them with actual team assignments.

## 8. Product Backlog

See [`product-backlog.md`](product-backlog.md) for eight stories, epics, priorities, proposed points, acceptance criteria, sprint assignments, and initial status.

## 9. User Stories

US-01/02 cover secure access and profile. US-03/04 cover symptom guidance and common health questions. US-05/06 cover doctor search and booking. US-07/08 cover chat, appointment, and medical-note history. Full As-a/I-want/so-that statements are in the product backlog.

## 10. Planning Poker Estimation

The example uses the Fibonacci sequence (1, 2, 3, 5, 8, 13) and four hypothetical estimates. They are clearly sample estimates, not a claimed planning poker session. Reasoning and consensus examples appear in [`planning-poker.md`](planning-poker.md).

## 11. Sprint Planning

Sprint 1: US-01/02 (8 sample points). Sprint 2: US-03/04 (13). Sprint 3: US-05/06 (11). Sprint 4: US-07/08 (8). Goals, tasks, acceptance, deliverables, and review checklists are in [`sprint-plans.md`](sprint-plans.md).

## 12. Acceptance Criteria

Criteria are maintained per story in `product-backlog.md`, including duplicate account handling, authentication, safe fallback/emergency behavior, patient data isolation, and unique active appointments. Given–When–Then ATDD examples are included there for all eight stories.

## 13. Definition of Done

A story is Done when functionality is implemented; acceptance criteria pass; unit/integration tests pass; code is reviewed; no critical bugs remain; changes are committed; documentation is updated; and the feature can be demonstrated. These are team process criteria, not a claim that historical ceremonies occurred.

## 14. TDD and ATDD

The suite in `portal/tests.py` gives automated examples for account, chatbot, booking, and patient ownership behaviors. [`tdd-atdd.md`](tdd-atdd.md) describes how to capture real Red–Green–Refactor outputs. No fabricated historical test sequence is claimed.

## 15. Scrum Board

Workflow: To Do → Development in Progress → Testing in Progress → Verification → Done. Import-ready story data is in [`scrum-board.csv`](scrum-board.csv). No Jira or Trello board is claimed as created.

## 16. Capacity Planning

An editable example for five members, 10 working days, ceremony allowance, availability, and focus factor is in [`capacity-planning.md`](capacity-planning.md). Values are sample assumptions, not actual team data.

## 17. System Architecture

Browser templates use Bootstrap and JavaScript Fetch for chat. Django URLs route to views and forms; Django ORM persists users, profile, messages, doctors, slots, appointments, and notes in SQLite locally or PostgreSQL via `DATABASE_URL`. CSRF middleware protects forms and chat POSTs. Ownership filters scope private information to the signed-in user.

## 18. Database Design

- User has one `PatientProfile`.
- `Doctor` has many `AppointmentSlot` records.
- `Appointment` joins patient to slot; a conditional unique constraint permits one active booking per slot.
- `ChatMessage` and `MedicalNote` each belong to one patient.

## 19. Implementation

The application is divided into Django configuration (`config`) and feature application (`portal`) with templates, static styling, and a `seed_demo` command. Chat rules prioritize emergency warning terms before ordinary symptom topics. `select_for_update` and a database constraint protect booking against concurrent duplicate requests.

## 20. Testing

The included Django TestCase suite checks registration and password hashing, duplicate email, protected dashboard, login error, profile update, chat normal/unknown/emergency behavior and persistence, patient-scoped history/notes, search, booking, cancellation, past slots, and unauthorized cancellation. Record the actual output of `python manage.py test` in `report-templates.md`; do not pre-fill pass counts.

## 21. GitHub and CI/CD

`.gitignore` excludes local secrets, SQLite, and generated assets. GitHub Actions installs dependencies, checks Django, migrates the test database, and runs tests. Branch strategy and sample push commands are in README. A remote repository/push is not asserted.

## 22. Deployment

The application reads `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL`; WhiteNoise serves collected static files and Gunicorn runs WSGI. Use persistent PostgreSQL, HTTPS, secure cookies, valid host configuration, and migrations. See README for commands. No live deployment is claimed.

## 23. Sprint Reviews and Retrospectives

Use the review and retrospective templates in [`report-templates.md`](report-templates.md) after actual sprint events. No feedback, review, or retrospective outcome is invented in this report.

## 24. Results

The repository contains a runnable Django application and test suite. Insert actual check/test output, screenshots, and observed demo results after running the project. Do not report unobserved results as facts.

## 25. Conclusion

CareBridge demonstrates a small end-to-end patient assistance workflow with authentication, safe educational chat, booking controls, and patient-owned history. The Agile artifacts are structured for a student team to refine and complete with real activity evidence.

## 26. Future Enhancements

Add clinician-managed availability, email verification and password reset, audit/privacy controls appropriate to a real deployment, localization/accessibility review, richer appointment notifications, and clinically governed content review. Any real health use requires appropriate security, privacy, and clinical evaluation.
