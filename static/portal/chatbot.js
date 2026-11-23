(() => {
  const form = document.getElementById('chat-form');
  if (!form) return;
  const input = document.getElementById('chat-input');
  const log = document.getElementById('chat-log');
  const error = document.getElementById('chat-error');
  const send = form.querySelector('button[type="submit"]');
  const panel = document.getElementById('context-panel');
  const shareLocation = document.getElementById('share-chat-location');
  const stopFlow = document.getElementById('stop-symptom-flow');
  const locationStatus = document.getElementById('chat-location-status');
  let sharedCoordinates = null;

  shareLocation?.addEventListener('click', () => {
    if (!navigator.geolocation) {
      locationStatus.textContent = 'Location is unavailable; use the hospital finder and enter coordinates instead.';
      return;
    }
    shareLocation.disabled = true;
    locationStatus.textContent = 'Waiting for browser location permission...';
    navigator.geolocation.getCurrentPosition((position) => {
      sharedCoordinates = {latitude: position.coords.latitude, longitude: position.coords.longitude};
      locationStatus.textContent = 'Location is ready for one provider search only and is not saved in chat history.';
      shareLocation.disabled = false;
    }, () => {
      locationStatus.textContent = 'Location was not shared. You can still search without mapped results.';
      shareLocation.disabled = false;
    }, {enableHighAccuracy: false, timeout: 8000});
  });

  document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => {
    input.value = button.dataset.prompt;
    input.focus();
  }));
  stopFlow?.addEventListener('click', () => {
    input.value = 'Stop symptom questions';
    form.requestSubmit();
  });
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message || send.disabled) return;
    document.querySelector('.welcome-state')?.remove();
    const userRow = appendMessage(message, 'user');
    input.value = '';
    error.hidden = true;
    send.disabled = true;
    send.querySelector('[data-send-label]').textContent = 'Sending...';
    const typing = appendMessage('MediReach is preparing a response...', 'bot', true);
    try {
      const payload = {message, conversation_id: window.mediReachChat.conversationId};
      const providerSearch = /\b(?:hospital|hospitals|clinic|clinics|pharmacy|pharmacies|laborator|diagnostic|doctor|doctors|dentist|dentistry|dental|specialist|cardiologist|cardiology|dermatologist|dermatology|pediatrician|paediatrician|neurologist|neurology)\b/i.test(message);
      if (sharedCoordinates && providerSearch) {
        Object.assign(payload, sharedCoordinates);
        sharedCoordinates = null;
        locationStatus.textContent = 'Shared location used for that nearby search and not retained by this page.';
      }
      const response = await fetch(window.mediReachChat.sendUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]').value},
        body: JSON.stringify(payload),
      });
      let data;
      try {
        data = await response.json();
      } catch (_) {
        throw new Error('The assistant returned an unreadable response. Please try again.');
      }
      if (!response.ok) {
        throw new Error(response.status >= 500
          ? 'The assistant is temporarily unavailable. Please try again.'
          : 'Unable to send your message. Please check it and try again.');
      }
      if (!data || typeof data.reply !== 'string') {
        throw new Error('The assistant returned an incomplete response. Your message is still in the composer.');
      }
      typing.remove();
      appendMessage(data.reply, 'bot');
      renderContext(data);
    } catch (requestError) {
      typing.remove();
      userRow.remove();
      input.value = message;
      error.textContent = `${requestError.message || 'The assistant could not respond.'} Your message is still in the composer.`;
      error.hidden = false;
    } finally {
      send.disabled = false;
      send.querySelector('[data-send-label]').textContent = 'Send';
      input.focus();
    }
  });

  function appendMessage(text, role, typing = false) {
    const row = document.createElement('article');
    row.className = `message-row ${role}${typing ? ' is-typing' : ''}`;
    const avatar = document.createElement('span'); avatar.className = 'message-avatar'; avatar.textContent = role === 'bot' ? 'M' : 'You';
    const content = document.createElement('div'); content.className = 'message-content';
    const bubble = document.createElement('div'); bubble.className = 'message-bubble'; bubble.textContent = text; content.append(bubble);
    if (!typing) { const time = document.createElement('time'); time.textContent = new Intl.DateTimeFormat(undefined, {hour: 'numeric', minute: '2-digit'}).format(new Date()); content.append(time); }
    row.append(avatar, content); log.append(row); log.scrollTop = log.scrollHeight; return row;
  }
  function clearPanel(title, urgent = false) {
    panel.replaceChildren(); panel.classList.toggle('is-urgent', urgent);
    const heading = document.createElement('h2'); heading.className = 'context-result-title'; heading.textContent = title; panel.append(heading);
  }
  function paragraph(text, parent = panel) { const p = document.createElement('p'); p.textContent = text; parent.append(p); }
  function link(label, href, className = 'btn btn-outline-primary btn-sm') {
    const localPath = href?.startsWith('/') && !href.startsWith('//');
    const webLink = href?.startsWith('https://') || href?.startsWith('http://');
    if (!href || (!localPath && !href.startsWith('tel:') && !webLink)) return;
    const a = document.createElement('a'); a.className = className; a.href = href; a.textContent = label;
    if (webLink) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
    panel.append(a);
  }
  function renderContext(data) {
    if (stopFlow) stopFlow.hidden = data.flow_active !== true;
    switch (data.response_type) {
      case 'emergency_alert': {
        clearPanel('Potential emergency warning', true);
        paragraph('Do not wait for more chatbot questions. Call emergency services now.');
        link('Call 112 now', 'tel:112', 'btn btn-emergency w-100');
        if (data.warning_signs?.length) paragraph(`Warning signs mentioned: ${data.warning_signs.join(', ').replaceAll('_', ' ')}`);
        link('Find Hospitals', '/hospitals/');
        if (data.first_aid) renderGuide(data.first_aid);
        break;
      }
      case 'first_aid_guide':
        clearPanel('First-Aid Guidance'); if (data.first_aid) renderGuide(data.first_aid); break;
      case 'symptom_followup':
        clearPanel('Symptom questions'); paragraph('One question at a time. You can stop these questions at any point.'); break;
      case 'symptom_summary':
        clearPanel('Reported symptom summary'); paragraph('These details are based on what you told the assistant. They are not a diagnosis or substitute for a clinician.'); break;
      case 'hospital_results':
        clearPanel('Hospital search results');
        (data.hospitals || []).forEach(renderHospital);
        (data.mapped_facilities || []).forEach(renderMappedFacility);
        (data.source_errors || []).forEach((sourceError) => paragraph(`${sourceError.source || 'A discovery source'} is temporarily unavailable.`));
        if (!data.hospitals?.length && !data.mapped_facilities?.length) paragraph('No matching records. Try the hospital finder with a city or coordinates.');
        if (data.mapped_facilities?.length) link('OpenStreetMap attribution', 'https://www.openstreetmap.org/copyright');
        link('Open Find Hospitals', '/hospitals/'); break;
      case 'doctor_results':
        clearPanel('Doctor directory'); (data.doctors || []).forEach(renderDoctor);
        (data.mapped_facilities || []).forEach(renderMappedFacility);
        (data.source_errors || []).forEach((sourceError) => paragraph(`${sourceError.source || 'A discovery source'} is temporarily unavailable.`));
        if (!data.doctors?.length) paragraph(data.mapped_facilities?.length ? 'No MediReach doctor profile matched; mapped healthcare facilities are listed separately.' : 'No directory profiles matched that specialty.');
        if (data.mapped_facilities?.length) link('OpenStreetMap attribution', 'https://www.openstreetmap.org/copyright');
        link('Browse doctors', '/doctors/'); break;
      case 'emergency_contact':
        clearPanel('Emergency contact'); paragraph('India emergency response number'); link('Call 112', 'tel:112', 'btn btn-emergency w-100'); break;
      case 'referral_action':
        clearPanel('Referral request'); paragraph('This saves a local demo request. It is not sent to or acknowledged by a hospital.'); link('Prepare referral request', '/referrals/new/'); break;
      case 'enquiry_action':
        clearPanel('General hospital enquiry'); paragraph('This saves a local demo enquiry. It is not delivered to or acknowledged by a hospital.'); link('Prepare general enquiry', '/enquiries/new/'); break;
      default:
        clearPanel('Conversation support'); paragraph('General information only. For urgent symptoms, call 112 or contact a qualified healthcare professional.');
        link('Find Hospitals', '/hospitals/'); link('First-Aid Centre', '/first-aid/');
    }
    if (data.fallback_notice) paragraph(data.fallback_notice);
    const emergencyLinksAlreadyRendered = data.response_type === 'emergency_alert'
      ? new Set(['tel:112', '/hospitals/'])
      : new Set();
    (data.actions || [])
      .filter((action) => !emergencyLinksAlreadyRendered.has(action.href))
      .forEach((action) => link(action.label, action.href));
  }
  function renderGuide(guide) {
    const card = document.createElement('section'); card.className = 'context-guide';
    const heading = document.createElement('h3'); heading.textContent = guide.title; card.append(heading);
    const list = document.createElement('ul');
    (guide.immediate_actions || []).slice(0, 4).forEach((text) => { const li = document.createElement('li'); li.textContent = text; list.append(li); });
    card.append(list); panel.append(card);
    if (guide.source_url) link(`Source: ${guide.source_name}`, guide.source_url, 'source-link');
    if (guide.slug) link('Read full guide', `/first-aid/${guide.slug}/`);
  }
  function renderHospital(hospital) {
    const card = document.createElement('article'); card.className = 'context-result-card';
    const title = document.createElement('h3'); title.textContent = hospital.name;
    card.append(title); paragraph(`Source: ${hospital.source || 'MediReach'}`, card); paragraph(`${hospital.address}, ${hospital.city}`, card);
    const status = document.createElement('span'); status.className = `status-chip trust-status ${hospital.provider_status || hospital.verification_status || 'unknown'}`; status.textContent = hospital.trust_label || hospital.verification_status; card.append(status);
    (hospital.services || []).slice(0, 3).forEach((service) => paragraph(`${service.name}: ${service.status_label || `Reported ${service.status}`}`, card));
    (hospital.sources || []).forEach((source) => paragraph(`Source: ${source.source_name}`, card));
    (hospital.contacts || []).forEach((contact) => paragraph(`${contact.type}: ${contact.value} (${contact.label})`, card));
    panel.append(card); link('Facility details', `/hospitals/${hospital.id}/`);
    if (hospital.phone) link(`Call facility (${hospital.phone_contact_label || 'contact status unknown'})`, `tel:${hospital.phone}`);
    if (hospital.website && /^https?:\/\//i.test(hospital.website)) link('Facility website', hospital.website);
    if (Number.isFinite(Number(hospital.latitude)) && Number.isFinite(Number(hospital.longitude))
      && hospital.latitude !== null && hospital.longitude !== null) {
      link('Directions', `https://www.openstreetmap.org/directions?to=${hospital.latitude},${hospital.longitude}`);
    }
  }
  function renderDoctor(doctor) {
    const card = document.createElement('article'); card.className = 'context-result-card';
    const title = document.createElement('h3'); title.textContent = doctor.name; card.append(title);
    paragraph(`Source: ${doctor.source || 'MediReach'}`, card);
    paragraph(`${(doctor.specialties || [doctor.specialty]).join(', ')}${(doctor.facilities || []).length ? ` | ${(doctor.facilities || []).map((facility) => facility.name).join(', ')}` : ''}`, card);
    const status = document.createElement('span'); status.className = `status-chip trust-status ${doctor.provider_status || doctor.verification_status || 'unknown'}`; status.textContent = doctor.trust_label || doctor.verification_status; card.append(status);
    panel.append(card);
    if (doctor.id !== undefined && doctor.id !== null) link('View doctor profile and local slots', `/doctors/${encodeURIComponent(doctor.id)}/`);
    if (doctor.contact_route) link('Hospital contact route', doctor.contact_route);
    (doctor.contacts || []).forEach((contact) => paragraph(`${contact.type}: ${contact.value} (${contact.label})`, card));
    (doctor.contact_information || []).forEach((contact) => {
      if (contact.type === 'phone' && contact.verification_status === 'verified') link(`Call doctor (${contact.label})`, `tel:${contact.value}`);
      else if (contact.type === 'website' && /^https?:\/\//i.test(contact.value || '')) link(`Doctor website (${contact.label})`, contact.value);
    });
    (doctor.facilities || []).forEach((facility) => {
      paragraph(`${facility.name}: ${facility.address || facility.city || 'Address not available'}`, card);
      if (facility.phone) link(`Call facility (${facility.phone_contact_label || 'contact status unknown'})`, `tel:${facility.phone}`);
      if (Number.isFinite(Number(facility.latitude)) && Number.isFinite(Number(facility.longitude)) && facility.latitude !== null && facility.longitude !== null) {
        link('Directions to facility', `https://www.openstreetmap.org/directions?to=${facility.latitude},${facility.longitude}`);
      }
    });
    (doctor.sources || []).forEach((source) => paragraph(`Source: ${source.source_name}`, card));
  }
  function renderMappedFacility(facility) {
    const card = document.createElement('article'); card.className = 'context-result-card mapped-result';
    const title = document.createElement('h3');
    title.textContent = facility.name || 'Name not available in OpenStreetMap tags';
    card.append(title);
    paragraph('Source: OpenStreetMap', card);
    if (facility.facility_category) paragraph(`Mapped category: ${facility.facility_category}`, card);
    if (facility.address) paragraph(Object.values(facility.address).join(', '), card);
    (facility.specialties || []).forEach((specialty) => paragraph(`OSM-tagged specialty: ${specialty}`, card));
    (facility.contact_information || []).forEach((contact) => {
      paragraph(`${contact.type}: ${contact.value} (${contact.label})`, card);
      if (contact.type === 'phone') link(`Call mapped number (${contact.label})`, `tel:${contact.value}`);
      if (contact.type === 'website' && /^https?:\/\//i.test(contact.value || '')) link('Mapped website (unverified)', contact.value);
    });
    const status = document.createElement('span'); status.className = 'status-chip trust-status mapped'; status.textContent = facility.trust_label; card.append(status);
    panel.append(card);
    link('View OpenStreetMap record', facility.source_url);
    if (Number.isFinite(Number(facility.latitude)) && Number.isFinite(Number(facility.longitude)) && facility.latitude !== null && facility.longitude !== null) {
      link('Directions', `https://www.openstreetmap.org/directions?to=${facility.latitude},${facility.longitude}`);
    }
  }
})();
