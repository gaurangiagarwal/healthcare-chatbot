# MediReach — Feature Catalogue and Implementation Status

## 1. Purpose

This document provides a feature-by-feature view of MediReach.

It distinguishes:
- Implemented functionality.
- Partial functionality.
- Planned functionality.
- Functionality requiring browser verification.
- Features that must not be claimed as complete.

Statuses describe source inspected during P6. They do not establish runtime, database, network, or browser behavior.

They are not a substitute for end-to-end verification.

## 2. Status definitions

| Status | Meaning |
|---|---|
| Implemented | Core functionality exists in the current code |
| Partially implemented | Some functionality exists, but important parts remain |
| Not implemented | No complete implementation is present |
| Needs browser verification | Source exists but real browser behaviour has not been confirmed |
| Blocked | Cannot proceed until a dependency or decision is resolved |

A feature must not be marked complete based only on an AI coding agent's report.

## 3. Authentication and patient accounts

### Registration

Status: Implemented.

Existing behaviour:
- User registration through RegisterForm.
- Email validation.
- PatientProfile creation.
- Automatic login after registration.

### Login and logout

Status: Implemented.

Uses Django authentication views.

### Patient profile

Status: Implemented.

Profile fields:
- Age.
- Gender.
- Phone.
- Health information.
- User first name and email.

Further work:
- Privacy review.
- Data minimisation.
- Account data export and deletion planning.
- Production security review.

## 4. Dashboard

Status: Implemented.

The dashboard displays patient-owned summaries, including:
- Recent chat conversations.
- Recent emergency contacts.
- Recent emergency summaries.
- Recent appointment requests.
- Recent referrals.
- Recent enquiries.
- Chat message count.

Further work:
- End-to-end usability review.
- Responsive browser testing.
- Clear empty states.

## 5. Chat assistant

Status: Partially implemented.

Existing components:
- ChatConversation.
- ChatMessage.
- `portal/services/chat.py`.
- `portal/services/safety.py`.
- `portal/chatbot.py`.
- `static/portal/chatbot.js`.

Existing capabilities:
- Conversation creation.
- Patient-scoped conversations.
- Persisted user and assistant messages.
- Rule-based intent handling.
- Hospital discovery intent.
- Doctor discovery intent.
- First-aid intent.
- Emergency priority handling.
- Conversation state.

Limitations:
- Not a completed medically reviewed AI system.
- Optional local Ollama integration exists for general fallback questions; availability and output safety still require runtime evaluation.
- Not a general-purpose diagnostic assistant.
- Structured symptom navigation is implemented for a limited symptom set; it is not comprehensive.
- Two rule-based modules remain (`portal/chatbot.py` and `portal/services/chat.py`) and must both be understood before changes.

Source implementation is present; clinical evaluation and runtime/browser validation remain outstanding.

## 6. Emergency assistance

Status: Implemented provisionally; browser verification pending.

Existing capabilities:
- Deterministic emergency assessment.
- Emergency warning-sign detection.
- Negation and historical-context handling.
- Emergency page.
- Emergency call action using 112.
- Emergency summary generation.
- Optional saving of emergency summaries.
- Location consent and coordinate validation.

Limitations:
- No automatic emergency dispatch.
- No automatic ambulance booking.
- No automatic emergency-contact notification.
- Browser-level execution must be verified.
- Emergency safety coverage requires continued testing.

Future work:
- Browser-level emergency journey tests.
- Safety evaluation.
- Clear user-facing limitations.

## 7. First-aid guidance

Status: Partially implemented.

Existing implementation:
- Curated guides in `portal/services/first_aid.py`.
- Guide retrieval and listing.
- First-aid pages and JSON endpoints.
- Source URLs and review date.
- Warning signs.
- Immediate actions.
- Things to avoid.
- Emergency escalation guidance.
- Disclaimer.

Existing categories include:
- Burns.
- Bleeding.
- Choking.
- Fractures.
- Seizures.
- Stroke.
- Cardiac emergencies.
- Severe allergic reactions.

Future work:
- Medical content review.
- Review schedule.
- Additional trusted sources.
- Versioned content governance.
- Testing of unsafe or ambiguous requests.

## 8. Doctor directory

Status: Implemented locally.

Existing functionality:
- Doctor listing.
- Search.
- Specialty filtering.
- Location filtering.
- Doctor detail page.
- Hospital relationship.
- Verification status.
- Contact route.
- Local appointment slots.
- Structured specialties and current/historical facility affiliations through provider foundation models.
- Provenance and source/trust labels.

Limitations:
- Existing local records are not a complete live directory.
- Demo records are fictional and unverified.
- Qualification text is not proof of professional registration.
- No unrestricted professional registry API is established.

Future work:
- Authorized credential verification workflow and reviewer permissions.
- External official source adapters when access is approved.

## 9. Hospital directory

Status: Implemented locally.

Existing functionality:
- Hospital listing.
- Text search.
- City/location filtering.
- Emergency service filter.
- ICU filter.
- Trauma filter.
- Specialty filter.
- Hospital detail page.
- Hospital services.
- Verification status.
- Coordinates.
- Website and phone fields.
- Facility type and operational status fields.
- Shared source, verification, and contact records.

Limitations:
- Local records only.
- Demo hospitals are fictional and unverified.
- Service information may be reported and may expire.
- A local record does not prove current operational availability.

Future work:
- Authorized verification workflow and data freshness.
- External official provider sources when access is approved.

## 10. Hospital map

Status: Needs browser verification.

Existing implementation:
- Leaflet.
- OpenStreetMap tile configuration and user-triggered nearby Overpass discovery.
- Managed hospital coordinates and separate transient mapped results.
- Map/list presentation.
- Coordinate validation.
- Failure fallback.
- OpenStreetMap attribution.

Known limitations:
- Browser rendering, external tile loading, browser geolocation, and live Overpass behavior were not verified in P6.
- OSM results are mapped listings, not independently verified providers or evidence of operating status/capacity.

Required QA:
- Map initialization.
- Tile loading.
- Attribution.
- Coordinate handling.
- Marker rendering.
- Fallback list.
- Browser console.
- Network errors.

## 11. Appointment workflows

Status: Implemented locally.

Existing capabilities:
- Doctor appointment slots.
- Future-slot filtering.
- Local appointment creation.
- Active booking uniqueness.
- Patient appointment listing.
- Patient-scoped cancellation.
- Prevention of booking expired slots.

Important limitation:
The current workflow records a local demo booking.

No provider is contacted and no external appointment is confirmed.

Future work:
- Provider request lifecycle.
- Provider response.
- Confirmation.
- Cancellation communication.
- Audit trail.
- Real notification integration if approved.

## 12. Referrals

Status: Implemented locally.

Existing capabilities:
- Referral form.
- Local Referral records.
- Patient-owned referral listing.
- Hospital-admin visibility.
- Hospital-admin status updates.
- Audit logging for status changes.

Limitations:
- No external referral delivery is established.
- Local status does not prove an external hospital received the referral.

Future work:
- Provider response workflow.
- Delivery status.
- Patient tracking.
- Audit improvements.

## 13. Hospital enquiries

Status: Implemented locally.

Existing capabilities:
- Hospital enquiry form.
- Optional anonymous submission.
- Local HospitalEnquiry record.
- Patient tracking for authenticated enquiries.
- Hospital-admin enquiry visibility.
- Hospital-admin status update.

Limitations:
- Anonymous enquiries cannot be tracked by the submitter.
- Enquiries are not externally delivered by the current implementation.
- Local acknowledgement is not proof of hospital acknowledgement.

Future work:
- Delivery mechanism.
- Anonymous tracking decision.
- Provider response lifecycle.
- Notification mechanism.

## 14. Emergency contacts

Status: Implemented.

Existing capabilities:
- Create emergency contacts.
- Edit emergency contacts.
- Delete emergency contacts.
- Patient-owned listing.
- JSON contact endpoint.

Limitation:
Stored contacts are not automatically notified during emergencies.

Future work:
- Explicit consent.
- Secure notification design.
- Delivery evidence.
- Failure handling.
- Audit trail.

## 15. Emergency summaries

Status: Implemented.

Existing capabilities:
- User-reported facts.
- Optional location sharing.
- Coordinate validation.
- Summary generation.
- Optional authenticated saving.
- Patient-owned summary listing and detail view.

Limitations:
- A summary is not an emergency dispatch.
- Saving a summary does not notify emergency services or contacts.

## 16. Patient notes

Status: Implemented.

Existing capabilities:
- Patient-owned notes.
- Note title.
- Note body.
- Creation timestamp.
- Patient-scoped listing.

Future work:
- Editing and deletion review.
- Export and retention policy.
- Privacy review.

## 17. Patient history

Status: Implemented.

Existing capabilities:
- Patient chat history.
- Search by message text.
- Patient-scoped retrieval.

Future work:
- Improved filtering.
- Export.
- Retention and deletion controls.

## 18. Hospital administration

Status: Partially implemented.

Existing capabilities:
- HospitalAdministrator association.
- Hospital-scoped dashboard.
- Hospital profile updates.
- Hospital service updates.
- Enquiry visibility.
- Referral visibility.
- Audit logs.
- Service status API.
- Referral status API.
- Enquiry status API.

Limitations:
- The batch service update endpoint processes records sequentially and is not guaranteed atomic.
- Production role-management and account-provisioning processes need review.
- Service status must not be confused with verified real-time capacity.

Future work:
- Stronger transactional handling.
- Admin audit review.
- Verification workflows.
- Role provisioning.
- Browser testing.

## 19. Provider discovery and verification

Status: Partially implemented; not a complete verified provider directory.

Current foundation:
- Doctor and Hospital models.
- Verification status fields.
- Hospital service provenance fields.
- Local search services.
- ProviderSourceRecord, ProviderVerification, ProviderContact, Specialty, DoctorSpecialty, and DoctorHospitalAffiliation schema.
- Shared managed/OSM discovery boundary.
- Transient nearby OpenStreetMap/Overpass results with attribution and mapped/unverified trust label.

Not yet established:
- Nominatim integration.
- ABDM HFR integration.
- Professional registry integration.
- Authorized reviewer permission and verification decision workflow.
- Data freshness pipeline.
- Provider persistence or contact with external sources.

P2/P3 implementation source exists; database and browser validation remain outstanding.

## 20. Diagnostic-centre discovery

Status: Partially implemented through generic facility types and explicitly tagged mapped results; not a complete service.

The Hospital model has diagnostic-centre/imaging-centre categories, and OSM normalization supports diagnostic-centre/laboratory tags. There is no complete diagnostic service catalogue, verified diagnostic-provider directory, or dedicated booking workflow.

Future work:
- Provider data design.
- Facility category support.
- Diagnostic service representation.
- Discovery and verification.
- Search and map integration.

## 21. Notifications and external communication

Status: Not implemented as a complete delivery system.

Current local records do not establish:
- SMS delivery.
- Email delivery.
- WhatsApp delivery.
- Provider communication.
- Emergency-contact notification.
- External referral delivery.

A future notification adapter requires explicit approval and evidence-based status reporting.

## 22. AI and local model integration

Status: Partially implemented; local assistant behavior is not clinically validated.

The current application uses deterministic emergency screening, structured symptom flow, reviewed first-aid content, rule-based intent handling, deterministic fallback, and optional local Ollama for general fallback replies.

Remaining work:
- Expand and govern reviewed medical knowledge.
- Evaluate clinical safety and adversarial prompts.
- Validate Ollama integration and fallback behavior in the approved runtime.
- Keep emergency rules independent of model output.

No paid cloud LLM API is approved under the current zero-budget constraint.

## 23. Production readiness

Status: Not established.

Outstanding areas include:
- Production settings.
- Secret management.
- Deployment configuration.
- Database recovery.
- Backup strategy.
- Security review.
- Privacy and retention.
- Browser and end-to-end testing.
- External integration governance.
- Accessibility.
- Monitoring and error handling.

## 24. Feature roadmap mapping

| Feature | Phase |
|---|---|
| Emergency safety refinement | P0 |
| Core workflow repair | P1 |
| Documentation | P1.5 |
| Provider data foundation | P2 |
| Open provider discovery | P3 |
| Hybrid assistant | P4 |
| Care coordination | P5 |
| Integration and release QA | P6 |

## 25. Feature completion policy

A feature may be marked COMPLETED only when:

1. Its acceptance criteria are met.
2. Relevant tests pass.
3. Ownership and permissions are verified.
4. Database impact is reviewed.
5. Browser behaviour is verified where relevant.
6. Known limitations are documented.
7. Documentation is updated.
8. A human reviewer approves it.

A working interface alone is not proof that a feature is complete.
