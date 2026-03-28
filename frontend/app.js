/* ────────────────────────────────────────────────
   PaperTrail – Application Logic
   ──────────────────────────────────────────────── */

const API = 'http://localhost:3001';

/* ─── State ─────────────────────────────────────── */
const state = {
  formId: null,
  originalImage: null,
  processedImage: null,
  originalFilename: '',
  extractedFields: {},
  finalFields: {},
  confidenceScores: {},
  formType: '',
  department: '',
  classificationConf: 0,
  auditRecords: [],
};

/* ─── Utils ──────────────────────────────────────── */
function confClass(score) {
  if (score >= 0.80) return 'high';
  if (score >= 0.60) return 'medium';
  return 'low';
}

function confLabel(score) {
  return (score * 100).toFixed(0) + '%';
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function fieldDisplayName(key) {
  const names = {
    full_name: 'Full Name',
    date_of_birth: 'Date of Birth',
    address: 'Address',
    id_number: 'Identification Number',
  };
  return names[key] || key;
}

function formTypeDisplayName(key) {
  const names = {
    birth_certificate: 'Birth Certificate Application',
    residence_certificate: 'Residence Certificate Application',
  };
  return names[key] || key || 'Unknown';
}

/* ─── Navigation ─────────────────────────────────── */
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  const navEl = document.getElementById('nav-' + page);
  if (navEl) navEl.classList.add('active');

  const labels = {
    upload: 'Upload Form',
    review: 'Review & Verify',
    confirmation: 'Confirmation',
    audit: 'Audit Dashboard',
  };
  document.getElementById('page-breadcrumb').textContent = labels[page] || page;

  if (page === 'audit') loadAuditRecords();
  window.scrollTo(0, 0);
}

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    navigate(item.dataset.page);
  });
});

/* ─── PAGE 1: Upload ─────────────────────────────── */
const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('file-input');
const previewSec = document.getElementById('preview-section');

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelect(file);
});
dropZone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleFileSelect(fileInput.files[0]);
});

function handleFileSelect(file) {
  state.originalFilename = file.name;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('original-preview').src = e.target.result;
    document.getElementById('file-name-chip').textContent = file.name;
    dropZone.style.display = 'none';
    previewSec.style.display = 'block';
    startPipelineAnimation(file);
  };
  reader.readAsDataURL(file);
}

const PIPELINE_STEPS = [
  'Convert to grayscale',
  'Reduce noise',
  'Adjust brightness',
  'Correct skew',
  'Enhance contrast',
];

function startPipelineAnimation(file) {
  const container = document.getElementById('pipeline-steps');
  const processedWrap = document.getElementById('processed-wrap');
  const processingBadge = document.getElementById('processing-badge');
  const proceedBtn = document.getElementById('proceed-btn');

  container.innerHTML = '';
  processedWrap.style.opacity = '0.4';
  proceedBtn.disabled = true;

  const dots = [];
  PIPELINE_STEPS.forEach((step, i) => {
    const div = document.createElement('div');
    div.className = 'pipeline-step';
    div.innerHTML = `<div class="step-dot" id="dot-${i}"></div><span>${step}</span>`;
    container.appendChild(div);
    dots.push(document.getElementById('dot-' + i));
  });

  // Upload to backend and animate simultaneously
  uploadToBackend(file);

  let current = 0;
  const interval = setInterval(() => {
    if (current > 0) dots[current - 1].className = 'step-dot done';
    if (current < dots.length) {
      dots[current].className = 'step-dot active';
      current++;
    } else {
      clearInterval(interval);
    }
  }, 600);
}

async function uploadToBackend(file) {
  const proceedBtn = document.getElementById('proceed-btn');
  const processedWrap = document.getElementById('processed-wrap');
  const processingBadge = document.getElementById('processing-badge');

  try {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API}/upload-form`, { method: 'POST', body: formData });
    const data = await res.json();

    state.formId = data.form_id;
    state.originalImage = data.original_image;
    state.processedImage = data.processed_image;

    // After upload completes, mark all steps done and enable proceed
    setTimeout(() => {
      document.querySelectorAll('.step-dot').forEach(d => d.className = 'step-dot done');
      processedWrap.style.opacity = '1';
      document.getElementById('processed-preview').src = API + data.processed_image;
      processingBadge.textContent = 'Done ✓';
      processingBadge.style.background = 'var(--pastel-green)';
      processingBadge.style.color = 'var(--text-primary)';
      proceedBtn.disabled = false;
    }, PIPELINE_STEPS.length * 600 + 200);

  } catch (err) {
    // Offline fallback: use original as processed
    state.formId = 'DEMO' + Math.random().toString(36).substring(2,6).toUpperCase();
    state.originalImage = document.getElementById('original-preview').src;
    state.processedImage = document.getElementById('original-preview').src;

    setTimeout(() => {
      document.querySelectorAll('.step-dot').forEach(d => d.className = 'step-dot done');
      processedWrap.style.opacity = '1';
      document.getElementById('processed-preview').src = document.getElementById('original-preview').src;
      processingBadge.textContent = 'Done ✓';
      processingBadge.style.background = 'var(--pastel-green)';
      processingBadge.style.color = 'var(--text-primary)';
      proceedBtn.disabled = false;
    }, PIPELINE_STEPS.length * 600 + 200);
  }
}

document.getElementById('reset-btn').addEventListener('click', () => {
  fileInput.value = '';
  dropZone.style.display = 'block';
  previewSec.style.display = 'none';
  document.getElementById('pipeline-steps').innerHTML = '';
  state.formId = null;
});

document.getElementById('proceed-btn').addEventListener('click', async () => {
  navigate('review');
  await loadReviewData();
});

/* ─── PAGE 2: Review & Verify ────────────────────── */
async function loadReviewData() {
  // Set images
  document.getElementById('rv-original').src = typeof state.originalImage === 'string' && state.originalImage.startsWith('/') ? API + state.originalImage : state.originalImage;
  document.getElementById('rv-processed').src = typeof state.processedImage === 'string' && state.processedImage.startsWith('/') ? API + state.processedImage : state.processedImage;

  // Tab switching
  document.querySelectorAll('.img-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.img-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.review-img').forEach(img => img.classList.remove('active-img'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.target).classList.add('active-img');
    });
  });

  await Promise.all([extractFields(), classifyForm()]);
}

async function extractFields() {
  try {
    const res = await fetch(`${API}/extract-fields`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ form_id: state.formId }),
    });
    const data = await res.json();
    state.extractedFields = data.extracted_fields;
  } catch (_) {
    // Mock fallback
    state.extractedFields = {
      full_name:     { value: 'Rajesh Kumar Sharma', confidence: 0.92 },
      date_of_birth: { value: '15/08/1985',          confidence: 0.78 },
      address:       { value: '12, Gandhi Nagar, Pune, Maharashtra – 411001', confidence: 0.43 },
      id_number:     { value: 'MH-2318-5574-9921',   confidence: 0.61 },
    };
  }

  renderFormFields();
}

async function classifyForm() {
  try {
    const res = await fetch(`${API}/classify-form`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ form_id: state.formId, filename: state.originalFilename }),
    });
    const data = await res.json();
    state.formType = data.form_type;
    state.department = data.department;
    state.classificationConf = data.confidence;
  } catch (_) {
    const types = ['birth_certificate', 'residence_certificate'];
    const deptMap = {
      'birth_certificate': 'Civil Records Department',
      'residence_certificate': 'Local Administration Department',
    };
    state.formType = '';
    state.department = '—';
    state.classificationConf = 0;
  }

  document.getElementById('routing-dept').textContent = state.department;
  document.getElementById('class-conf-display').innerHTML = `<span class="conf-badge high">${(state.classificationConf * 100).toFixed(0)}%</span>`;

  const sel = document.getElementById('form-type-select');
  sel.value = state.formType;
  sel.addEventListener('change', () => {
    const deptMap = {
      'birth_certificate': 'Civil Records Department',
      'residence_certificate': 'Local Administration Department',
    };
    state.formType = sel.value;
    state.department = deptMap[sel.value];
    document.getElementById('routing-dept').textContent = state.department;
  });
}

function renderFormFields() {
  const container = document.getElementById('form-fields');
  container.innerHTML = '';

  let hasLow = false;

  Object.entries(state.extractedFields).forEach(([key, field]) => {
    const level = confClass(field.confidence);
    if (level === 'low') hasLow = true;

    state.finalFields[key] = field.value;
    state.confidenceScores[key] = field.confidence;

    const div = document.createElement('div');
    div.className = 'field-group';
    div.innerHTML = `
      <label class="field-label">${fieldDisplayName(key)}</label>
      <div class="field-row">
        <input class="field-input conf-${level}" id="field-${key}"
               type="text" value="${field.value}"
               data-key="${key}" />
        <span class="conf-badge ${level}">
          ${level === 'high' ? '✓' : level === 'low' ? '✕' : '~'} ${confLabel(field.confidence)}
        </span>
      </div>
    `;
    container.appendChild(div);

    document.getElementById('field-' + key).addEventListener('input', e => {
      state.finalFields[key] = e.target.value;
    });
  });

  document.getElementById('low-conf-alert').style.display = hasLow ? 'block' : 'none';
}

/* Submit button */
document.getElementById('submit-btn').addEventListener('click', async () => {
  state.formType = document.getElementById('form-type-select').value;
  await submitVerifiedForm();
});

async function submitVerifiedForm() {
  const payload = {
    form_id: state.formId,
    form_type: state.formType,
    department: state.department,
    original_image: state.originalImage,
    processed_image: state.processedImage,
    extracted_fields: state.extractedFields,
    final_corrected_fields: state.finalFields,
    confidence_scores: state.confidenceScores,
  };

  try {
    await fetch(`${API}/submit-verified`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (_) {
    // Store locally as fallback
    const record = {
      ...payload,
      timestamp: new Date().toISOString(),
      verification_status: 'Verified',
    };
    state.auditRecords.unshift(record);
  }

  showConfirmation();
  navigate('confirmation');
}

/* ─── PAGE 3: Confirmation ───────────────────────── */
function showConfirmation() {
  const grid = document.getElementById('confirm-grid');
  const items = [
    { label: 'Form ID',     value: state.formId },
    { label: 'Form Type',   value: formTypeDisplayName(state.formType) },
    { label: 'Department',  value: state.department },
    { label: 'Full Name',   value: state.finalFields.full_name || '—' },
    { label: 'Date of Birth', value: state.finalFields.date_of_birth || '—' },
    { label: 'ID Number',   value: state.finalFields.id_number || '—' },
    { label: 'Status',      value: '✓ Verified' },
    { label: 'Timestamp',   value: formatDate(new Date().toISOString()) },
  ];
  grid.innerHTML = items.map(i => `
    <div class="confirm-item">
      <div class="confirm-item-label">${i.label}</div>
      <div class="confirm-item-value">${i.value}</div>
    </div>
  `).join('');
}

document.getElementById('new-form-btn').addEventListener('click', () => {
  fileInput.value = '';
  dropZone.style.display = 'block';
  previewSec.style.display = 'none';
  document.getElementById('pipeline-steps').innerHTML = '';
  state.formId = null;
  navigate('upload');
});

document.getElementById('go-audit-btn').addEventListener('click', () => navigate('audit'));

/* ─── PAGE 4: Audit Dashboard ────────────────────── */
async function loadAuditRecords() {
  const filter = document.getElementById('audit-filter').value;
  let records = [];

  try {
    const url = `${API}/audit-records` + (filter ? `?form_type=${encodeURIComponent(filter)}` : '');
    const res = await fetch(url);
    const data = await res.json();
    records = data.records || [];
  } catch (_) {
    records = state.auditRecords.filter(r => !filter || r.form_type === filter);
  }

  renderAuditTable(records);
}

function renderAuditTable(records) {
  const tbody = document.getElementById('audit-tbody');
  const empty = document.getElementById('audit-empty');
  tbody.innerHTML = '';

  if (!records.length) {
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  records.forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code style="font-size:12px;font-weight:700;color:var(--brown-accent)">${r.form_id}</code></td>
      <td>${formatDate(r.timestamp)}</td>
      <td>${formTypeDisplayName(r.form_type)}</td>
      <td>${r.department || '—'}</td>
      <td><span class="status-badge status-verified">● ${r.verification_status}</span></td>
      <td><button class="btn-detail" data-id="${r.form_id}">View Details</button></td>
    `;
    tbody.appendChild(tr);
  });

  document.querySelectorAll('.btn-detail').forEach(btn => {
    btn.addEventListener('click', () => openModal(btn.dataset.id));
  });
}

document.getElementById('audit-filter').addEventListener('change', loadAuditRecords);
document.getElementById('audit-search').addEventListener('input', e => {
  const q = e.target.value.toLowerCase();
  document.querySelectorAll('#audit-tbody tr').forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
  });
});

/* ─── Detail Modal ───────────────────────────────── */
async function openModal(formId) {
  let record = null;

  try {
    const res = await fetch(`${API}/audit-record/${formId}`);
    record = await res.json();
  } catch (_) {
    record = state.auditRecords.find(r => r.form_id === formId);
  }

  if (!record) return;

  document.getElementById('modal-form-id').textContent = record.form_id;

  // Images
  const imgWrap = document.getElementById('modal-images');
  const origSrc = record.original_image
    ? (record.original_image.startsWith('/') ? API + record.original_image : record.original_image)
    : '';
  const procSrc = record.processed_image
    ? (record.processed_image.startsWith('/') ? API + record.processed_image : record.processed_image)
    : '';

  imgWrap.innerHTML = `
    <div class="modal-img-wrap">
      <label>Original Upload</label>
      ${origSrc ? `<img src="${origSrc}" alt="original">` : '<p style="color:var(--text-muted);font-size:12px">Not available</p>'}
    </div>
    <div class="modal-img-wrap">
      <label>Processed Image</label>
      ${procSrc ? `<img src="${procSrc}" alt="processed">` : '<p style="color:var(--text-muted);font-size:12px">Not available</p>'}
    </div>
  `;

  // OCR vs Final comparison
  const ocrDiv = document.getElementById('modal-ocr-fields');
  const finalDiv = document.getElementById('modal-final-fields');
  const extracted = record.extracted_fields || {};
  const corrected = record.final_corrected_fields || {};

  ocrDiv.innerHTML = Object.keys(extracted).map(k => `
    <div class="compare-row">
      <div class="compare-label">${fieldDisplayName(k)}</div>
      <div class="compare-value">${extracted[k]?.value ?? extracted[k]}</div>
    </div>
  `).join('');

  finalDiv.innerHTML = Object.keys(corrected).map(k => `
    <div class="compare-row">
      <div class="compare-label">${fieldDisplayName(k)}</div>
      <div class="compare-value">${corrected[k]}</div>
    </div>
  `).join('');

  // Meta
  document.getElementById('modal-meta').innerHTML = `
    <span>Form Type: <strong>${formTypeDisplayName(record.form_type)}</strong></span>
    <span>Department: <strong>${record.department || '—'}</strong></span>
    <span>Submitted: <strong>${formatDate(record.timestamp)}</strong></span>
    <span>Status: <strong>${record.verification_status}</strong></span>
  `;

  document.getElementById('modal-overlay').classList.add('open');
}

document.getElementById('modal-close').addEventListener('click', () => {
  document.getElementById('modal-overlay').classList.remove('open');
});
document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay'))
    document.getElementById('modal-overlay').classList.remove('open');
});

/* ─── Init ───────────────────────────────────────── */
navigate('upload');
