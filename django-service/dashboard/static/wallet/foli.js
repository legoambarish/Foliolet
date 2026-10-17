/* Private, ephemeral Ask Foli. Model/source strings are always DOM text nodes. */
(() => {
  'use strict';
  const root = document.getElementById('foli-app');
  if (!root) return;
  const $ = id => document.getElementById('foli-' + id);
  const state = {documents: [], selected: null, manifest: null, history: [], activeJob: null,
    busy: false, generation: 0, retry: null, source: null, sourceGeneration: 0, health: null};
  const csrf = root.querySelector('[name=csrfmiddlewaretoken]').value;
  const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined && text !== null) element.textContent = String(text);
    if (className) element.className = className;
    return element;
  };
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
  const endpoint = (path, params) => {
    const url = new URL(root.dataset.api + path + '/', window.location.origin);
    if (params) Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, String(value)));
    return url.pathname + url.search;
  };
  async function api(path, {method = 'GET', payload, params} = {}) {
    let response;
    try {
      response = await fetch(endpoint(path, params), {method, credentials: 'same-origin', redirect: 'error',
        headers: {'Accept': 'application/json', ...(method !== 'GET' ? {'X-CSRFToken': csrf} : {}),
          ...(payload ? {'Content-Type': 'application/json'} : {})},
        ...(payload ? {body: JSON.stringify(payload)} : {})});
    } catch (_) { throw {code: 'SERVICE_OFFLINE', message: 'The private application is unavailable. Check the local services and retry.'}; }
    let data;
    try { data = await response.json(); }
    catch (_) { throw {code: 'INVALID_RESPONSE', message: 'The private application returned an unreadable response. Refresh the page.'}; }
    if (!response.ok) {
      if (response.status === 401) {
        state.history = []; state.documents = []; state.manifest = null; state.selected = null; state.source = null;
        $('log').replaceChildren(); $('documents').replaceChildren(); $('coverage').hidden = true;
        $('question').value = ''; $('document-title').textContent = 'Signed out'; $('document-subtitle').textContent = 'Sign in to continue';
        $('source-dialog').close(); state.generation++; setBusy(false);
        alert('Your session is no longer authorized. Sign in again.', null, 'SIGNED_OUT');
      }
      throw data;
    }
    return data;
  }
  function alert(message, retry = null, code = '') {
    const box = $('alert'); box.replaceChildren(node('span', message)); box.hidden = false;
    if (retry) {
      const button = node('button', 'Retry', 'foli-small-btn'); button.type = 'button';
      button.addEventListener('click', () => { box.hidden = true; retry(); }); box.append(button);
    }
    if (code === 'SIGNED_OUT') {
      const link = node('a', 'Sign in'); link.href = root.dataset.login; box.append(' ', link);
    }
  }
  function failure(error, retry) {
    const messages = {
      OFFLINE: 'Ollama is offline. Start tools/start-foli-ollama.ps1, then retry.',
      MODEL_MISSING: 'The configured local model is missing. Install the model named in the startup guide, then retry.',
      CLOUD_NOT_DISABLED: 'Ollama cloud mode is enabled. Restart with tools/start-foli-ollama.ps1; Foli refused to send your question.',
      SOURCE_CHANGED: 'This source changed or its citation expired. Select the document again to read the current version.',
      SOURCE_UNAVAILABLE: 'The original source is unavailable. Foli has not restored or changed it.',
      BUSY: 'The local reader is busy. Wait a moment or stop the current request.',
      RATE_LIMIT: 'You have sent several requests. Wait a minute and retry.',
      CONTEXT_LIMIT: 'This question and its evidence exceed the local context budget. Shorten the question or clear the conversation.'
    };
    alert(messages[error.code] || error.message || 'Foli could not finish the request. Retry or inspect the source.', retry, error.code);
  }
  function setBusy(value) {
    state.busy = value; $('progress').hidden = !value;
    $('send').disabled = value || !$('question').value.trim();
    $('review').disabled = value || !state.selected || !state.selected.supported;
    $('source-open').disabled = !state.manifest;
    $('log').setAttribute('aria-busy', String(value));
  }
  function resizeComposer() {
    // CSS alone keeps this control bounded; no inline style or HTML injection.
    $('question').rows = Math.min(5, Math.max(1, $('question').value.split('\n').length));
    $('send').disabled = state.busy || !$('question').value.trim();
  }
  function dismissWelcome() { const welcome = $('welcome'); if (welcome) welcome.remove(); }
  function scrollLog() { $('log').scrollTop = $('log').scrollHeight; }
  function userMessage(text) {
    dismissWelcome(); $('log').append(node('div', text, 'foli-message foli-message-user')); scrollLog();
  }
  function citationButton(citation) {
    const label = state.manifest && state.manifest.format !== 'pdf' ? 'Segment' : 'Page';
    const button = node('button', `${label} ${citation.page} · source matched`, 'foli-citation');
    button.type = 'button'; button.append(node('small', citation.provenance));
    button.addEventListener('click', () => showSource(citation)); return button;
  }
  function appendInline(container, text, citations) {
    const pattern = /\[(E\d+)\]|\*\*([^*\n]+)\*\*|`([^`\n]+)`/g;
    let start = 0, match;
    while ((match = pattern.exec(text))) {
      container.append(document.createTextNode(text.slice(start, match.index)));
      if (match[1]) {
        const citation = citations.find(c => c.id === match[1]);
        if (citation) {
          const button = node('button', `[${match[1]}]`, 'foli-inline-source'); button.type = 'button';
          button.setAttribute('aria-label', `View source ${match[1]}, page ${citation.page}`);
          button.addEventListener('click', () => showSource(citation)); container.append(button);
        } else container.append(document.createTextNode(match[0]));
      } else container.append(node(match[2] ? 'strong' : 'code', match[2] || match[3]));
      start = pattern.lastIndex;
    }
    container.append(document.createTextNode(text.slice(start)));
  }
  function safeMarkdown(container, text, citations = []) {
    // A deliberately small markdown subset. Links, HTML, images and URLs remain text.
    let code = false, pre = null, list = null;
    for (const line of String(text).split('\n')) {
      if (/^```/.test(line)) { code = !code; list = null; if (code) { pre = node('pre', ''); container.append(pre); } continue; }
      if (code) { pre.append(document.createTextNode(line + '\n')); continue; }
      const bullet = line.match(/^\s*(?:[-*]|\d+[.)])\s+(.+)$/);
      if (bullet) {
        if (!list) { list = node('ul'); container.append(list); }
        const item = node('li'); appendInline(item, bullet[1], citations); list.append(item); continue;
      }
      list = null; if (!line.trim()) continue;
      const paragraph = node('p'); appendInline(paragraph, line.replace(/^#{1,4}\s+/, ''), citations); container.append(paragraph);
    }
  }
  function notes(warnings) {
    const box = node('details', null, 'foli-answer-notes'); box.append(node('summary', 'Coverage & reading cautions'));
    const list = node('ul'); [...new Set(warnings)].forEach(warning => list.append(node('li', warning))); box.append(list); return box;
  }
  function renderFindings(container, answer) {
    const coverage = answer.reviewCoverage || {};
    container.append(node('p', `Checklist: ${coverage.checklistPages}/${coverage.totalPages} pages or segments · Semantic review: ${coverage.semanticChunks}/${coverage.totalChunks} chunks${coverage.semanticComplete ? '' : ' (partial)'}`, 'foli-review-summary'));
    const filter = node('label', 'Show ', 'foli-filter'); const select = node('select');
    select.setAttribute('aria-label', 'Filter fine-print findings');
    const all = node('option', 'All reading flags'); all.value = ''; select.append(all);
    const categories = [...new Set(answer.findings.flatMap(f => f.categories))].sort();
    categories.forEach(category => { const option = node('option', category.charAt(0).toUpperCase() + category.slice(1)); option.value = category; select.append(option); });
    filter.append(select); container.append(filter); const cards = [];
    for (const finding of answer.findings) {
      const card = node('details', null, 'foli-finding');
      const summary = node('summary', finding.title);
      const first = finding.citations[0]; summary.append(node('small', `Page/segment ${first.page}${finding.priority === 'attention' ? ' · possible conflict' : ''}`)); card.append(summary);
      const content = node('div', null, 'foli-finding-content');
      content.append(node('p', finding.explanation));
      if (finding.modelInterpretation) {
        content.append(node('p', 'AI interpretation · verify against the passage', 'muted small'));
        const interpretation = node('div'); safeMarkdown(interpretation, finding.modelInterpretation); content.append(interpretation);
      }
      finding.citations.forEach(citation => { content.append(node('blockquote', citation.quote)); content.append(citationButton(citation)); });
      if (finding.definitions.length) {
        content.append(node('p', 'Related definitions', 'muted small'));
        const sources = node('div', null, 'foli-citations'); finding.definitions.forEach(c => sources.append(citationButton(c))); content.append(sources);
      }
      finding.references.forEach(reference => {
        content.append(node('p', `${reference.label}: ${reference.status}`, 'muted small'));
        reference.sources.forEach(citation => content.append(citationButton(citation)));
      });
      if (finding.warnings.length) content.append(notes(finding.warnings));
      card.append(content); container.append(card); cards.push({card, finding});
    }
    select.addEventListener('change', () => cards.forEach(({card, finding}) => { card.hidden = !!select.value && !finding.categories.includes(select.value); }));
  }
  function assistantMessage(answer) {
    dismissWelcome(); const message = node('article', null, 'foli-message foli-message-assistant');
    const header = node('div', null, 'foli-message-header'); header.append(node('strong', 'Foli'));
    const labels = {GENERAL: 'General explanation', INTERPRETATION: 'AI interpretation · inspect the evidence',
      DOCUMENT_REVIEW: 'Whole-document reading review', READ_ONLY_EXPLANATION: 'Read-only assistant', NO_SOURCE_SUPPORT: 'No source support confirmed'};
    header.append(node('span', labels[answer.answerKind] || 'Reading assistant')); message.append(header);
    const body = node('div', null, 'foli-message-body'); safeMarkdown(body, answer.answer, answer.citations || []); message.append(body);
    if (answer.findings && answer.findings.length) renderFindings(body, answer);
    else if (answer.citations && answer.citations.length) {
      const sources = node('div', null, 'foli-citations'); answer.citations.forEach(c => sources.append(citationButton(c))); message.append(sources);
    }
    if (answer.warnings && answer.warnings.length) message.append(notes(answer.warnings));
    const tools = node('div', null, 'foli-result-tools'); const copy = node('button', 'Copy answer', 'text-btn'); copy.type = 'button';
    copy.addEventListener('click', async () => {
      try { await navigator.clipboard.writeText(answer.answer); copy.textContent = 'Copied'; }
      catch (_) { copy.textContent = 'Select the answer to copy'; }
    }); tools.append(copy);
    if (answer.performance && answer.performance.modelMilliseconds) tools.append(node('span', `${(answer.performance.modelMilliseconds / 1000).toFixed(1)}s local inference`, 'muted small'));
    message.append(tools); $('log').append(message); scrollLog();
  }
  function renderManifest(manifest) {
    state.manifest = manifest; $('coverage').hidden = false;
    $('coverage-summary').textContent = `${manifest.readablePages}/${manifest.totalPages} readable · ${manifest.accountedPages} accounted for${manifest.ocrPages ? ` · ${manifest.ocrPages} OCR` : ''}${manifest.complete ? '' : ' · check cautions'}`;
    const content = $('coverage-content'); content.className = 'foli-coverage-content'; content.replaceChildren();
    const warnings = [...manifest.warnings, ...manifest.pages.flatMap(page => page.warnings.map(w => `Page/segment ${page.number}: ${w}`))];
    if (warnings.length) content.append(notes(warnings));
    const list = node('ul');
    manifest.pages.forEach(page => {
      const item = node('li'); const button = node('button', `${manifest.format === 'pdf' ? 'Page' : 'Segment'} ${page.number} · ${page.status}${page.confidence != null ? ` · OCR ${page.confidence.toFixed(0)}%` : ''}${page.firstLine ? ` · lines ${page.firstLine}–${page.lastLine}` : ''}`, 'text-btn');
      button.type = 'button'; button.addEventListener('click', () => showSource({documentId: manifest.documentId, sourceHash: manifest.sourceHash, page: page.number})); item.append(button); list.append(item);
    }); content.append(list); $('source-open').disabled = false;
  }
  async function run(mode, question = '') {
    if (state.busy) return;
    if ((mode === 'index' || mode === 'review') && !state.selected) { alert('Select a document from Your sources first.'); return; }
    if (state.selected && !state.selected.supported) { alert('This file type is not supported yet. Choose PDF, UTF-8 TXT or CSV.'); return; }
    const generation = ++state.generation; setBusy(true); $('alert').hidden = true; state.retry = () => run(mode, question);
    $('progress-label').textContent = mode === 'review' ? 'Starting a whole-document reading review' : mode === 'index' ? 'Opening your source' : 'Preparing your question';
    const payload = {mode, question, history: mode === 'chat' ? state.history.slice(-6) : []};
    if(mode === 'chat' && $('cloud-consent')?.checked) payload.cloudConsent = true;
    if($('cloud-consent')) $('cloud-consent').checked = false;
    if (state.selected) payload.documentId = state.selected.id;
    if (state.manifest) payload.sourceHash = state.manifest.sourceHash;
    try {
      const job = await api('jobs', {method: 'POST', payload});
      if (generation !== state.generation) { await api('jobs/' + job.id, {method: 'DELETE'}); return; }
      state.activeJob = job.id; let result = job, previewShown = false; const start = Date.now();
      while (result.state === 'QUEUED' || result.state === 'RUNNING') {
        if (generation !== state.generation) return;
        if(result.preview && !previewShown) {
          assistantMessage({...result.preview,answer:'Initial source checklist. Model interpretation is still running. '+result.preview.answer});
          previewShown = true;
        }
        $('progress-label').textContent = result.stage; await pause(600);
        if (Date.now() - start > 320000) throw {code: 'TIMEOUT', message: 'The local request took too long. Stop it and retry.'};
        result = await api('jobs/' + job.id);
      }
      if (generation !== state.generation) return;
      if (result.state === 'ERROR') throw {code: result.code, message: result.message};
      if (result.state === 'CANCELLED') { alert('Request stopped. No document or trust data was changed.'); return; }
      if (mode === 'index') renderManifest(result.result);
      else {
        if (result.result.manifest) renderManifest(result.result.manifest);
        assistantMessage(result.result);
        if (mode === 'chat') {
          state.history.push({role: 'user', text: question.slice(0, 1500)}, {role: 'assistant', text: result.result.answer.slice(0, 1500)});
          state.history = state.history.slice(-6);
        }
      }
    } catch (error) { if (generation === state.generation) failure(error, state.retry); }
    finally { if (generation === state.generation) { state.activeJob = null; setBusy(false); } }
  }
  async function stop() {
    const id = state.activeJob; state.generation++; state.activeJob = null; setBusy(false);
    if (id) { try { await api('jobs/' + id, {method: 'DELETE'}); } catch (error) { failure(error); } }
  }
  async function selectDocument(document) {
    await stop(); state.selected = document; state.manifest = null; state.history = []; state.retry = null;
    $('log').replaceChildren(); $('coverage').hidden = true; $('alert').hidden = true; $('source-dialog').close();
    $('document-title').textContent = document ? document.name : 'General conversation';
    $('document-subtitle').textContent = document ? `${document.format.toUpperCase()} · version ${document.version} · ${document.status.toLowerCase()}` : 'General explanations · no source selected';
    $('question').placeholder = document ? 'Ask anything about this document…' : 'Ask Foli a question…';
    $('general').setAttribute('aria-pressed', String(!document)); renderDocuments(); setBusy(false);
    if (document) {
      if (!document.supported) alert('This file type is not supported yet. Foli currently reads PDF, UTF-8 TXT and CSV.');
      else await run('index');
    } else assistantMessage({answer: 'Hello. Ask general questions here. To summarize or ask about a document, select it from Your sources in the sidebar first.', answerKind: 'GENERAL', citations: [], warnings: []});
    $('question').focus();
  }
  function renderDocuments() {
    const list = $('documents'); list.replaceChildren(); const query = $('search').value.toLocaleLowerCase();
    const documents = state.documents.filter(d => `${d.name} ${d.filename}`.toLocaleLowerCase().includes(query));
    documents.forEach(document => {
      const button = node('button', null, 'foli-doc'); button.type = 'button';
      button.setAttribute('aria-pressed', String(state.selected && state.selected.id === document.id)); button.title = document.filename;
      button.append(node('span', document.format.toUpperCase(), 'foli-doc-icon'));
      const label = node('span'); label.append(node('strong', document.name), node('small', `${document.id.startsWith('wallet:') ? 'Wallet' : 'Legacy'} · v${document.version}${document.supported ? '' : ' · unsupported'}`));
      button.append(label); button.addEventListener('click', () => selectDocument(document)); list.append(button);
    });
    if (!documents.length) list.append(node('p', state.documents.length ? 'No matching documents.' : 'No documents yet. Add one in Documents to read it here.', 'foli-library-empty'));
  }
  async function refreshDocuments() {
    try {
      state.documents = await api('documents'); renderDocuments();
      if (state.selected && !state.documents.some(d => d.id === state.selected.id)) { await selectDocument(null); alert('The selected source is no longer available.'); }
    } catch (error) { failure(error, refreshDocuments); $('documents').replaceChildren(node('p', 'Could not load your sources.', 'foli-library-empty')); }
  }
  async function health() {
    try {
      const result = await api('health'); state.health = result; const runtime = result.ollama;
      if($('cloud-option')) $('cloud-option').hidden = result.geminiAvailable !== true;
      const labels = {READY: 'Local model ready', OFFLINE: 'Local model offline', MODEL_MISSING: 'Model not installed', CLOUD_NOT_DISABLED: 'Cloud mode blocked', MODEL_SIZE_LIMIT: 'Model exceeds limit'};
      $('health-label').textContent = labels[runtime.status] || 'Local model unavailable'; $('health').dataset.status = runtime.status;
      $('health').title = `${runtime.model} · ${result.ocr}${runtime.cloudDisabled ? ' · cloud disabled' : ''}`;
    } catch (error) { $('health-label').textContent = 'Service unavailable'; $('health').dataset.status = 'OFFLINE'; failure(error, health); }
  }
  async function showSource(citation) {
    const generation = ++state.sourceGeneration; state.source = citation;
    if (!$('source-dialog').open) $('source-dialog').showModal();
    $('source-title').textContent = state.selected ? state.selected.name : 'Source passage'; $('source-text').textContent = 'Loading permitted source…';
    $('source-status').textContent = 'Checking current access and source hash'; $('original').hidden = true; $('page-image').removeAttribute('src');
    $('original-toggle').textContent = 'Show original page';
    try {
      const data = await api('source', {params: {documentId: citation.documentId, hash: citation.sourceHash, page: citation.page}});
      if (generation !== state.sourceGeneration) return;
      const page = data.page; $('source-text').replaceChildren();
      if (Number.isInteger(citation.start) && citation.start >= 0 && citation.end <= page.text.length && page.text.slice(citation.start, citation.end) === citation.quote) {
        $('source-text').append(document.createTextNode(page.text.slice(0, citation.start)), node('mark', citation.quote), document.createTextNode(page.text.slice(citation.end)));
      } else $('source-text').textContent = page.text || 'No readable text on this page. Inspect the rendered original.';
      $('page-label').textContent = `${data.document.format === 'pdf' ? 'Page' : 'Segment'} ${page.number}${state.manifest ? ' of ' + state.manifest.totalPages : ''}${page.firstLine ? ` · lines ${page.firstLine}–${page.lastLine}` : ''}`;
      $('source-status').textContent = `${page.status}${page.confidence != null ? ' · OCR confidence ' + page.confidence.toFixed(0) + '%' : ''} · ${page.warnings.join(' ') || 'Compare the source before relying on an interpretation.'}`;
      $('original-toggle').hidden = data.document.format !== 'pdf'; $('page-prev').disabled = page.number <= 1;
      $('page-next').disabled = !state.manifest || page.number >= state.manifest.totalPages;
      $('source-text').scrollIntoView({block: 'nearest'});
    } catch (error) { if (generation === state.sourceGeneration) { $('source-text').textContent = ''; $('source-status').textContent = error.message || 'Source no longer available.'; } }
  }
  $('source-close').addEventListener('click', () => { state.sourceGeneration++; $('source-dialog').close(); $('page-image').removeAttribute('src'); });
  $('source-dialog').addEventListener('close', () => { state.sourceGeneration++; state.source = null; $('source-text').replaceChildren(); $('page-image').removeAttribute('src'); });
  $('page-prev').addEventListener('click', () => showSource({...state.source, page: state.source.page - 1, start: null, end: null, quote: null}));
  $('page-next').addEventListener('click', () => showSource({...state.source, page: state.source.page + 1, start: null, end: null, quote: null}));
  $('original-toggle').addEventListener('click', () => {
    const reveal = $('original').hidden; $('original').hidden = !reveal; $('original-toggle').textContent = reveal ? 'Hide original page' : 'Show original page';
    if (reveal) $('page-image').src = endpoint('page', {documentId: state.source.documentId, hash: state.source.sourceHash, page: state.source.page});
  });
  $('page-image').addEventListener('error', () => { $('source-status').textContent = 'The original page preview could not be loaded. Access may have changed or the reader may be busy; retry the source.'; });
  $('source-open').addEventListener('click', () => state.manifest && showSource({documentId: state.manifest.documentId, sourceHash: state.manifest.sourceHash, page: 1}));
  $('general').addEventListener('click', () => selectDocument(null)); $('search').addEventListener('input', renderDocuments);
  $('refresh').addEventListener('click', refreshDocuments); $('health').addEventListener('click', health);
  $('question').addEventListener('input', resizeComposer);
  $('question').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); $('form').requestSubmit(); }
  });
  $('form').addEventListener('submit', event => {
    event.preventDefault(); const question = $('question').value.trim(); if (!question || state.busy) return;
    userMessage(question); $('question').value = ''; resizeComposer(); run('chat', question);
  });
  $('review').addEventListener('click', () => { if (!state.busy) { userMessage('Review the whole document for fine print, exceptions and possible conflicts.'); run('review'); } });
  root.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => { $('question').value = button.dataset.question; resizeComposer(); $('question').focus(); }));
  root.querySelectorAll('[data-review]').forEach(button => button.addEventListener('click', () => { if (state.selected) $('review').click(); else alert('Select a document from Your sources to review its fine print.'); }));
  $('stop').addEventListener('click', async () => { await stop(); alert('Request stopped. Your source was not changed.'); });
  $('clear').addEventListener('click', async () => {
    await stop(); state.history = []; state.manifest = null; $('log').replaceChildren(); $('coverage').hidden = true; $('source-dialog').close(); $('question').value = ''; resizeComposer();
    try { await api('memory', {method: 'DELETE'}); assistantMessage({answer: 'Conversation and cached readings cleared. Your documents are unchanged. Ask a new question whenever you are ready.', answerKind: 'GENERAL', citations: [], warnings: []}); $('alert').hidden = true; }
    catch (error) { failure(error); } setBusy(false); $('question').focus();
  });
  // No localStorage/sessionStorage, IndexedDB, service worker or durable history.
  window.addEventListener('pagehide', () => {
    state.history = []; state.documents = []; state.selected = null; state.manifest = null; state.source = null;
    $('log').replaceChildren(); $('documents').replaceChildren(); $('source-text').replaceChildren(); $('question').value = '';
  });
  window.addEventListener('pageshow', event => { if (event.persisted) window.location.reload(); });
  refreshDocuments(); health();
})();
