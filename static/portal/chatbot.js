(() => {
  const form = document.getElementById('chat-form');
  if (!form) return;
  const input = document.getElementById('chat-input');
  const log = document.getElementById('chat-log');
  const error = document.getElementById('chat-error');
  const send = form.querySelector('button[type="submit"]');
  const panel = document.getElementById('context-panel');

  document.querySelectorAll('[data-prompt]').forEach((button) => button.addEventListener('click', () => {
    input.value = button.dataset.prompt;
    input.focus();
  }));
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
      const response = await fetch(window.mediReachChat.sendUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name="csrfmiddlewaretoken"]').value},
        body: JSON.stringify({message, conversation_id: window.mediReachChat.conversationId}),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Unable to send your message. Please try again.');
      await new Promise((resolve) => window.setTimeout(resolve, 3000));
      typing.remove();
      appendMessage(data.reply, 'bot');
      renderContext(data);
    } catch (requestError) {
      typing.remove();
      userRow.remove();
      input.value = message;
      error.textContent = `${requestError.message} Your message is still in the composer.`;
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
    if (!href || (!href.startsWith('/') && !href.startsWith('tel:') && !href.startsWith('https://'))) return;
    const a = document.createElement('a'); a.className = className; a.href = href; a.textContent = label;
    if (href.startsWith('https://')) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
    panel.append(a);
  }
  function renderContext(data) {
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
      case 'hospital_results':
        clearPanel('Hospital search results');
        (data.hospitals || []).forEach(renderHospital);
        if (!data.hospitals?.length) paragraph('No matching records. Try the hospital finder with a city or coordinates.');
        link('Open Find Hospitals', '/hospitals/'); break;
      case 'doctor_results':
        clearPanel('Doctor directory'); (data.doctors || []).forEach(renderDoctor);
        if (!data.doctors?.length) paragraph('No directory profiles matched that specialty.');
        link('Browse doctors', '/doctors/'); break;
      case 'emergency_contact':
        clearPanel('Emergency contact'); paragraph('India emergency response number'); link('Call 112', 'tel:112', 'btn btn-emergency w-100'); break;
      case 'referral_action':
        clearPanel('Hospital enquiry'); paragraph('Review and submit an enquiry. This is not an admission request.'); link('Start an enquiry', '/referrals/new/'); break;
      default:
        clearPanel('Conversation support'); paragraph('General information only. For urgent symptoms, call 112 or contact a qualified healthcare professional.');
        link('Find Hospitals', '/hospitals/'); link('First-Aid Centre', '/first-aid/');
    }
    (data.actions || []).forEach((action) => link(action.label, action.href));
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
    card.append(title); paragraph(`${hospital.address}, ${hospital.city}`, card);
    const status = document.createElement('span'); status.className = 'status-chip'; status.textContent = hospital.is_demo ? 'Demo data' : hospital.verification_status; card.append(status);
    (hospital.services || []).slice(0, 3).forEach((service) => paragraph(`${service.name}: ${service.status}`, card));
    panel.append(card); link('Facility details', `/hospitals/${hospital.id}/`);
    if (hospital.phone) link('Call facility', `tel:${hospital.phone}`);
    if (hospital.latitude && hospital.longitude) link('Directions', `https://www.openstreetmap.org/directions?to=${hospital.latitude},${hospital.longitude}`);
  }
  function renderDoctor(doctor) {
    const card = document.createElement('article'); card.className = 'context-result-card';
    const title = document.createElement('h3'); title.textContent = doctor.name; card.append(title);
    paragraph(`${doctor.specialty}${doctor.hospital ? ` | ${doctor.hospital}` : ''}`, card);
    const status = document.createElement('span'); status.className = 'status-chip'; status.textContent = doctor.verification_status; card.append(status);
    panel.append(card); if (doctor.contact_route) link('Hospital contact route', doctor.contact_route);
  }
})();
