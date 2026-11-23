# MediReach — API and Route Reference

## 1. Purpose

This document lists the routes declared in `portal/urls.py` and the root URL configuration in `config/urls.py`.

It distinguishes:
- Browser pages.
- Form submissions.
- JSON endpoints.
- Hospital-administrator endpoints.

The route list is based on the current URL declarations and view implementation.

A route's existence does not imply that it is a public third-party API.

## 2. General conventions

Base application routes are included at the root URL.

Django administration is mounted at:

`/admin/`

The application routes are defined in:

`portal/urls.py`

Authentication uses Django's configured authentication system.

JSON endpoints use Django `JsonResponse`.

CSRF protection and browser session behaviour follow the Django configuration and middleware.

Unless a view explicitly states otherwise, do not assume an endpoint supports arbitrary HTTP methods.

## 3. Browser routes

| Method | Path | Name | Access / behaviour |
|---|---|---|---|
| GET | `/` | home | Public home page |
| GET, POST | `/register/` | register | Registration form |
| GET, POST | `/login/` | login | Django LoginView |
| POST | `/logout/` | logout | Django LogoutView |
| GET | `/dashboard/` | dashboard | Login required |
| GET, POST | `/profile/` | profile | Login required |
| GET | `/chat/` | chatbot | Login required |
| POST | `/chat/new/` | new_chat | Login required |
| POST | `/chat/send/` | chat_send | Login required; returns JSON |
| GET | `/doctors/` | doctors | Public doctor directory |
| GET | `/doctors/{doctor_id}/` | doctor_detail | Login required |
| POST | `/slots/{slot_id}/book/` | book_appointment | Login required |
| GET | `/appointments/` | appointments | Login required |
| POST | `/appointments/{appointment_id}/cancel/` | cancel_appointment | Login required |
| GET | `/history/` | chat_history | Login required |
| GET, POST | `/notes/` | notes | Login required |
| GET | `/hospitals/` | hospitals | Public hospital directory |
| GET | `/hospitals/{hospital_id}/` | hospital_detail | Public hospital detail |
| GET | `/first-aid/` | first_aid | Public first-aid index |
| GET | `/first-aid/{category}/` | first_aid_detail | Public guide detail |
| GET | `/emergency/` | emergency | Public emergency page |
| GET | `/emergency/summaries/` | emergency_summaries | Login required |
| GET | `/emergency/summaries/{case_id}/` | emergency_summary_detail | Login required; owner-scoped |
| GET, POST | `/emergency-profile/` | emergency_profile | Login required |
| POST | `/emergency-profile/contact/{contact_id}/delete/` | delete_emergency_contact | Login required; owner-scoped |
| GET, POST | `/emergency-profile/contact/{contact_id}/edit/` | edit_emergency_contact | Login required; owner-scoped |
| GET, POST | `/referrals/new/` | referral_new | Login required |
| GET | `/referrals/` | my_referrals | Login required |
| GET, POST | `/enquiries/new/` | hospital_enquiry | Public; authenticated users are associated with their account |

## 4. JSON endpoints

### 4.1 POST `/api/chat`

View: `chat_send`

Authentication:
- Login required.

Purpose:
- Sends a patient message to the active or selected conversation.
- Calls the shared chat response service.
- Persists the user message and assistant reply.
- Updates conversation state.

Request JSON:

```json
{
  "message": "I need help finding a hospital",
  "conversation_id": 1,
  "latitude": 28.6,
  "longitude": 77.3
}
```

Fields:
- `message`: required, non-empty, maximum 2,000 characters.
- `conversation_id`: optional; if supplied, must belong to the authenticated user.
- `latitude`: optional.
- `longitude`: optional.

The exact validation of optional coordinates is governed by the chat/resource implementation.

Response:
- The response object returned by `portal/services/chat.py`.
- It is persisted with the conversation's updated state.
- The precise response keys should be taken from that service implementation.

Errors:
- 405 if method is not POST.
- 400 for invalid JSON, empty message or message over 2,000 characters.
- 404 if the supplied conversation does not belong to the user or does not exist.

No external AI provider is called by this endpoint in the current implementation.

### 4.2 GET `/api/hospitals/nearby`

View: `hospitals_api`

Purpose:
- Search local hospital records.

Query parameters:

| Parameter | Meaning |
|---|---|
| q | Search text |
| location | Manual location text |
| lat | Latitude |
| lon | Longitude |
| emergency | Set to `1` to filter for emergency service |
| icu | Set to `1` to filter for ICU service |
| trauma | Set to `1` to filter for trauma service |
| specialty | Specialty filter |

Response shape:

```json
{
  "results": []
}
```

Each result is produced by the shared hospital search and serialization logic.

Errors:
- 405 if method is not GET.

This endpoint searches existing local application records. It is not a live external provider directory.

### 4.3 GET `/api/hospitals/{hospital_id}`

View: `hospital_details_api`

Purpose:
- Retrieve serialized details for one hospital.

Response:
- A serialized hospital object from `get_hospital_details`.

Errors:
- 404 when the hospital is not found.
- 405 for methods other than GET.

### 4.4 GET `/api/doctors`

View: `doctors_api`

Query parameters:
- `specialty`
- `location`
- `q`

Response:

```json
{
  "results": []
}
```

Results are generated by `search_doctors`.

Errors:
- 405 for methods other than GET.

### 4.5 `/api/first-aid`

View: `first_aid_api`

Method handling:
- The view does not restrict `request.method` or return 405 for other methods.
- Requests that reach the view receive the index JSON response.

Purpose:
- Return the available first-aid guide index.

Response:

```json
{
  "results": []
}
```

### 4.6 `/api/first-aid/{category}`

View: `first_aid_api`

Method handling:
- The view does not restrict `request.method` or return 405 for other methods.
- Requests that reach the view receive the guide JSON response, or 404 when the guide is not found.

Purpose:
- Retrieve one first-aid guide.

The category is a slug.

Response:
- Guide data, including title, situation, warning signs, immediate actions, things to avoid, emergency guidance, source information, review date and disclaimer.

Errors:
- 404 if the guide is not found.

### 4.7 POST `/api/emergency/summary`

View: `emergency_summary_api`

Purpose:
- Generate an emergency summary from user-reported facts.
- Optionally save it to the authenticated user's account.

Request:

```json
{
  "reported_facts": {
    "symptoms": "Reported symptoms",
    "onset": "When symptoms started",
    "temperature": "Reported temperature",
    "relevant_information": "Additional relevant information",
    "actions_taken": "Actions already taken"
  },
  "save": false,
  "location_consent": false
}
```

Allowed `reported_facts` keys:
- symptoms
- onset
- temperature
- relevant_information
- actions_taken

Each value must be text and no longer than 1,000 characters.

Optional location consent:

```json
{
  "location_consent": true,
  "latitude": 28.6,
  "longitude": 77.3
}
```

Coordinates must be numeric, finite and within valid latitude/longitude ranges.

Saving:
- `save: true` requires authentication.
- When saved, an EmergencyCase is created.
- Location is stored only when valid coordinates and consent are provided.

Errors:
- 405 for methods other than POST.
- 400 for invalid JSON, invalid facts or invalid coordinates.
- 401 when saving is requested by an anonymous user.

The endpoint does not dispatch emergency services or notify emergency contacts.

### 4.8 GET `/api/emergency/contacts`

View: `emergency_contacts_api`

Purpose:
- Return emergency contacts for the current user.

Authentication:
- The view itself is not decorated with `login_required`.
- The service must be consulted for anonymous behaviour.

Do not assume anonymous users receive another user's contacts.

### 4.9 POST `/api/emergency/contacts`

View: `emergency_contacts_api`

Purpose:
- Save an emergency contact.

Authentication:
- Required.

Request:

```json
{
  "name": "Contact name",
  "phone": "Contact number",
  "relationship": "Relationship"
}
```

Success:
- HTTP 201.
- Returns contact ID and contact fields.

Errors:
- 400 for invalid JSON or form validation errors.
- 401 for anonymous requests.
- 405 for unsupported methods.

### 4.10 POST `/api/referrals`

View: `referrals_api`

Authentication:
- Login required.

Request:

```json
{
  "hospital": 1,
  "summary": "Referral summary"
}
```

Success:
- HTTP 201.
- Returns ID, status and hospital name.

Errors:
- 400 for invalid JSON or form validation.
- 405 for methods other than POST.

The referral is stored locally and is not externally delivered.

### 4.11 Hospital-admin services

Path:

`/api/hospital-admin/services`

View:
`hospital_admin_services_api`

Authentication:
- Login required.
- HospitalAdministrator profile required.

GET:
- Returns services belonging to the administrator's hospital.

Response includes:
- id
- type
- specialty
- effective status
- source
- updated_at
- expires_at

PUT request:

```json
{
  "services": [
    {
      "id": 1,
      "service_type": "emergency",
      "specialty_name": "",
      "status": "available",
      "details": "Service details",
      "source": "Reported source",
      "expires_at": null
    }
  ]
}
```

The submitted service fields must match HospitalServiceForm.

Success:
- Returns the updated service IDs and effective statuses.

Errors:
- 400 for malformed JSON or validation errors.
- 405 for methods other than GET or PUT.
- 403 for users without hospital-admin access.

Important:
The current implementation processes updates sequentially. Do not assume the entire batch is atomic.

### 4.12 Hospital-admin enquiries

GET `/api/hospital-admin/enquiries`

View:
`hospital_admin_enquiries_api`

Authentication:
- Hospital administrator required.

Returns enquiries belonging to the administrator's assigned hospital.

Result fields:
- id
- hospital
- message
- status
- created_at

Other methods:
- 405.

### 4.13 Update referral status

PATCH `/api/referrals/{referral_id}/status`

View:
`update_referral_status`

Authentication:
- Hospital administrator required.

Request:

```json
{
  "status": "reviewing"
}
```

Allowed statuses:
- received
- reviewing
- information_requested
- acknowledged
- closed

The referral must belong to the administrator's assigned hospital.

Success returns:
- id
- status

Errors:
- 400 for invalid JSON or status.
- 403 for non-authorised users.
- 404 when the referral is not associated with the administrator's hospital.
- 405 for methods other than PATCH.

### 4.14 Update enquiry status

PATCH `/api/enquiries/{enquiry_id}/status`

View:
`update_enquiry_status`

Authentication:
- Hospital administrator required.

Request:

```json
{
  "status": "acknowledged"
}
```

Allowed statuses are the same as Referral.

The enquiry must belong to the administrator's assigned hospital.

Success returns:
- id
- status

Errors:
- 400 for invalid JSON or status.
- 403 for non-authorised users.
- 404 when the enquiry is not associated with the administrator's hospital.
- 405 for methods other than PATCH.

## 5. Additional route declarations

Except for `/chat/send/`, which is a login-required POST JSON endpoint handled by `chat_send`, the following routes are browser/form workflows:

- `/chat/send/`
- `/referrals/new/`
- `/referrals/`
- `/enquiries/new/`
- `/emergency-profile/`
- `/hospital-admin/profile/`
- `/hospital-admin/services/{service_id}/`

The remaining routes should be documented as page or form workflows.

## 6. Hospital-admin browser routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/hospital-admin/` | Admin dashboard |
| POST | `/hospital-admin/profile/` | Update assigned hospital profile |
| POST | `/hospital-admin/services/{service_id}/` | Update assigned hospital service |

These require a valid hospital administrator profile.

## 7. Error and status conventions

Observed JSON error patterns include:

- `400` — malformed JSON, invalid fields or validation errors.
- `401` — authentication required for selected actions.
- `403` — permission failure.
- `404` — requested object not found or not accessible within the scoped query.
- `405` — unsupported HTTP method.

Do not assume every endpoint returns identical error JSON.

### 4.15 POST `/api/providers/discover`

View: `provider_discovery_api`.

Purpose:
- Search MediReach-managed doctors/facilities through the shared provider service.
- Optionally include transient OpenStreetMap mapped listings when `include_osm` is `true` and valid latitude/longitude are supplied.

Relevant JSON fields include `result_types`, `query`, `facility_type`, `specialty`, `location`, `latitude`, `longitude`, `radius_km`, `include_osm`, `trust_category`, and `source_category`. Results remain separate by source and include normalized identifiers, source, trust, and available data. Managed identifiers use `managed:doctor:<id>` or `managed:hospital:<id>`; mapped identifiers use `osm:<element-type>:<id>`. These identifiers supplement the existing numeric `id` field on managed results. Partial source failures are returned in `source_errors` while available managed results can remain present.

Errors:
- 400 for malformed request shape, unsupported result type, invalid coordinate pair, or invalid radius.
- 405 for methods other than POST.

Mapped-source errors are returned in `source_errors` as partial results rather than failing the whole request.

The endpoint does not require login in its view. Browser POST requests remain subject to the configured CSRF middleware.

### 4.16 POST `/api/facilities/osm/nearby`

View: `osm_facilities_api`.

Purpose:
- Return transient nearby OpenStreetMap facilities using explicitly supplied coordinates and a bounded radius. This endpoint is distinct from the unified discovery endpoint and does not persist results.

Request JSON: `latitude`, `longitude`, and optional `radius_km` (default 5; maximum 20 km).

Success includes `results`, `source: "OpenStreetMap"`, attribution, a mapped/not-independently-verified trust label, and the selected radius. Only fields provided by OSM are normalized.

Errors:
- 400 for invalid/missing coordinates or invalid radius.
- 503 for Overpass timeout, rate limit, malformed response, or service error.
- 405 for methods other than POST.

The endpoint does not require login in its view. Browser POST requests remain subject to CSRF middleware.

## 8. External APIs and services

The source includes a user-triggered OpenStreetMap/Overpass adapter for nearby geographic facility listings. It uses bounded requests, timeouts, and a short in-process cache; availability is subject to public service limits. OSM does not verify provider credentials or operational status.

The current inspected implementation does not establish an integration with:
- ABDM HFR.
- NMC/NMR APIs.
- Nominatim.
- A paid maps or places provider.
- A cloud LLM API.
- An external notification provider.

Ollama is an optional local model integration, not an external cloud API.

## 9. API change requirements

When adding or changing an endpoint:

1. Update this reference.
2. Document method and authentication.
3. Document query and body fields.
4. Document success responses.
5. Document errors.
6. Document ownership and role restrictions.
7. Add regression tests.
8. Update the master plan.

---
