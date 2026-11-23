# MediReach MVP Demo Script

**Length:** 5–7 minutes  
**Purpose:** Demonstrate the current patient journey and its limits. This script is for a controlled demonstration, not clinical use.

## Before the demo

- Use an approved, working environment. The repository's existing `db.sqlite3` is unverified and must not be used for validation until a separate recovery plan is approved.
- Use only records that are actually present in that environment. Do not add or imply real provider data for the demo.
- If there are no eligible doctor slots, use the referral request as the care-coordination example instead of implying availability.
- Nearby OpenStreetMap discovery requires a user-initiated search and an available Overpass service. If it is unavailable, show the managed directory list and explain the limitation.
- Do not place an emergency call or submit requests to real facilities during the demo.

## Patient journey

### 0:00–0:45 — Open MediReach

Start on the home page. Point out the emergency call action, assistant, first-aid guide, doctor directory and facility finder. Explain that the application provides navigation and local coordination; it does not dispatch emergency services.

### 0:45–1:30 — Demonstrate emergency guidance

Open the assistant and select its **Emergency medical assistance** welcome prompt. Show that the assistant presents its urgent warning and a **Call 112** action. Do not activate the telephone link. State clearly that the call action opens the user's phone interface and that MediReach has not contacted anyone.

### 1:30–2:30 — Demonstrate a normal symptom conversation

Start a separate normal conversation, for example: “I have had a cough since yesterday.” Show the one-question-at-a-time follow-up and the option to stop. Explain that the assistant records user-reported context, gives cautious general guidance, and does not diagnose or prescribe. If local Ollama is unavailable or not configured, explain that the deterministic fallback is expected.

### 2:30–3:45 — Discover doctors and facilities

Browse doctor profiles using a specialty or city filter. Open a profile and point out its source and trust label. **DEMO** means fictional demonstration data; **unverified**, **pending**, **verified**, **rejected**, **revoked**, and **expired** describe the displayed verification state. A source record alone is not verification.

Open the facility finder. The ordinary list is backed by MediReach records. To show mapped discovery, enter coordinates or explicitly choose the browser location action and submit the nearby search. Explain that OpenStreetMap listings are separate, mapped records, are not independently verified, and do not establish that a site is open, operating, or accepting patients. Keep OpenStreetMap attribution visible. If the map tiles or Overpass service fail, use the facility list and its status message.

### 3:45–5:00 — Review a provider and make a local request

Open a facility detail page and review its stored source, trust label, reported services and contact labels. Explain that service reports are not live capacity. If a future local doctor slot is shown, submit a local demo booking request; otherwise skip booking. Explain that the request is saved in MediReach and no provider is contacted or asked to confirm it.

Alternatively, open a facility's referral action, review the selected facility and submit a concise demo referral reason. Referrals and enquiries are stored locally; they are not delivered to or accepted by a facility.

### 5:00–6:00 — Show request tracking

Open **Appointments** or **My Requests** and show the local status and next step. Then open the patient dashboard to show that signed-in records are scoped to that patient. Do not use another patient's account or reveal another person's data.

### 6:00–7:00 — Close with limits

Summarize: emergency calls are user-initiated; mapped listings are not verified providers; demo profiles are fictional; local booking, referral and enquiry records are not provider confirmations or deliveries. Production readiness, database compatibility, live browser behavior and external service reliability remain to be validated.

## Stop conditions

- If a real emergency is reported, stop the demonstration and direct the person to call 112 or seek immediate local emergency help. Do not continue the chatbot demo.
- Do not present any demo record as a real clinician or facility.
- Do not claim a contact was notified, an appointment was confirmed, or a facility received or accepted a request.
- Do not expose real patient history, contacts, messages or request details on a shared screen.
