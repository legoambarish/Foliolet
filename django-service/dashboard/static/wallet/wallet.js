document.addEventListener('DOMContentLoaded', () => {
  // Fact editor: add/remove rows. The last row is cleared instead of removed.
  const rows = document.getElementById('fact-rows');
  document.getElementById('add-fact')?.addEventListener('click', () => {
    const row = rows.firstElementChild.cloneNode(true);
    row.querySelectorAll('input').forEach(input => { input.value = ''; });
    row.querySelector('select').value = 'string';
    row.querySelector('.scan-note')?.remove();
    row.classList.remove('scanned');
    rows.appendChild(row);
    row.querySelector('input').focus();
  });
  rows?.addEventListener('click', event => {
    if (!event.target.matches('.remove-fact')) return;
    if (rows.children.length > 1) {
      const row = event.target.closest('.edit-row');
      (row.previousElementSibling || row.nextElementSibling).querySelector('input').focus();
      row.remove();
    } else rows.querySelectorAll('input').forEach(input => { input.value = ''; });
  });

  // Scan for fields: an AI model proposes facts, which land in the same editable rows a person
  // would type. Nothing is saved until the holder ticks the box and presses Confirm facts.
  const scan = document.getElementById('scan-fields');
  if (scan && rows) {
    const status = document.getElementById('scan-status');
    const blank = row => [...row.querySelectorAll('input')].every(input => !input.value.trim());
    const addRow = () => {
      const row = rows.firstElementChild.cloneNode(true);
      row.querySelectorAll('input').forEach(input => { input.value = ''; });
      row.querySelector('select').value = 'string';
      row.querySelector('.scan-note')?.remove();
      row.classList.remove('scanned');
      rows.appendChild(row);
      return row;
    };
    const fill = (row, field) => {
      row.querySelector('[name=claim_label]').value = field.label;
      row.querySelector('[name=claim_value]').value = field.value;
      row.querySelector('[name=claim_type]').value = field.type;
      row.querySelector('[name=claim_path]').value = field.path;
      row.querySelector('.scan-note')?.remove();
      const note = document.createElement('p'), tag = document.createElement('strong');
      note.className = 'help scan-note';
      tag.textContent = 'AI suggested. ';
      note.append(tag, field.evidence
        ? 'Found in your document: \u201c' + field.evidence + '\u201d'
        : 'Read from a page image. Check it carefully.');
      row.appendChild(note);
      row.classList.add('scanned');
    };
    scan.addEventListener('click', async () => {
      scan.disabled = true;
      status.textContent = 'Scanning your document. This can take up to a minute.';
      try {
        const token = document.querySelector('#claim-form [name=csrfmiddlewaretoken]').value;
        const response = await fetch(scan.dataset.url, {
          method: 'POST', credentials: 'same-origin',
          headers: { 'X-CSRFToken': token, 'Accept': 'application/json' },
        });
        if (response.redirected) throw new Error('Your session has ended. Please sign in again.');
        let body = null;
        try { body = await response.json(); } catch { /* not JSON: treated as a failed scan */ }
        if (!response.ok || !body || !Array.isArray(body.fields))
          throw new Error(body && body.error ? body.error : 'The scan could not be completed.');
        const known = new Set([...rows.querySelectorAll('[name=claim_path]')]
          .map(input => input.value.trim()).filter(Boolean));
        let added = 0, existing = 0, first = null;
        for (const field of body.fields) {
          if (known.has(field.path)) { existing++; continue; }
          known.add(field.path);
          const row = [...rows.children].find(blank) || addRow();
          fill(row, field);
          first = first || row;
          added++;
        }
        const parts = [added ? 'Added ' + added + ' suggested field' + (added === 1 ? '' : 's') + '.'
                             : 'No new fields were found.'];
        if (existing) parts.push(existing + ' already in your list.');
        if (body.discarded) parts.push(body.discarded + ' unreliable suggestion' + (body.discarded === 1 ? ' was' : 's were') + ' discarded.');
        if (body.source === 'image') parts.push('These were read from page images, so check them closely.');
        parts.push(added ? 'Check each value against your document, fix or remove anything wrong, then confirm.'
                         : 'You can still add facts by hand.');
        status.textContent = parts.join(' ');
        if (first) first.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } catch (error) {
        status.textContent = 'Scan failed. ' + error.message + ' You can still add facts by hand.';
      } finally {
        scan.disabled = false;
      }
    });
  }

  // Composer: the slip shows exactly the checked facts and one redaction bar per unchecked fact.
  const composer = document.getElementById('compose-form');
  if (composer) {
    const choices = [...composer.querySelectorAll('input[name=claims]')];
    const lines = [...document.querySelectorAll('#slip-lines [data-claim]')];
    const bars = [...document.querySelectorAll('#slip .redacted')];
    const to = document.getElementById('slip-to'), purpose = document.getElementById('slip-purpose');
    const button = document.getElementById('create-proof');
    const update = () => {
      const selected = choices.filter(input => input.checked);
      lines.forEach((line, i) => {
        const show = choices[i].checked;
        if (show && line.hidden) line.classList.add('fade-in');
        line.hidden = !show;
      });
      bars.forEach((bar, i) => bar.classList.toggle('off', i >= choices.length - selected.length));
      document.getElementById('slip-empty').hidden = selected.length > 0;
      document.getElementById('private-count').textContent = choices.length - selected.length;
      document.getElementById('disclosed-count').textContent = selected.length;
      document.getElementById('plural').textContent = selected.length === 1 ? '' : 's';
      button.disabled = !selected.length;
      to.textContent = composer.verifier_label.value.trim() || '(who it is for)';
      purpose.textContent = composer.purpose.value.trim();
    };
    composer.addEventListener('change', update);
    composer.addEventListener('input', update);
    update();
  }

  // Share receipt: copy and QR.
  const copy = document.getElementById('copy-link');
  copy?.addEventListener('click', async () => {
    const field = document.getElementById('share-url'), status = document.getElementById('copy-status');
    try {
      await navigator.clipboard.writeText(field.value);
      copy.textContent = 'Copied';
      status.textContent = 'Link copied. Send it only to the intended verifier.';
    } catch {
      field.select();
      status.textContent = 'Press Ctrl+C (or ⌘C) to copy the selected link.';
    }
  });
  const qrBox = document.getElementById('qr-code');
  if (qrBox && typeof qrcode === 'function') {
    const qr = qrcode(0, 'M');
    qr.addData(document.getElementById('share-url').value);
    qr.make();
    qrBox.innerHTML = qr.createImgTag(5, 8, 'QR code for the proof link');
  }
});
