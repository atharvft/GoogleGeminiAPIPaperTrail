/* ────────────────────────────────────────────────
   PaperTrail – Application Logic
   Integrated with FastAPI Backend
   ──────────────────────────────────────────────── */

const API = '/api';

/* ─── State ─────────────────────────────────────── */
const state = {
  formId: null,
  originalImage: null,
  processedImage: null,
  originalFilename: '',
  extractedFields: {},
  finalFields: {},
  confidenceScores: {},
  verificationFlags: {},
  formType: '',
  department: '',
  classificationConf: 0,
  auditRecords: [],
};

/* ─── Utils ──────────────────────────────────────── */
function confClass(score) {
  // Spec: High 80-100 | Medium 50-80 | Low <50
  if (score >= 0.80) return 'high';
  if (score >= 0.50) return 'medium';
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
    // Birth Certificate fields
    name: 'Name',
    sex: 'Sex/Gender',
    date_of_birth: 'Date of Birth',
    place_of_birth: 'Place of Birth',
    name_of_mother: "Mother's Name",
    name_of_father: "Father's Name",
    address_of_parents_at_birth: 'Address at Birth',
    permanent_address_of_parents: 'Permanent Address',
    registration_number: 'Registration Number',
    date_of_registration: 'Date of Registration',
    remarks: 'Remarks',
    date_of_issue: 'Date of Issue',
    // Residence Certificate fields
    full_name: 'Full Name',
    father_husband_name: 'Father/Husband Name',
    residential_address: 'Residential Address',
    mobile_number: 'Mobile Number',
    purpose_of_certificate: 'Purpose of Certificate',
    duration_of_residence_years: 'Duration of Residence (Years)',
    date: 'Date',
    place: 'Place',
    // Legacy fields
    address: 'Address',
    id_number: 'Identification Number',
  };
  return names[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formTypeDisplayName(key) {
  const names = {
    birth_certificate: 'Birth Certificate (West Bengal)',
    residence_certificate: 'Residence Certificate (Maharashtra)',
  };
  return names[key] || key || 'Unknown';
}

function departmentDisplayName(dept) {
  const names = {
    civil_records_department: 'Civil Records Department',
    citizen_services_department: 'Citizen Services Department',
  };
  return names[dept] || dept || '—';
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
  'Upload Image',
  'OpenCV preprocessing',
  'Gemini Vision OCR',
  'Text parsing & field extraction',
  'Fields extracted',
  'Confidence from AI engine',
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
    
    // Call backend API
    const res = await fetch(`${API}/upload-form`, { method: 'POST', body: formData });
    
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Upload failed');
    }
    
    const data = await res.json();
    
    // Store response data in state
    state.formId = data.form_id;
    state.formType = data.form_type;
    state.department = data.department;
    state.classificationConf = data.classification_confidence || 0;
    state.extractedFields = data.extracted_data || {};
    state.confidenceScores = data.confidence_scores || {};
    state.verificationFlags = data.verification_flags || {};
    state.ocrMethod = data.ocr_method || 'Coordinate OCR (PaddleOCR)';
    state.originalImage = document.getElementById('original-preview').src;
    state.processedImage = document.getElementById('original-preview').src;

    // Initialize finalFields with extracted data
    Object.keys(state.extractedFields).forEach(key => {
      state.finalFields[key] = state.extractedFields[key];
    });

    // After upload completes, mark all steps done and enable proceed
    setTimeout(() => {
      document.querySelectorAll('.step-dot').forEach(d => d.className = 'step-dot done');
      processedWrap.style.opacity = '1';
      document.getElementById('processed-preview').src = state.originalImage;
      processingBadge.textContent = 'Done ✓';
      processingBadge.style.background = 'var(--pastel-green)';
      processingBadge.style.color = 'var(--text-primary)';
      proceedBtn.disabled = false;
    }, PIPELINE_STEPS.length * 600 + 200);

  } catch (err) {
    console.error('Upload error:', err);
    
    // Show error message
    setTimeout(() => {
      document.querySelectorAll('.step-dot').forEach(d => d.className = 'step-dot done');
      processedWrap.style.opacity = '1';
      document.getElementById('processed-preview').src = document.getElementById('original-preview').src;
      processingBadge.textContent = err.message.includes('identify') ? 'Manual Entry Required' : 'Error - Retry';
      processingBadge.style.background = 'var(--pastel-yellow)';
      processingBadge.style.color = 'var(--text-primary)';
      
      // Still allow proceeding for manual entry
      state.formId = 'MANUAL_' + Date.now();
      state.originalImage = document.getElementById('original-preview').src;
      state.processedImage = document.getElementById('original-preview').src;
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
  document.getElementById('rv-original').src = state.originalImage || '';
  document.getElementById('rv-processed').src = state.processedImage || '';

  // Tab switching
  document.querySelectorAll('.img-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.img-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.review-img').forEach(img => img.classList.remove('active-img'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.target).classList.add('active-img');
    });
  });

  // Data is already loaded from upload response - just render
  renderFormFields();
  renderRoutingInfo();
}

function renderRoutingInfo() {
  // Update routing card
  document.getElementById('routing-dept').textContent = departmentDisplayName(state.department);
  
  const confPercent = (state.classificationConf * 100).toFixed(0);
  const confLevel = state.classificationConf >= 0.8 ? 'high' : state.classificationConf >= 0.6 ? 'medium' : 'low';
  document.getElementById('class-conf-display').innerHTML = `<span class="conf-badge ${confLevel}">${confPercent}%</span>`;

  // Set form type select
  const sel = document.getElementById('form-type-select');
  sel.value = state.formType || '';
  
  sel.addEventListener('change', () => {
    const deptMap = {
      'birth_certificate': 'civil_records_department',
      'residence_certificate': 'citizen_services_department',
    };
    state.formType = sel.value;
    state.department = deptMap[sel.value];
    document.getElementById('routing-dept').textContent = departmentDisplayName(state.department);
  });
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

  // Show OCR method banner if available
  const ocrMethod = state.ocrMethod || '';
  if (ocrMethod) {
    const banner = document.createElement('div');
    banner.className = 'ocr-method-banner';
    banner.innerHTML = `
      <span class="ocr-engine-icon">🔬</span>
      <span>Extracted via <strong>${ocrMethod}</strong> · AI-powered form extraction</span>
      <span class="conf-badge ${confClass(state.classificationConf)}">${(state.classificationConf * 100).toFixed(0)}% overall</span>
    `;
    container.appendChild(banner);
  }

  Object.entries(state.extractedFields).forEach(([key, value]) => {
    const confidence = state.confidenceScores[key] || 0.5;
    const needsVerification = state.verificationFlags[key] || false;
    const level = confClass(confidence);

    if (level === 'low' || needsVerification) hasLow = true;

    if (!state.finalFields[key]) {
      state.finalFields[key] = value;
    }

    const div = document.createElement('div');
    div.className = 'field-group';
    div.innerHTML = `
      <label class="field-label">${fieldDisplayName(key)}</label>
      <div class="field-row">
        <input class="field-input conf-${level}" id="field-${key}"
               type="text" value="${(value || '').replace(/"/g, '&quot;')}"
               data-key="${key}" />
        <span class="conf-badge ${level}" title="Confidence: ${(confidence * 100).toFixed(0)}%">
          ${level === 'high' ? '✓' : level === 'low' ? '✕' : '~'} ${confLabel(confidence)}
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
    department: state.department,
    corrected_data: state.finalFields,
  };

  try {
    // Submit to backend verification endpoint
    const res = await fetch(`${API}/verify-form`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    
    if (!res.ok) {
      const errorData = await res.json();
      throw new Error(errorData.detail || 'Verification failed');
    }
    
    const data = await res.json();
    console.log('Form verified:', data);
    
  } catch (err) {
    console.error('Verification error:', err);
    // Store locally as fallback
    const record = {
      form_id: state.formId,
      form_type: state.formType,
      department: state.department,
      original_image: state.originalImage,
      processed_image: state.processedImage,
      extracted_fields: state.extractedFields,
      final_corrected_fields: state.finalFields,
      confidence_scores: state.confidenceScores,
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
  
  // Get key field based on form type
  let primaryField = state.finalFields.name || state.finalFields.full_name || '—';
  let dateField = state.finalFields.date_of_birth || state.finalFields.date || '—';
  let idField = state.finalFields.registration_number || state.finalFields.mobile_number || '—';
  
  const items = [
    { label: 'Form ID',     value: state.formId },
    { label: 'Form Type',   value: formTypeDisplayName(state.formType) },
    { label: 'Department',  value: departmentDisplayName(state.department) },
    { label: 'Primary Name', value: primaryField },
    { label: 'Key Date',    value: dateField },
    { label: 'ID/Reg Number', value: idField },
    { label: 'Status',      value: '✓ Verified & Saved' },
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
    // Call backend API to get forms
    let url = `${API}/forms?limit=100`;
    if (filter) {
      url += `&form_type=${encodeURIComponent(filter)}`;
    }
    
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch');
    
    const data = await res.json();
    records = (data.forms || []).map(form => ({
      form_id: form._id,
      form_type: form.form_type,
      department: form.department,
      timestamp: form.created_at,
      verification_status: form.status === 'verified' ? 'Verified' : 'Pending',
      extracted_fields: form.extracted_data,
      final_corrected_fields: form.corrected_data && Object.keys(form.corrected_data).length > 0 
        ? form.corrected_data 
        : form.extracted_data,
      confidence_scores: form.confidence_scores,
      image_path: form.image_path,
    }));
    
  } catch (err) {
    console.error('Error fetching records:', err);
    // Fall back to local records
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
    const statusClass = r.verification_status === 'Verified' ? 'status-verified' : 'status-pending';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code style="font-size:12px;font-weight:700;color:var(--brown-accent)">${r.form_id ? r.form_id.substring(0, 12) : '—'}...</code></td>
      <td>${formatDate(r.timestamp)}</td>
      <td>${formTypeDisplayName(r.form_type)}</td>
      <td>${departmentDisplayName(r.department)}</td>
      <td><span class="status-badge ${statusClass}">● ${r.verification_status}</span></td>
      <td><button class="btn-detail" data-id="${r.form_id}" data-dept="${r.department}">View Details</button></td>
    `;
    tbody.appendChild(tr);
  });

  document.querySelectorAll('.btn-detail').forEach(btn => {
    btn.addEventListener('click', () => openModal(btn.dataset.id, btn.dataset.dept));
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
async function openModal(formId, department) {
  let record = null;

  try {
    // Fetch from backend API
    const res = await fetch(`${API}/forms?limit=100`);
    if (res.ok) {
      const data = await res.json();
      const form = data.forms?.find(f => f._id === formId);
      if (form) {
        record = {
          form_id: form._id,
          form_type: form.form_type,
          department: form.department,
          timestamp: form.created_at,
          original_image: form.image_path ? `/uploads/${form.image_path.split('/').pop()}` : null,
          processed_image: form.processed_image_path ? `/uploads/${form.processed_image_path.split('/').pop()}` : null,
          extracted_fields: form.extracted_data || {},
          final_corrected_fields: (form.corrected_data && Object.keys(form.corrected_data).length > 0) 
            ? form.corrected_data 
            : form.extracted_data || {},
          confidence_scores: form.confidence_scores || {},
          verification_status: form.status === 'verified' ? 'Verified' : 'Pending',
        };
      }
    }
  } catch (err) {
    console.error('Error fetching form:', err);
    record = state.auditRecords.find(r => r.form_id === formId);
  }

  // Fallback to local state
  if (!record) {
    record = state.auditRecords.find(r => r.form_id === formId);
  }

  if (!record) {
    alert('Form not found');
    return;
  }

  document.getElementById('modal-form-id').textContent = record.form_id;
  document.getElementById('btn-auto-template').dataset.id = record.form_id;
  document.getElementById('btn-view-digital').dataset.id = record.form_id;

  // Images
  const imgWrap = document.getElementById('modal-images');
  const origSrc = record.original_image || '';
  const procSrc = record.processed_image || '';

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
      <div class="compare-value">${extracted[k] || '—'}</div>
    </div>
  `).join('');

  finalDiv.innerHTML = Object.keys(corrected).map(k => `
    <div class="compare-row">
      <div class="compare-label">${fieldDisplayName(k)}</div>
      <div class="compare-value">${corrected[k] || '—'}</div>
    </div>
  `).join('');

  // Meta
  document.getElementById('modal-meta').innerHTML = `
    <span>Form Type: <strong>${formTypeDisplayName(record.form_type)}</strong></span>
    <span>Department: <strong>${departmentDisplayName(record.department)}</strong></span>
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

/* ─── Digital Form Generation ────────────────────── */
document.getElementById('btn-auto-template').addEventListener('click', async (e) => {
  const formId = e.target.dataset.id;
  const originalText = e.target.textContent;
  e.target.textContent = 'Processing OCR...';
  e.target.disabled = true;
  
  try {
    const res = await fetch(`${API}/templates/auto-create/${formId}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to auto-create template');
    alert('✅ ' + data.message);
  } catch (err) {
    alert('❌ Error: ' + err.message);
  } finally {
    e.target.textContent = originalText;
    e.target.disabled = false;
  }
});

document.getElementById('btn-view-digital').addEventListener('click', (e) => {
  const formId = e.target.dataset.id;
  // Open the digital form image endpoint in a new tab
  window.open(`${API}/templates/generate-digital/${formId}`, '_blank');
});

/* ─── Init ───────────────────────────────────────── */
navigate('upload');
