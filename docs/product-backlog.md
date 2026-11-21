# Product backlog

All estimates and sprint allocations below are editable planning examples. The team should validate them together before treating them as commitments. Status starts at **To Do**.

| ID | Epic | User story | Priority | Points | Sprint | Status |
|---|---|---|---|---:|---:|---|
| US-01 | Patient access | As a patient, I want to register and log in so that I can securely access my healthcare dashboard. | Must | 5 | 1 | To Do |
| US-02 | Patient access | As a patient, I want to update my profile so that my information remains accurate. | Must | 3 | 1 | To Do |
| US-03 | Guidance | As a patient, I want to describe symptoms to a chatbot so that I can receive general guidance. | Must | 8 | 2 | To Do |
| US-04 | Guidance | As a patient, I want to ask health questions so that I can learn about common symptoms and prevention. | Should | 5 | 2 | To Do |
| US-05 | Appointments | As a patient, I want to search doctors by specialization so that I can find a suitable doctor. | Must | 3 | 3 | To Do |
| US-06 | Appointments | As a patient, I want to book an appointment so that I can schedule a consultation. | Must | 8 | 3 | To Do |
| US-07 | Patient records | As a patient, I want to view previous chatbot conversations so that I can refer to earlier guidance. | Should | 3 | 4 | To Do |
| US-08 | Patient records | As a patient, I want appointment and medical history so that I can track my activities. | Should | 5 | 4 | To Do |

## Acceptance criteria

- **US-01:** registration validates fields and password; duplicate username/email is rejected; password is hashed; login errors are clear; private routes require authentication.
- **US-02:** a logged-in patient can change their own profile; invalid fields are explained; another account's profile cannot be edited.
- **US-03:** symptom text receives safe general guidance, relevant follow-up, and urgent escalation for predefined danger signs; messages are persisted to the patient.
- **US-04:** supported common topics get relevant educational replies; unsupported questions receive a safe fallback; no diagnosis or prescription is presented.
- **US-05:** authenticated patients can search by doctor name or specialization and see future open slots.
- **US-06:** future open slot can be booked once; past/taken slot is rejected; patient can see/cancel own booking; cancellation frees the slot.
- **US-07:** patient can search their own chat history; other patients' messages are inaccessible.
- **US-08:** patient can see own appointment statuses and add/read private notes; dashboard counts reflect account data.

## Given / When / Then ATDD scenarios

| Story | Given | When | Then |
|---|---|---|---|
| US-01 | a visitor supplies unique valid details | they submit registration and sign in | a patient account is created with a hashed password and protected dashboard access |
| US-02 | a signed-in patient has a profile | they save valid updated details | their own profile reflects the changes |
| US-03 | a patient is on the chat page | they submit a supported symptom or emergency warning | a safe, relevant response is shown and both messages are stored; emergency text escalates immediately |
| US-04 | a patient asks a common or unknown question | the chatbot evaluates it | supported topics get educational information and unknown topics get a clinician referral fallback |
| US-05 | doctors are seeded | a patient searches a specialty | matching fictional doctors and future availability appear |
| US-06 | a future slot is open | a patient books it | exactly one active appointment exists and it appears in their list |
| US-07 | a patient has saved messages | they search history | only matching messages belonging to that patient appear |
| US-08 | a patient has appointments and notes | they open history and add a note | their own statuses and saved note appear on subsequent requests |
