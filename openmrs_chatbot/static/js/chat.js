/* ============================================================
   OpenMRS Clinical Chatbot — Frontend Logic
   ============================================================ */

'use strict';

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  selectedPatient: null,
  isLoading: false,
};

// ── DOM refs ───────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const els = {
  patientSearch:          $('patientSearch'),
  clearSearch:            $('clearSearch'),
  btnListAll:             $('btnListAll'),
  searchResultsSection:   $('searchResultsSection'),
  searchResults:          $('searchResults'),
  resultCount:            $('resultCount'),
  selectedPatientSection: $('selectedPatientSection'),
  selectedPatientCard:    $('selectedPatientCard'),
  btnClearPatient:        $('btnClearPatient'),
  noPatientHint:          $('noPatientHint'),
  patientHeader:          $('patientHeader'),
  patientAvatar:          $('patientAvatar'),
  patientHeaderName:      $('patientHeaderName'),
  patientHeaderMeta:      $('patientHeaderMeta'),
  patientHeaderBadges:    $('patientHeaderBadges'),
  chatEmpty:              $('chatEmpty'),
  messages:               $('messages'),
  typingIndicator:        $('typingIndicator'),
  messageInput:           $('messageInput'),
  sendBtn:                $('sendBtn'),
  noPatientWarning:       $('noPatientWarning'),
  patientSelectedHint:    $('patientSelectedHint'),
};

// ── Intent display labels ──────────────────────────────────────────────────
const INTENT_LABELS = {
  MEDICATION_QUERY:               'Medication',
  MEDICATION_INFO_QUERY:          'Medication Info',
  MEDICATION_ADMINISTRATION_QUERY:'Administration',
  MEDICATION_SIDE_EFFECTS_QUERY:  'Side Effects',
  MEDICATION_EMERGENCY:           '⚠ Emergency',
  MEDICATION_COMPATIBILITY_QUERY: 'Drug Interaction',
  PAST_MEDICATIONS_QUERY:         'Past Medications',
  ALLERGY_QUERY:                  'Allergy Check',
  IMMUNIZATION_QUERY:             'Immunization',
  MILESTONE_QUERY:                'Milestones',
  VITALS_QUERY:                   'Vitals',
  PATIENT_RECORD_QUERY:           'Patient Record',
  GENERAL_MEDICAL_QUERY:          'General',
};

// ── Utilities ──────────────────────────────────────────────────────────────

function formatTime(isoStr) {
  try {
    const d = isoStr ? new Date(isoStr) : new Date();
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

function escapeHtml(str) {
  const map = { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#039;' };
  return String(str || '').replace(/[&<>"']/g, c => map[c]);
}

/** Auto-grow textarea height */
function autoGrow(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

/** Scroll messages to bottom */
function scrollToBottom() {
  const m = els.messages;
  m.scrollTop = m.scrollHeight;
}

// ── Patient Rendering ──────────────────────────────────────────────────────

function buildPatientListItem(p) {
  const div = document.createElement('div');
  div.className = 'patient-list-item';
  div.dataset.patientId = p.patient_identifier || p.patient_id;
  div.innerHTML = `
    <div class="patient-list-item__name">${escapeHtml(p.full_name)}</div>
    <div class="patient-list-item__meta">
      <span>${escapeHtml(p.patient_identifier || p.patient_id)}</span>
      <span>${escapeHtml(p.gender)}</span>
      <span>${escapeHtml(p.age)}</span>
    </div>
  `;
  div.addEventListener('click', () => selectPatient(p));
  return div;
}

function selectPatient(p) {
  state.selectedPatient = p;

  // Highlight in list
  document.querySelectorAll('.patient-list-item').forEach(el => {
    el.classList.toggle('active', el.dataset.patientId === String(p.patient_identifier || p.patient_id));
  });

  // Fill sidebar card
  const pid = p.patient_identifier || p.patient_id;
  let addressParts = [p.address1, p.city_village, p.state_province, p.postal_code].filter(Boolean);
  const deadBadge = p.dead
    ? `<span class="patient-card__status--deceased">Deceased${p.death_date ? ' – ' + p.death_date : ''}</span>`
    : '';

  els.selectedPatientCard.innerHTML = `
    <div class="patient-card__name">${escapeHtml(p.full_name)}</div>
    <span class="patient-card__id">${escapeHtml(String(pid))}</span>
    <div class="patient-card__row"><strong>Gender:</strong> ${escapeHtml(p.gender)}</div>
    <div class="patient-card__row"><strong>DOB:</strong> ${escapeHtml(p.birthdate)}</div>
    <div class="patient-card__row"><strong>Age:</strong> ${escapeHtml(p.age)}</div>
    ${addressParts.length ? `<div class="patient-card__row"><strong>Address:</strong> ${escapeHtml(addressParts.join(', '))}</div>` : ''}
    ${deadBadge}
  `;

  // Show card, hide hint
  els.selectedPatientSection.style.display = 'block';
  els.noPatientHint.style.display = 'none';

  // Fill chat header
  const initials = (p.full_name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  els.patientAvatar.textContent = initials;
  els.patientHeaderName.textContent = p.full_name;
  els.patientHeaderMeta.textContent = `ID: ${pid}  •  ${p.gender}  •  Age: ${p.age}`;

  // Header badges
  const badges = [];
  if (p.dead) badges.push(`<span class="badge" style="background:#fee2e2;color:#b91c1c">Deceased</span>`);
  els.patientHeaderBadges.innerHTML = badges.join('');

  els.patientHeader.style.display = 'flex';
  els.chatEmpty.style.display = 'flex';

  // Enable input
  updateInputState();
}

function clearPatientSelection() {
  state.selectedPatient = null;
  els.selectedPatientSection.style.display = 'none';
  els.patientHeader.style.display = 'none';
  els.noPatientHint.style.display = 'flex';
  document.querySelectorAll('.patient-list-item').forEach(el => el.classList.remove('active'));
  updateInputState();
}

// ── Patient Search ─────────────────────────────────────────────────────────

let searchDebounce = null;

function showResults(patients, emptyMsg) {
  els.searchResultsSection.style.display = 'block';
  els.searchResults.innerHTML = '';
  els.resultCount.textContent = patients.length;

  if (!patients.length) {
    els.searchResults.innerHTML = `<p style="font-size:12px;color:var(--color-text-subtle);padding:8px 4px">${escapeHtml(emptyMsg || 'No patients found.')}</p>`;
    return;
  }
  patients.forEach(p => els.searchResults.appendChild(buildPatientListItem(p)));
}

async function doSearch(query) {
  try {
    const url = query
      ? `/api/patients/search?q=${encodeURIComponent(query)}`
      : '/api/patients/list';
    const res = await fetch(url);
    const data = await res.json();
    if (data.error) {
      showResults([], `Error: ${data.error}`);
    } else {
      showResults(data.patients || [], 'No patients found.');
    }
  } catch (e) {
    showResults([], 'Network error. Please try again.');
  }
}

els.patientSearch.addEventListener('input', function() {
  const val = this.value.trim();
  els.clearSearch.style.display = val ? 'flex' : 'none';

  clearTimeout(searchDebounce);
  if (val.length >= 2) {
    searchDebounce = setTimeout(() => doSearch(val), 350);
  } else if (!val) {
    els.searchResultsSection.style.display = 'none';
  }
});

els.clearSearch.addEventListener('click', () => {
  els.patientSearch.value = '';
  els.clearSearch.style.display = 'none';
  els.searchResultsSection.style.display = 'none';
  els.patientSearch.focus();
});

els.btnListAll.addEventListener('click', () => doSearch(''));

els.btnClearPatient.addEventListener('click', clearPatientSelection);

// ── Input State ────────────────────────────────────────────────────────────

function updateInputState() {
  const hasPatient = !!state.selectedPatient;
  const hasText = els.messageInput.value.trim().length > 0;
  els.sendBtn.disabled = !hasPatient || !hasText || state.isLoading;
  els.noPatientWarning.style.display = hasPatient ? 'none' : 'inline';
  els.patientSelectedHint.style.display = hasPatient ? 'inline' : 'none';
  els.messageInput.disabled = !hasPatient || state.isLoading;
}

els.messageInput.addEventListener('input', function() {
  autoGrow(this);
  updateInputState();
});

els.messageInput.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!els.sendBtn.disabled) sendMessage();
  }
});

// ── Message Building ───────────────────────────────────────────────────────

function buildUserMessage(text) {
  const msg = document.createElement('div');
  msg.className = 'message message--user';
  msg.innerHTML = `
    <div class="message__bubble">${escapeHtml(text)}</div>
    <span class="message__time">${formatTime()}</span>
  `;
  return msg;
}

function buildBotMessage(data) {
  const msg = document.createElement('div');
  msg.className = 'message message--bot';

  const intent = data.intent || 'GENERAL_MEDICAL_QUERY';
  const label = INTENT_LABELS[intent] || intent;
  const isEmergency = data.emergency_flag || intent === 'MEDICATION_EMERGENCY';
  const isAllergy = intent === 'ALLERGY_QUERY';

  // Sources tags
  const sourceTags = (data.sources || [])
    .map(s => `<span class="source-tag">${escapeHtml(s)}</span>`)
    .join('');

  // Emergency alert prefix
  let specialPrefix = '';
  if (isEmergency) {
    specialPrefix = `
      <div class="emergency-alert">
        <div class="emergency-alert__icon">🚨</div>
        <div>
          <div class="emergency-alert__title">MEDICAL EMERGENCY — Seek Immediate Help</div>
          <div style="font-size:12px;color:#7f1d1d">
            Call emergency services or go to the nearest emergency room immediately.
          </div>
        </div>
      </div>`;
  } else if (isAllergy && /allerg|contraindic|warning|avoid|do not|cannot/i.test(data.response || '')) {
    specialPrefix = `
      <div class="allergy-warning">
        <span>⚠</span>
        <span><strong>Allergy Alert:</strong> Review allergy information carefully before administering any medication.</span>
      </div>`;
  }

  const bubbleClass = isEmergency ? 'message__bubble message__bubble--emergency' : 'message__bubble';

  // Response HTML (already converted from Markdown by server, or fallback to escaped)
  const responseHtml = data.response_html
    ? `<div class="response-body">${data.response_html}</div>`
    : `<div class="response-body">${escapeHtml(data.response || '')}</div>`;

  msg.innerHTML = `
    <div class="${bubbleClass}">
      <div class="message__header">
        <span class="intent-badge intent-${escapeHtml(intent)}">${escapeHtml(label)}</span>
        ${sourceTags}
      </div>
      ${specialPrefix}
      ${responseHtml}
    </div>
    <span class="message__time">${formatTime(data.timestamp)}</span>
  `;

  return msg;
}

function buildErrorMessage(errorText) {
  const msg = document.createElement('div');
  msg.className = 'message message--bot';
  msg.innerHTML = `
    <div class="message__error">
      <strong>Error:</strong> ${escapeHtml(errorText)}
    </div>
  `;
  return msg;
}

// ── Send Message ───────────────────────────────────────────────────────────

async function sendMessage() {
  const text = els.messageInput.value.trim();
  if (!text || !state.selectedPatient || state.isLoading) return;

  // Hide empty state on first message
  els.chatEmpty.style.display = 'none';

  // Add user bubble
  els.messages.appendChild(buildUserMessage(text));
  scrollToBottom();

  // Clear input
  els.messageInput.value = '';
  autoGrow(els.messageInput);

  // Set loading state
  state.isLoading = true;
  updateInputState();
  els.typingIndicator.style.display = 'flex';
  scrollToBottom();

  const patientId = state.selectedPatient.patient_identifier || state.selectedPatient.patient_id;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text, patient_id: String(patientId) }),
    });

    const data = await res.json();

    els.typingIndicator.style.display = 'none';

    if (!res.ok || data.error) {
      els.messages.appendChild(buildErrorMessage(data.error || `Server error (${res.status})`));
    } else {
      els.messages.appendChild(buildBotMessage(data));
    }
  } catch (e) {
    els.typingIndicator.style.display = 'none';
    els.messages.appendChild(buildErrorMessage('Network error. Please check your connection.'));
  } finally {
    state.isLoading = false;
    updateInputState();
    scrollToBottom();
    els.messageInput.focus();
  }
}

els.sendBtn.addEventListener('click', sendMessage);

// ── Example query chips ────────────────────────────────────────────────────

document.querySelectorAll('.example-query').forEach(chip => {
  chip.addEventListener('click', () => {
    if (!state.selectedPatient) return;
    els.messageInput.value = chip.dataset.query;
    autoGrow(els.messageInput);
    updateInputState();
    els.messageInput.focus();
  });
});

// ── Session expired handling ───────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  updateInputState();

  // Check for 401 and redirect to role selection
  const origFetch = window.fetch;
  window.fetch = async function(...args) {
    const res = await origFetch.apply(this, args);
    if (res.status === 401) {
      window.location.href = '/';
    }
    return res;
  };
});
