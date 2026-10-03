document.addEventListener('DOMContentLoaded', () => {
  // Fact editor: add/remove rows. The last row is cleared instead of removed.
  const rows = document.getElementById('fact-rows');
  document.getElementById('add-fact')?.addEventListener('click', () => {
    const row = rows.firstElementChild.cloneNode(true);
    row.querySelectorAll('input').forEach(input => { input.value = ''; });
    row.querySelector('select').value = 'string';
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
