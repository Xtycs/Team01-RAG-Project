const state = {
  step: 0,
  apiBase: 'http://localhost:8000',
  lastConfig: null,
  lastIngestion: null,
  lastAnswer: null,
};

const steps = Array.from(document.querySelectorAll('.wizard-step'));
const indicators = Array.from(document.querySelectorAll('.step-indicator'));
const setupForm = document.querySelector('#setup-form');
const ingestForm = document.querySelector('#ingest-form');
const queryForm = document.querySelector('#query-form');
const setupStatus = document.querySelector('#setup-status');
const ingestStatus = document.querySelector('#ingest-status');
const queryStatus = document.querySelector('#query-status');
const ingestLog = document.querySelector('#ingest-log');
const resultPanel = document.querySelector('#result-panel');
const resultPlaceholder = document.querySelector('#result-placeholder');
const answerElement = document.querySelector('#answer');
const citationsElement = document.querySelector('#citations');
const snippetsElement = document.querySelector('#snippets');

function goToStep(index) {
  state.step = Math.max(0, Math.min(index, steps.length - 1));
  steps.forEach((step, idx) => {
    step.classList.toggle('active', idx === state.step);
  });
  indicators.forEach((indicator, idx) => {
    indicator.classList.toggle('active', idx === state.step);
  });
}

function showStatus(output, message, kind = 'info') {
  if (!output) return;
  output.textContent = message;
  output.dataset.status = kind;
}

function resetWizard() {
  setupForm.reset();
  ingestForm.reset();
  queryForm.reset();
  ingestLog.innerHTML = '';
  resultPanel.hidden = true;
  resultPlaceholder.hidden = false;
  answerElement.textContent = '';
  citationsElement.innerHTML = '';
  snippetsElement.innerHTML = '';
  state.lastConfig = null;
  state.lastIngestion = null;
  state.lastAnswer = null;
  state.apiBase = 'http://localhost:8000';
  showStatus(setupStatus, '');
  showStatus(ingestStatus, '');
  showStatus(queryStatus, '');
  goToStep(0);
}

async function request(path, payload) {
  let response;
  try {
    response = await fetch(`${state.apiBase}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (networkError) {
    throw new Error(`Unable to reach API gateway: ${networkError.message}`);
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = data?.error || `Request failed with status ${response.status}`;
    throw new Error(error);
  }
  return data;
}

setupForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formData = new FormData(setupForm);
  const apiBase = (formData.get('apiBase') || '').toString().trim();
  if (!apiBase) {
    showStatus(setupStatus, 'Please provide a valid API base URL.', 'error');
    return;
  }
  state.apiBase = apiBase.replace(/\/$/, '');
  const index = (formData.get('index') || 'hnsw').toString();
  const payload = {
    index,
    dimension: Number(formData.get('dimension') || 256),
    chunk_size: Number(formData.get('chunkSize') || 400),
    overlap: Number(formData.get('overlap') || 40),
  };
  const generatorMaxTokens = formData.get('generatorMaxTokens');
  if (generatorMaxTokens) {
    payload.generator_max_tokens = Number(generatorMaxTokens);
  }
  const indexParams = {};
  if (index === 'hnsw') {
    indexParams.ef = Number(formData.get('hnswEf') || 32);
  } else if (index === 'ivf') {
    indexParams.n_lists = Number(formData.get('ivfLists') || 4);
    indexParams.iterations = Number(formData.get('ivfIterations') || 5);
  }
  if (Object.keys(indexParams).length > 0) {
    payload.index_params = indexParams;
  }
  showStatus(setupStatus, 'Connecting to gateway...', 'info');
  try {
    const result = await request('/setup', payload);
    state.lastConfig = result;
    showStatus(setupStatus, 'Gateway configured successfully. You can upload documents next.', 'success');
    goToStep(1);
  } catch (error) {
    console.error(error);
    showStatus(setupStatus, error.message, 'error');
  }
});

function renderIngestionSummary(summary) {
  ingestLog.innerHTML = '';
  if (!summary || !summary.documents || summary.documents.length === 0) {
    const item = document.createElement('li');
    item.textContent = 'No documents ingested yet.';
    ingestLog.appendChild(item);
    return;
  }
  summary.documents.forEach((doc) => {
    const item = document.createElement('li');
    const label = doc.name || doc.metadata?.source || 'Untitled document';
    item.innerHTML = `<strong>${label}</strong> · ${doc.chunks} chunks`;
    ingestLog.appendChild(item);
  });
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error(`Failed to read ${file.name}`));
    reader.readAsText(file);
  });
}

ingestForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!state.lastConfig) {
    showStatus(setupStatus, 'Configure the gateway before ingesting documents.', 'error');
    goToStep(0);
    return;
  }
  const formData = new FormData(ingestForm);
  const files = ingestForm.querySelector('#document-files').files;
  const manualText = (formData.get('manualText') || '').toString().trim();
  const sourceLabel = (formData.get('sourceLabel') || '').toString().trim();
  const documents = [];

  for (const file of files) {
    if (!file) continue;
    const text = await readFileAsText(file);
    documents.push({
      name: file.name,
      content: text,
      metadata: {
        source: file.name,
        size: file.size,
        type: file.type || 'text/plain',
      },
    });
  }

  if (manualText) {
    documents.push({
      name: sourceLabel || 'Manual entry',
      content: manualText,
      metadata: {
        source: sourceLabel || 'Manual entry',
        origin: 'manual',
      },
    });
  }

  if (documents.length === 0) {
    showStatus(ingestStatus, 'Add files or paste text before ingesting.', 'error');
    return;
  }

  showStatus(ingestStatus, 'Uploading documents...', 'info');
  try {
    const result = await request('/ingest', { documents });
    state.lastIngestion = result;
    renderIngestionSummary(result);
    showStatus(ingestStatus, `Ingested ${result.chunks} chunks across ${result.documents.length} document(s).`, 'success');
  } catch (error) {
    console.error(error);
    showStatus(ingestStatus, error.message, 'error');
  }
});

function renderTemplate(list, templateId, entries) {
  const template = document.querySelector(templateId);
  list.innerHTML = '';
  if (!entries || entries.length === 0) {
    const item = document.createElement('li');
    item.textContent = 'No entries available yet.';
    list.appendChild(item);
    return;
  }
  entries.forEach((entry) => {
    const clone = template.content.firstElementChild.cloneNode(true);
    clone.querySelector('.source').textContent = entry.metadata?.source || entry.source || 'Unknown source';
    const scoreValue = entry.score?.toFixed ? entry.score.toFixed(3) : entry.score;
    clone.querySelector('.score').textContent = scoreValue !== undefined ? `Score: ${scoreValue}` : '';
    clone.querySelector('.text').textContent = entry.content || entry.text || '';
    list.appendChild(clone);
  });
}

function renderResults(result) {
  if (!result) {
    resultPanel.hidden = true;
    resultPlaceholder.hidden = false;
    return;
  }
  answerElement.textContent = result.answer || '';
  renderTemplate(citationsElement, '#citation-template', result.citations || []);
  renderTemplate(snippetsElement, '#snippet-template', result.snippets || []);
  resultPanel.hidden = false;
  resultPlaceholder.hidden = true;
}

queryForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!state.lastConfig) {
    showStatus(queryStatus, 'Configure the gateway first.', 'error');
    goToStep(0);
    return;
  }
  const formData = new FormData(queryForm);
  const question = (formData.get('question') || '').toString().trim();
  const topK = Number(formData.get('topK') || 3);
  const nProbeRaw = formData.get('nProbe');
  if (!question) {
    showStatus(queryStatus, 'Enter a question to run retrieval.', 'error');
    return;
  }
  const payload = {
    question,
    k: topK,
  };
  const nProbe = nProbeRaw ? Number(nProbeRaw) : null;
  if (nProbe) {
    payload.retrieval = { n_probe: nProbe };
  }
  showStatus(queryStatus, 'Running retrieval and generation...', 'info');
  try {
    const result = await request('/query', payload);
    state.lastAnswer = result;
    renderResults(result);
    showStatus(queryStatus, 'Answer generated with supporting citations.', 'success');
    goToStep(3);
  } catch (error) {
    console.error(error);
    showStatus(queryStatus, error.message, 'error');
  }
});

function handleNavigation(event) {
  const button = event.target.closest('button[data-nav]');
  if (!button) return;
  const action = button.dataset.nav;
  if (action === 'back') {
    goToStep(state.step - 1);
  } else if (action === 'next') {
    goToStep(state.step + 1);
  } else if (action === 'restart') {
    resetWizard();
  }
}

document.querySelectorAll('.step-actions').forEach((container) => {
  container.addEventListener('click', handleNavigation);
});

renderIngestionSummary(null);
renderResults(null);
