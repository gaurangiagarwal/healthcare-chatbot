# Sprint plans

Each sprint is an adjustable **10 working day** sample. Proposed points are planning examples, not measured team velocity.

## Sprint 1 — secure patient access (8 points)

Stories US-01 (5), US-02 (3). Tasks: configure Django/auth; implement registration and password validation; create profile model/form; protect dashboard; add auth/profile tests; review usability and errors. Acceptance: backlog criteria US-01/02. Deliverable: account, profile, dashboard increment. Review: register, duplicate email, invalid login, sign out, update profile, direct unauthenticated URL.

## Sprint 2 — safe guidance (13 points)

Stories US-03 (8), US-04 (5). Tasks: define supported rules and boundaries; implement emergency keyword priority; build chat page and fetch endpoint; persist messages; test normal/unknown/emergency cases; review disclaimer and mobile layout. Deliverable: authenticated rule-based assistant. Review: submit each supported topic, unknown request, emergency phrase, refresh and inspect history.

## Sprint 3 — doctor search and booking (11 points)

Stories US-05 (3), US-06 (8). Tasks: doctor/slot/appointment models; sample seed command; specialty/name search; detail and open slot views; atomic booking and uniqueness; cancellation; tests for taken/past slots and ownership. Deliverable: searchable directory and appointment lifecycle. Review: seed data, find doctor, book, attempt duplicate, cancel, rebook.

## Sprint 4 — patient continuity (8 points)

Stories US-07 (3), US-08 (5). Tasks: patient-filtered history/search; appointment history; medical notes; dashboard counts and upcoming visits; cross-account checks; responsive/error review. Deliverable: patient history and activity summary. Review: inspect own history/notes, verify isolation with second user, check desktop/mobile layouts.

## Common sprint review checklist

- Demonstrate each accepted story against its criteria.
- Review automated test and system-check output; record actual results and defects.
- Collect stakeholder feedback and create backlog follow-ups.
- Do not mark work Done until Definition of Done is met.
