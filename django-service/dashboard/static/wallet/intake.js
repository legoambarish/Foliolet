'use strict';
document.addEventListener('DOMContentLoaded', () => {
  const token = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  async function call(url, options = {}) {
    const response = await fetch(url, {credentials: 'same-origin', cache: 'no-store', ...options,
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
    const list = document.getElementById('intake-files'), count = document.getElementById('intake-file-count');
    const empty = document.getElementById('intake-files-empty'), feedback = document.getElementById('intake-file-feedback');
    let session = null, refreshing = false, generation = 0, importing = false, importError = false;
    const sizeLabel = size => size < 1024 ? size + ' B' : size < 1048576 ? (size / 1024).toFixed(1) + ' KB' : (size / 1048576).toFixed(1) + ' MB';
    function renderFiles(files) {
      count.textContent = files.length + (files.length === 1 ? ' file' : ' files');
      empty.hidden = files.length > 0;
      const existing = new Map([...list.children].map(row => [row.dataset.path, row]));
      files.sort((a, b) => b.modifiedAt - a.modifiedAt || a.relativePath.localeCompare(b.relativePath));
      files.forEach((file, index) => {
        let row = existing.get(file.relativePath);
        if (!row) {
          row = document.createElement('li'); row.className = 'tracked-file'; row.dataset.path = file.relativePath;
          const button = document.createElement('button'); button.type = 'button'; button.className = 'tracked-file-button';
          const kind = document.createElement('span'); kind.className = 'tracked-file-kind'; kind.setAttribute('aria-hidden', 'true');
          const text = document.createElement('span'); text.className = 'tracked-file-text';
          const name = document.createElement('strong'); name.className = 'tracked-file-name';
          const meta = document.createElement('span'); meta.className = 'tracked-file-meta';
          const action = document.createElement('span'); action.className = 'tracked-file-action'; action.textContent = 'Import & review →';
          text.append(name, meta); button.append(kind, text, action); row.append(button);
        }
        existing.delete(file.relativePath);
        const button = row.querySelector('button'); button.dataset.selection = file.selection;
        button.setAttribute('aria-label', 'Import ' + file.relativePath); button.disabled = importing;
        row.querySelector('.tracked-file-kind').textContent = file.name.split('.').pop().toUpperCase();
        row.querySelector('.tracked-file-name').textContent = file.name;
        const time = new Date(file.modifiedAt).toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'});
        row.querySelector('.tracked-file-meta').textContent = sizeLabel(file.size) + ' · ' + time
          + (file.relativePath !== file.name ? ' · ' + file.relativePath : '');
        row.classList.toggle('tracked-file-newest', index === 0);
        if (list.children[index] !== row) list.insertBefore(row, list.children[index] || null);
      });
      for (const row of existing.values()) row.remove();
    }
    list.addEventListener('click', async event => {
      const button = event.target.closest('button[data-selection]');
      if (!button || importing) return;
      importError = false;
      importing = true;
      for (const control of list.querySelectorAll('button')) control.disabled = true;
      feedback.dataset.state = 'busy'; feedback.textContent = 'Importing ' + button.closest('li').querySelector('strong').textContent + '…';
      try {
        const data = new FormData(); data.set('selection', button.dataset.selection);
        const result = await call(intake.dataset.import, {method:'POST', body:data});
        if (!/^\/wallet\/0x[0-9a-f]{64}\/$/.test(result.url)) throw new Error('The document could not be opened.');
        window.location.assign(result.url);
      } catch (error) {
        importError = true; feedback.dataset.state = 'error'; feedback.textContent = error.message;
        generation++; importing = false; await refresh();
        for (const control of list.querySelectorAll('button')) control.disabled = false;
      }
    });
    document.getElementById('manual-import')?.addEventListener('click', () => {
      const picker = document.getElementById('file'); picker.value = ''; picker.focus();
    });
    document.getElementById('intake-arm').addEventListener('submit', async event => {
      event.preventDefault();
      generation++; importError = false; renderFiles([]);
      const form = event.currentTarget, button = form.querySelector('button');
      button.disabled = true;
      try {
        const response = await fetch(form.action, {method: 'POST', credentials: 'same-origin', body: new FormData(form)});
        if (!response.ok || response.redirected) {
          const body = await response.json();
          throw new Error(body.error || 'Pairing failed. Sign in and check the folder.');
        }
        if (intake.dataset.managed === 'yes') {
          const result = await response.json();
          if (!result.managed) throw new Error('The managed watcher could not be paired. Retry.');
          status.textContent = 'Folder paired. Your watcher connects automatically and continues while Foliolet is running.';
        } else {
          const blob = await response.blob();
          const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'foliolet-intake.json';
          link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
          status.textContent = 'Pairing file downloaded. Start the local companion, then download to your chosen folder. Watching continues while Foliolet is running.';
        }
        await refresh();
      } catch (e) { status.textContent = e.message + ' Manual upload remains available.'; }
      finally { button.disabled = false; }
    });
    stop.addEventListener('click', async () => {
      if (!session) return;
      generation++; importError = false;
      try {
        await call('/intake/sessions/' + encodeURIComponent(session.id) + '/stop/', {method: 'POST'});
        status.textContent = 'Watching stopped. New uploads using this pairing are denied.';
        stop.disabled = true; session = null; renderFiles([]);
        empty.textContent = 'Watching stopped. Enable folder intake to see its documents again.';
        feedback.textContent = '';
      } catch (e) { status.textContent = e.message; }
    });
    async function refresh() {
      if (refreshing || importing) return;
      refreshing = true;
      const currentGeneration = generation;
      try {
        const [body, inventory] = await Promise.all([call(intake.dataset.sessions), call(intake.dataset.files)]);
        if (generation !== currentGeneration || importing) return;
        session = body.sessions.find(s => s.active) || null;
        stop.disabled = !session;
        if (session) {
          status.textContent = (session.connected ? 'Watcher connected. ' : 'Local watcher not connected. ')
            + session.folder + (session.expiresAt ? ' · ends ' + new Date(session.expiresAt).toLocaleTimeString() : ' · while Foliolet is running')
            + ' · ' + session.imported + ' files received.';
        } else status.textContent = 'Local watcher not connected. Enable a session to receive new files, or upload normally.';
        renderFiles(session && inventory.sessionId === session.id ? inventory.files : []);
        empty.textContent = session ? 'No completed PDF, TXT or CSV files yet. Save a document in your watched folder.' : 'Enable a folder watcher to see its documents here.';
        if (!importError) {
          feedback.dataset.state = session?.connected ? 'connected' : 'waiting';
          feedback.textContent = session ? (session.connected ? 'Live folder · updates automatically' : 'Folder paired · watcher reconnecting') : 'No folder paired';
        }
      } catch (e) {
        if (generation !== currentGeneration) return;
        renderFiles([]); feedback.dataset.state = 'error'; feedback.textContent = e.message + ' Retrying automatically.';
      } finally { refreshing = false; }
    }
    refresh(); setInterval(refresh, 2000);
    window.addEventListener('focus', refresh);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
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
      ? 'Preview: suggested facts unchanged. Confirmation checks this again on the server.'
      : 'Preview: facts edited since extraction. The original proposal remains saved for comparison.';
  }
  rows?.addEventListener('input', () => { dirty = true; changed(); });
  rows?.addEventListener('change', () => { dirty = true; changed(); });
  rows?.addEventListener('click', event => { if (event.target.closest('.remove-fact')) { dirty = true; setTimeout(changed, 0); } });
  document.getElementById('add-fact')?.addEventListener('click', () => { dirty = true; setTimeout(changed, 0); });
  const reviewReasons = {
    OCR_REQUIRES_VISUAL_REVIEW: 'Read from an image; check the original characters.',
    LOW_FIELD_OCR_CONFIDENCE: 'Some words in this field were hard to read.',
    CONFLICTING_READINGS: 'The source readings disagree about this value.',
    RENDERED_VALUE_NOT_CORROBORATED: 'The rendered page did not independently confirm this field.',
    AMBIGUOUS_DUPLICATE_LABEL: 'This label has multiple possible values.',
    OCR_CHARACTER_CONFUSION: 'A letter and a number may have been confused. No correction was guessed.',
    NON_NUMERIC_SCORE_LITERAL: 'This score contains more than a plain number.',
    VALUE_OUTSIDE_EXPECTED_RANGE: 'This value is outside the usual range.',
    AMBIGUOUS_DATE_FORMAT: 'The date order is ambiguous; the source spelling was kept.',
    INVALID_DATE_LITERAL: 'This date needs checking.',
    UNPARSED_DATE_LITERAL: 'The original date spelling was kept.',
    UNALIGNED_OR_HIDDEN_GLYPHS_NEAR_FIELD: 'Overlapping, hidden or unmapped text affects this field.',
    MARK_EXCEEDS_PRINTED_MAXIMUM: 'This mark exceeds the maximum printed in the same row.',
    MODEL_SELECTED_ASSOCIATION: 'The local model linked these source cells; check that the label belongs to this value.',
    LABEL_READINGS_DISAGREE: 'The readings disagree about the field label.',
    LABEL_VALUE_BOUNDARY_REQUIRES_REVIEW: 'The label and value share a text cell; check their boundary.'
  };
  function sourceLink(field) {
    const source = document.createElement('a');
    const q = new URLSearchParams({documentId: field.citation.documentId, hash: field.citation.sourceHash, page: String(field.citation.page)});
    source.href = analysis.dataset.pdf === 'yes' ? '/ask-foli/api/page/?' + q
      : '/wallet/' + encodeURIComponent(field.citation.documentId.slice(7)) + '/file/';
    source.target = '_blank'; source.rel = 'noopener noreferrer'; source.textContent = analysis.dataset.pdf === 'yes' ? 'View original page' : 'View original file';
    return source;
  }
  function showFields(fields) {
    baseline = fields;
    if (!rows || !fields.length || dirty || applied || analysis.dataset.editable !== 'yes') { changed(); return; }
    const template = rows.firstElementChild.cloneNode(true); rows.replaceChildren();
    function append(field) {
      const row = template.cloneNode(true); row.querySelector('.scan-note')?.remove();
      for (const key of ['path','label','type','value']) row.querySelector('[name=claim_' + key + ']').value = field[key];
      const note = document.createElement('p'); note.className = 'help scan-note';
      note.textContent = 'Page ' + field.citation.page + ' · ' + (field.support?.quality === 'REVIEW_REQUIRED' ? 'Added for your review' : 'Source-supported association') + ' · ' + field.citation.provenance + '. ';
      if (field.citation.provenance.includes('OCR')) note.append('OCR may misread characters; check the original. ');
      if (field.citation.documentId.startsWith('wallet:')) note.append(sourceLink(field));
      const details = document.createElement('details'), summary = document.createElement('summary'), quote = document.createElement('p');
      summary.textContent = 'Source evidence'; quote.className = 'help wrap-any'; quote.textContent = field.evidence;
      details.append(summary, quote); row.append(details);
      row.appendChild(note); rows.appendChild(row);
    }
    const uncertain = fields.filter(f => f.support?.quality === 'REVIEW_REQUIRED');
    for (const field of fields.filter(f => f.support?.quality !== 'REVIEW_REQUIRED')) append(field);
    const review = document.getElementById('intake-review'); review?.replaceChildren();
    if (review && uncertain.length) {
      const heading = document.createElement('h3'); heading.textContent = 'Check before using'; review.append(heading);
      const explain = document.createElement('p'); explain.className = 'help'; explain.textContent = 'These values were located, but need your review. Open the original page, then add a value if it is correct. You can edit it in the fact rows.'; review.append(explain);
      for (const field of uncertain) {
        const card = document.createElement('div'); card.className = 'notice warning';
        const title = document.createElement('strong'); title.textContent = field.label + ': ' + field.value;
        const reason = document.createElement('p'); reason.className = 'help'; reason.textContent = [...new Set((field.support.reasons || []).map(r => reviewReasons[r] || 'Check this source association.'))].join(' ');
        const add = document.createElement('button'); add.type = 'button'; add.className = 'btn line small use-reviewed-fact'; add.textContent = 'Use after checking';
        add.addEventListener('click', () => {
          if (rows.children.length === 1 && !rows.firstElementChild.querySelector('[name=claim_value]').value) rows.replaceChildren();
          append(field); add.disabled = true; add.textContent = 'Added to review rows'; dirty = true; changed();
        });
        card.append(title, reason, sourceLink(field), document.createTextNode(' '), add); review.append(card);
        if (field.support.alternatives?.length) {
          const alt = document.createElement('p'); alt.className = 'help wrap-any';
          alt.textContent = 'Other reading: ' + field.support.alternatives.map(f => f.quote).join(' ') + '. Check the original before choosing a value.';
          card.append(alt);
        }
      }
    }
    if (!rows.children.length) rows.append(template);
    applied = true; changed();
  }
  function showLabels(body) {
    const labels = document.getElementById('intake-labels'); labels.replaceChildren();
    for (const stamp of body.stamps || []) {
      const tag = document.createElement('span');
      tag.className = 'mark ' + (['pass','caution','quiet','fail'].includes(stamp.tone) ? stamp.tone : 'quiet');
      tag.dataset.check = stamp.id; tag.dataset.state = stamp.state; tag.title = stamp.detail;
      tag.textContent = (stamp.state === 'PASSED' ? '✓ ' : '') + stamp.label + ' · ' + stamp.display;
      labels.appendChild(tag);
    }
  }
  async function poll() {
    try {
      const body = await call(analysis.dataset.url); stage.textContent = body.stage || 'Original saved. Enter facts manually or read locally.';
      showLabels(body); showFields(body.fields || []);
      const manifest = body.report?.manifest, indicators = body.report?.indicators;
      const diagnostic = body.report?.diagnostics, diagnosticBox = document.getElementById('intake-diagnostics');
      if (diagnosticBox) {
        diagnosticBox.replaceChildren();
        if (diagnostic) {
          const counts = document.createElement('p'); counts.textContent = diagnostic.candidates + ' associations located · ' + diagnostic.supported + ' supported · ' + diagnostic.reviewRequired + ' need review.'; diagnosticBox.append(counts);
          const reasonNames = {OVERLAPPING_VALUE_WITHHELD:'An overprinted number could not be read safely',OCR_LABEL_NOT_RECOGNIZED:'An OCR field label could not be identified safely',NO_ALIGNED_GEOMETRY:'Readable text had no aligned field locations',PAGE_UNREADABLE:'A page could not be read',INVISIBLE_SOURCE_TEXT:'Hidden PDF text excluded',WORD_OFFSET_OR_GEOMETRY_MISMATCH:'Text with mismatched locations excluded',OCR_TOO_WEAK_TO_SUGGEST:'Fields too unclear to suggest safely',INVALID_LITERAL_VALUE:'Invalid field values excluded',TABLE_VALUE_MISSING:'Table cells were missing',TABLE_COLUMN_COLLISION:'More than one value occupied a table cell',TABLE_OVERLAPPING_COLUMNS:'Overlapping columns could not be paired safely',CITATION_MISMATCH:'A source quote failed exact validation',FIELD_COUNT_LIMIT:'The field limit was reached',UNSAFE_CGPA_LITERAL:'An unclear CGPA was withheld',INVALID_LABEL_PATH:'A label could not be safely identified',EVIDENCE_SPAN_LIMIT:'Evidence was too spread out to associate safely',CONFLICTING_READINGS:'Conflicting source readings held for review'};
          for (const [code, count] of Object.entries(diagnostic.rejections || {})) { const p = document.createElement('p'); p.textContent = (reasonNames[code] || 'Other source checks') + ': ' + count + '.'; diagnosticBox.append(p); }
        }
      }
      document.getElementById('intake-coverage').textContent = manifest
        ? manifest.readablePages + '/' + manifest.totalPages + ' pages readable · ' + manifest.ocrPages + ' OCR pages · '
          + (indicators?.qrInspectedPages ?? indicators?.inspectedPages ?? 0) + '/' + (indicators?.totalPages || 0) + ' pages checked for QR · '
          + (indicators?.logoInspectedPages ?? indicators?.inspectedPages ?? 0) + '/' + (indicators?.totalPages || 0) + ' pages checked for logo.' : '';
      const warnings = [...(manifest?.warnings || []), ...(indicators?.warnings || []), ...(body.report?.suggestionWarnings || []),
        ...(manifest?.pages || []).flatMap(p => p.warnings.map(w => 'Page ' + p.number + ': ' + w)),
        ...(indicators?.pages || []).flatMap(p => p.warnings.map(w => 'Page ' + p.page + ': ' + w))];
      const box = document.getElementById('intake-warnings'); box.replaceChildren();
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
