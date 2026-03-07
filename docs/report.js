/* Report Integrity Concern — form submission + stats display */

// ── Replace this with your deployed Google Apps Script web app URL ──
const APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbzvj1tVhYBlV2ycx-VJIxa4rJ5bUzKYnlqv8_Hy1-Bh2b-zZ_3-_I7AWvqqza8eFloR/exec';

const form = document.getElementById('report-form');
const submitBtn = document.getElementById('report-submit');
const statusEl = document.getElementById('report-status');
const statsLoading = document.getElementById('report-stats-loading');
const statsEmpty = document.getElementById('report-stats-empty');
const statsWrap = document.getElementById('report-stats-wrap');
const statsBody = document.getElementById('report-stats-body');

// ── Fetch client IP for rate limiting ──────────────────────────────
async function getClientIP() {
  try {
    const resp = await fetch('https://api.ipify.org?format=json');
    const data = await resp.json();
    return data.ip;
  } catch {
    return 'unknown';
  }
}

// ── Submit report ──────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
  e.preventDefault();

  if (document.getElementById('website').value) return;

  const data = {
    name: document.getElementById('reported-name').value.trim(),
    state: document.getElementById('reported-state').value,
    contest: document.getElementById('reported-contest').value.trim(),
    description: document.getElementById('reported-description').value.trim(),
  };

  if (!data.name || !data.state || !data.contest || !data.description) {
    showStatus('Please fill in the required fields.', 'error');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = 'Submitting…';
  showStatus('', '');

  try {
    data.ip = await getClientIP();
    const resp = await fetch(APPS_SCRIPT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify(data),
    });
    const result = await resp.json();
    if (result.error) {
      showStatus(result.error, 'error');
    } else {
      showStatus('Report submitted. Thank you.', 'success');
      form.reset();
      setTimeout(loadStats, 1500);
    }
  } catch (err) {
    showStatus('Failed to submit. Please try again later.', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit Report';
  }
});

function showStatus(msg, type) {
  statusEl.textContent = msg;
  statusEl.className = 'report-status' + (type ? ' report-status--' + type : '');
}

// ── Load aggregated stats ──────────────────────────────────────────
async function loadStats() {
  try {
    const resp = await fetch(APPS_SCRIPT_URL + '?action=stats');
    if (!resp.ok) throw new Error('Network error');
    const rows = await resp.json();

    statsLoading.hidden = true;

    if (!rows || rows.length === 0) {
      statsEmpty.hidden = false;
      statsWrap.hidden = true;
      return;
    }

    rows.sort((a, b) => b.count - a.count);

    statsBody.innerHTML = '';
    for (const row of rows) {
      const tr = document.createElement('tr');
      tr.innerHTML =
        '<td>' + esc(row.name) + '</td>' +
        '<td>' + esc(row.state || '—') + '</td>' +
        '<td>' + esc(row.contests) + '</td>' +
        '<td class="num">' + row.count + '</td>';
      statsBody.appendChild(tr);
    }
    statsEmpty.hidden = true;
    statsWrap.hidden = false;
  } catch (err) {
    statsLoading.textContent = 'Could not load reports.';
  }
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

if (APPS_SCRIPT_URL !== 'YOUR_APPS_SCRIPT_URL_HERE') {
  loadStats();
} else {
  statsLoading.textContent = 'Apps Script URL not configured yet. See setup instructions.';
}
