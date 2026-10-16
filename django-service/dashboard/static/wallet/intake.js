'use strict';
document.addEventListener('DOMContentLoaded', () => {
  const token = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  async function call(url, options = {}) {
    const response = await fetch(url, {credentials: 'same-origin', ...options,
      headers: {'Accept': 'application/json', 'X-CSRFToken': token(), ...options.headers}});
    if (response.redirected) throw new Error('Your session ended. Sign in again.');
    const body = await response.json();
    if (!response.ok) throw new Error(body.error || 'The local request failed. Retry shortly.');
    return body;
  }
  const intake = document.getElementById('digilocker-intake');
  if (intake) {
    const status = document.getElementById('intake-connection');
    const stop = document.getElementById('intake-stop');
    let session = null;
    document.getElementById('manual-import')?.addEventListener('click', () => document.getElementById('file').focus());
    document.getElementById('intake-arm').addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.currentTarget, button = form.querySelector('button');
      button.disabled = true;
      try {
        const response = await fetch(form.action, {method: 'POST', credentials: 'same-origin', body: new FormData(form)});
        if (!response.ok || response.redirected) {
          const body = await response.json();
          throw new Error(body.error || 'Pairing failed. Sign in and check the folder.');
        }
        const blob = await response.blob();
        const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'foliolet-intake.json';
        link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
        status.textContent = 'Pairing file downloaded. Start the local companion, then download to your chosen folder. Watching expires after ten minutes.';
        await refresh();
      } catch (e) { status.textContent = e.message + ' Manual upload remains available.'; }
      finally { button.disabled = false; }
    });
    stop.addEventListener('click', async () => {
      if (!session) return;
      try {
        await call('/intake/sessions/' + encodeURIComponent(session.id) + '/stop/', {method: 'POST'});
        status.textContent = 'Watching stopped. New uploads using this pairing are denied.';
        stop.disabled = true; session = null;
      } catch (e) { status.textContent = e.message; }
    });
    async function refresh() {
      try {
        const body = await call(intake.dataset.sessions);
        session = body.sessions.find(s => s.active) || null;
        stop.disabled = !session;
        if (session) {
          status.textContent = (session.connected ? 'Watcher connected. ' : 'Local watcher not connected. ')
            + session.folder + ' · ends ' + new Date(session.expiresAt).toLocaleTimeString()
            + ' · ' + session.imported + ' files received.';
        } else status.textContent = 'Local watcher not connected. Enable a session to receive new files, or upload normally.';
        const received = document.getElementById('intake-received'); received.replaceChildren();
        for (const s of body.sessions) for (const doc of s.documents || []) {
          if (!/^0x[0-9a-f]{64}$/.test(doc.id)) continue;
          const item = document.createElement('li'), link = document.createElement('a');
          link.href = '/wallet/' + doc.id + '/'; link.textContent = 'File received · review suggested facts';
          item.appendChild(link); received.appendChild(item);
        }
      } catch (e) { status.textContent = e.message + ' Manual upload remains available.'; }
    }
    refresh(); setInterval(refresh, 5000);
  }

  const analysis = document.getElementById('intake-analysis');
  if (!analysis) return;
  const rows = document.getElementById('fact-rows'), stage = document.getElementById('intake-stage');
  let dirty = false, applied = false, baseline = [], timer;
  const preview = document.createElement('p'); preview.className = 'help'; preview.setAttribute('role', 'status');
  document.getElementById('claim-form')?.prepend(preview);
  const pathFor = label => {
    const slug = label.normalize('NFD').replace(/[^\x00-\x7F]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    return ({math: 'education.math', mathematics: 'education.math', cgpa: 'education.cgpa', name: 'person.name',
      full_name: 'person.name', institution: 'education.institution', course: 'education.course',
      date_of_birth: 'person.birth_date', purchase_date: 'purchase.date', product_identifier: 'purchase.product_id'})[slug] || 'extracted.' + slug.slice(0, 60);
  };
  function canonical(field) {
    let value = String(field.value).trim().normalize('NFC');
    if (field.type === 'decimal' && /^-?\d+(\.\d+)?$/.test(value)) {
      let negative = value.startsWith('-'); value = value.replace(/^-/, '');
      let [whole, frac = ''] = value.split('.'); whole = whole.replace(/^0+(?=\d)/, ''); frac = frac.replace(/0+$/, '');
      value = (negative && (whole !== '0' || frac) ? '-' : '') + whole + (frac ? '.' + frac : '');
    }
    if (field.type === 'boolean') value = value.toLowerCase();
    return [field.path.trim() || pathFor(field.label), field.label.trim().normalize('NFC'), field.type, value];
  }
  const semantic = fields => JSON.stringify(fields.map(canonical).sort((a,b) => a[0].localeCompare(b[0])));
  function changed() {
    if (!rows || !baseline.length) { preview.textContent = 'Manual facts / not compared.'; return; }
    const actual = [...rows.children].map(row => Object.fromEntries(['path','label','type','value'].map(key => [key, row.querySelector('[name=claim_' + key + ']').value])))
      .filter(f => f.path.trim() || f.value.trim());
    preview.textContent = semantic(actual) === semantic(baseline)
      ? 'Preview: Source-suggested facts unchanged. Confirmation checks this again on the server.'
      : 'Preview: facts edited since extraction. The original source proposal remains saved for comparison.';
  }
  rows?.addEventListener('input', () => { dirty = true; changed(); });
  rows?.addEventListener('change', () => { dirty = true; changed(); });
  rows?.addEventListener('click', event => { if (event.target.closest('.remove-fact')) { dirty = true; setTimeout(changed, 0); } });
  document.getElementById('add-fact')?.addEventListener('click', () => { dirty = true; setTimeout(changed, 0); });
  function showFields(fields) {
    baseline = fields;
    if (!rows || !fields.length || dirty || applied || analysis.dataset.editable !== 'yes') { changed(); return; }
    const template = rows.firstElementChild.cloneNode(true); rows.replaceChildren();
    for (const field of fields) {
      const row = template.cloneNode(true); row.querySelector('.scan-note')?.remove();
      for (const key of ['path','label','type','value']) row.querySelector('[name=claim_' + key + ']').value = field[key];
      const note = document.createElement('p'); note.className = 'help scan-note';
      note.textContent = 'Page ' + field.citation.page + ' · ' + field.citation.provenance + '. ';
      const evidence = document.createElement('details'), summary = document.createElement('summary'), quote = document.createElement('pre');
      summary.textContent = 'Show matching source text'; quote.textContent = field.evidence;
      quote.style.whiteSpace = 'pre-wrap'; quote.style.overflowWrap = 'anywhere';
      evidence.append(summary, quote);
      if (field.citation.provenance.includes('OCR')) note.append('OCR may misread characters; check the original. ');
      const source = document.createElement('a');
      const q = new URLSearchParams({documentId: field.citation.documentId, hash: field.citation.sourceHash, page: String(field.citation.page)});
      source.href = analysis.dataset.pdf === 'yes' ? '/ask-foli/api/page/?' + q
        : '/wallet/' + encodeURIComponent(field.citation.documentId.slice(7)) + '/file/';
      source.target = '_blank'; source.rel = 'noopener noreferrer'; source.textContent = analysis.dataset.pdf === 'yes' ? 'View original page' : 'View original file';
      if (field.citation.documentId.startsWith('wallet:')) note.append(source);
      row.append(note, evidence); rows.appendChild(row);
    }
    applied = true; changed();
  }
  function showLabels(body) {
    const labels = document.getElementById('intake-labels'); labels.replaceChildren();
    const names = [body.indicator === 'POSSIBLE_DIGILOCKER_FORMAT' ? 'Possible DigiLocker document (unverified)'
      : body.indicator === 'NO_DIGILOCKER_INDICATOR' ? 'No DigiLocker indicator found' : 'DigiLocker indicator check inconclusive'];
    if (body.method === 'WATCHER_ASSISTED') names.push('Imported with Foliolet');
    names.push(body.lineage === 'SUGGESTIONS_UNMODIFIED' ? 'Source-suggested facts unchanged'
      : body.lineage === 'SUGGESTIONS_MODIFIED' ? 'Facts edited since extraction' : 'Manual facts / not compared', 'Issuer not verified');
    for (const text of names) { const tag = document.createElement('span'); tag.className = 'mark quiet'; tag.textContent = text; labels.appendChild(tag); }
  }
  async function poll() {
    try {
      const body = await call(analysis.dataset.url); stage.textContent = body.stage || 'Original saved. Enter facts manually or read locally.';
      showLabels(body); showFields(body.fields || []);
      const manifest = body.report?.manifest, indicators = body.report?.indicators;
      document.getElementById('intake-coverage').textContent = manifest
        ? manifest.readablePages + '/' + manifest.totalPages + ' pages readable · ' + manifest.ocrPages + ' OCR pages · '
          + (indicators?.inspectedPages || 0) + '/' + (indicators?.totalPages || 0) + ' pages inspected for indicators.' : '';
      const warnings = [...(manifest?.warnings || []), ...(indicators?.warnings || []), ...(body.report?.suggestionWarnings || []),
        ...(manifest?.pages || []).flatMap(p => p.warnings.map(w => 'Page ' + p.number + ': ' + w)),
        ...(indicators?.pages || []).flatMap(p => p.warnings.map(w => 'Page ' + p.page + ': ' + w))];
      const box = document.getElementById('intake-warnings'); box.replaceChildren();
      const diagnostics = body.report?.suggestionDiagnostics || {};
      const reasons = {
        LOW_WORD_CONFIDENCE: 'Uncertain words or digits; check the original',
        DUPLICATE_SCOPE: 'Repeated labels at different locations; choose the intended one manually',
        MISSING_OR_MISMATCHED_HEADER: 'Several columns without a matching header',
        AMBIGUOUS_VALUE_HEADER: 'More than one possible value column',
        COLUMN_ALIGNMENT_MISMATCH: 'A row does not align with its header',
        INVALID_NUMERIC_LITERAL: 'A score is not a plain readable number; no repair was guessed',
        MIXED_LAYER_CONTRADICTION: 'Embedded text and the visible-page transcription disagree',
        MIXED_TABLES_REQUIRE_REVIEW: 'Mixed text/image table association needs manual review',
        PAGE_NOT_READABLE: 'Page reading is incomplete or uncertain',
        LITERAL_GEOMETRY_MISMATCH: 'Text cannot be safely paired on one visual row',
        NO_WORD_GEOMETRY: 'Position evidence is unavailable',
        INVALID_SOURCE_GEOMETRY: 'Position evidence failed its integrity checks',
        INVALID_LITERAL_OR_TYPE: 'Invalid value or date',
        CGPA_RANGE: 'CGPA is outside the supported 0–10 range',
        UNSUPPORTED_LABEL: 'Text is not a supported fact label',
        OVERLAPPING_CELLS: 'Overlapping text needs manual review',
        TIME_BUDGET: 'Source matching reached its time limit',
        ROW_BUDGET: 'Source matching reached its row limit',
        WORD_BUDGET: 'The page exceeded the word limit',
        FIELD_BUDGET: 'Only the first 40 unambiguous proposals are shown',
        EVIDENCE_SPAN_LIMIT: 'The supporting passage is too large for one safe proposal'
      };
      const detail = document.createElement('details'), title = document.createElement('summary');
      title.textContent = 'Why some facts were not suggested'; detail.appendChild(title);
      let reasonCount = 0;
      for (const [key, description] of Object.entries(reasons)) if (Number.isSafeInteger(diagnostics[key]) && diagnostics[key] > 0) {
        const p = document.createElement('p'); p.textContent = description + ' · ' + diagnostics[key]; detail.appendChild(p); reasonCount++;
      }
      if (reasonCount) box.appendChild(detail);
      for (const warning of [...new Set(warnings)].slice(0, 30)) { const p = document.createElement('p'); p.textContent = warning; box.appendChild(p); }
      if (['QUEUED','RUNNING'].includes(body.state)) timer = setTimeout(poll, 2500);
    } catch (e) { stage.textContent = e.message + ' The original is saved; manual fact entry remains available.'; }
  }
  document.getElementById('retry-intake')?.addEventListener('click', async event => {
    event.currentTarget.disabled = true; clearTimeout(timer);
    try { await call(analysis.dataset.retry, {method: 'POST'}); await poll(); }
    catch (e) { stage.textContent = e.message; }
    finally { event.currentTarget.disabled = false; }
  });
  changed(); poll();
});
