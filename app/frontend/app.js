/* ═══════════════════════════════════════════════════════════════
   NovelForge AI — Application Logic
   Pure Vanilla JS  |  No external dependencies
   ═══════════════════════════════════════════════════════════════ */

const API = 'http://127.0.0.1:8000/api';

// ─────────────────────────────────────────────
// APPLICATION STATE
// ─────────────────────────────────────────────
const state = {
  characters: [],
  scenes: [],
  world: {},
  chapters: [],
  novelMeta: {},
  currentChapter: null,
  isGenerating: false,
  activeModal: null,
  // Tag input data stores
  _abilities: [],
  _habits: [],
  _inhabitants: [],
  _genreTags: [],
  _professions: [],
  _hierarchy: [],
  _factions: [],
  // Relationship editor
  _relationships: {},
  // Profile view context
  _profileContext: null,
  _editingCharSlug: null,
  _editingSceneSlug: null,
};

// ─────────────────────────────────────────────
// DOM REFERENCES (cached)
// ─────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const $$ = (sel, root = document) => root.querySelectorAll(sel);

const DOM = {
  // Header
  novelTitleWrapper: $('novel-title-wrapper'),
  novelTitleDisplay: $('novel-title-display'),
  novelTitleInput:   $('novel-title-input'),
  chapterCount:      $('chapter-count'),
  btnSettings:       $('btn-settings'),
  btnExport:         $('btn-export'),
  exportDropdown:    $('export-dropdown'),
  exportTxt:         $('export-txt'),
  exportMd:          $('export-md'),

  // Sidebar - Characters
  mainCastList:      $('main-cast-list'),
  supportingCastList:$('supporting-cast-list'),
  mainCastEmpty:     $('main-cast-empty'),
  supportingCastEmpty:$('supporting-cast-empty'),
  charCountBadge:    $('char-count-badge'),
  btnAddCharacter:   $('btn-add-character'),

  // Sidebar - Scenes
  scenesList:        $('scenes-list'),
  scenesEmpty:       $('scenes-empty'),
  sceneCountBadge:   $('scene-count-badge'),
  btnAddScene:       $('btn-add-scene'),
  btnWorld:          $('btn-world'),

  // Center - Plot
  chapterNumLabel:   $('chapter-num-label'),
  nextChapterHint:   $('next-chapter-hint'),
  plotInput:         $('plot-input'),
  btnGenerate:       $('btn-generate'),

  // Center - Pipeline
  pipelineSection:   $('pipeline-section'),
  pipelineProgressFill: $('pipeline-progress-fill'),
  newEntities:       $('new-entities'),

  // Center - Output
  outputSection:     $('output-section'),
  outputChapterBadge:$('output-chapter-badge'),
  outputChapterTitle:$('output-chapter-title'),
  wordCountNum:      $('word-count-num'),
  chapterTextArea:   $('chapter-text-area'),
  textCursor:        $('text-cursor'),
  btnViewFull:       $('btn-view-full'),
  multiChapterNotice:$('multi-chapter-notice'),
  multiChapterMessage:$('multi-chapter-message'),

  // History
  historyPills:      $('history-pills'),
  historyEmpty:      $('history-empty'),

  // Toast
  toastContainer:    $('toast-container'),
};

// ─────────────────────────────────────────────
// INITIALIZATION
// ─────────────────────────────────────────────
async function init() {
  console.log('[NovelForge] Initializing...');
  bindStaticEvents();
  await Promise.allSettled([
    loadNovelMeta(),
    loadCharacters(),
    loadScenes(),
    loadWorld(),
    loadChapters(),
  ]);
  updateChapterHint();
  console.log('[NovelForge] Ready.');
}

// ─────────────────────────────────────────────
// API HELPERS
// ─────────────────────────────────────────────
async function apiGet(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status} ${res.statusText}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} failed: ${res.status} — ${text}`);
  }
  return res;
}

async function apiPut(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`PUT ${path} failed: ${res.status} — ${text}`);
  }
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(`${API}${path}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
// LOAD & RENDER — NOVEL META
// ─────────────────────────────────────────────
async function loadNovelMeta() {
  try {
    state.novelMeta = await apiGet('/novel-meta');
    renderNovelMeta();
  } catch (e) {
    console.warn('[NovelForge] Could not load novel meta:', e.message);
    state.novelMeta = {
      title: 'Untitled Novel',
      genre: '',
      author: '',
      total_chapters: 0,
      writer_model: 'gemma3:12b',
      specialist_model: 'gemma3:12b',
    };
  }
}

function renderNovelMeta() {
  const meta = state.novelMeta;
  if (meta.title) {
    DOM.novelTitleDisplay.textContent = meta.title;
    document.title = `${meta.title} — NovelForge AI`;
  }
}

// ─────────────────────────────────────────────
// LOAD & RENDER — CHARACTERS
// ─────────────────────────────────────────────
async function loadCharacters() {
  try {
    state.characters = await apiGet('/characters');
    renderCharacters();
  } catch (e) {
    console.warn('[NovelForge] Could not load characters:', e.message);
    state.characters = [];
  }
}

function renderCharacters() {
  const chars = state.characters;
  const main = chars.filter(c => c.type === 'main');
  const temp = chars.filter(c => c.type !== 'main');

  DOM.charCountBadge.textContent = chars.length;

  renderCardList(DOM.mainCastList, main, DOM.mainCastEmpty, 'character');
  renderCardList(DOM.supportingCastList, temp, DOM.supportingCastEmpty, 'character');
}

function renderCardList(container, items, emptyEl, type) {
  // Clear existing cards (keep empty state)
  Array.from(container.children).forEach(child => {
    if (child !== emptyEl) child.remove();
  });

  if (items.length === 0) {
    emptyEl.style.display = '';
    return;
  }
  emptyEl.style.display = 'none';

  items.forEach((item, i) => {
    const card = createEntityCard(item, type);
    card.style.animationDelay = `${i * 50}ms`;
    container.appendChild(card);
  });
}

function createEntityCard(item, type) {
  const isChar = type === 'character';
  const card = document.createElement('div');
  card.className = `entity-card ${isChar ? '' : 'card-gold'}`;
  card.dataset.slug = item.slug;
  card.dataset.type = type;

  const badgeClass = isChar
    ? (item.type === 'main' ? 'badge-main' : 'badge-temp')
    : 'badge-scene';
  const badgeText = isChar
    ? (item.type === 'main' ? 'MAIN' : 'TEMP')
    : (item.scene_type || 'LOCATION');

  const metaText = isChar
    ? `Ch. ${item.first_appeared_chapter ?? '?'} — ${item.last_seen_chapter ?? '?'}`
    : `First: Ch. ${item.first_appeared_chapter ?? '?'}`;

  card.innerHTML = `
    <div class="card-header-row">
      <div class="card-name">${escHtml(item.name)}</div>
      <span class="type-badge ${badgeClass}">${escHtml(badgeText)}</span>
    </div>
    <div class="card-summary">${escHtml(item.micro_summary || '—')}</div>
    <div class="card-meta">${metaText}</div>
    <div class="card-actions">
      <button class="btn-card" data-action="view" aria-label="View ${escHtml(item.name)}">View</button>
      <button class="btn-card" data-action="edit" aria-label="Edit ${escHtml(item.name)}">Edit</button>
      <button class="btn-card btn-card-delete" data-action="delete" aria-label="Delete ${escHtml(item.name)}">Delete</button>
    </div>
  `;

  card.addEventListener('click', (e) => {
    const action = e.target.dataset.action;
    if (action === 'edit') {
      e.stopPropagation();
      isChar ? openCharacterModal(item.slug) : openSceneModal(item.slug);
    } else if (action === 'delete') {
      e.stopPropagation();
      isChar ? deleteCharacter(item.slug, item.name) : deleteScene(item.slug, item.name);
    } else if (action === 'view') {
      e.stopPropagation();
      isChar ? viewCharacterProfile(item.slug) : viewSceneProfile(item.slug);
    } else {
      isChar ? viewCharacterProfile(item.slug) : viewSceneProfile(item.slug);
    }
  });

  return card;
}

// ─────────────────────────────────────────────
// LOAD & RENDER — SCENES
// ─────────────────────────────────────────────
async function loadScenes() {
  try {
    state.scenes = await apiGet('/scenes');
    renderScenes();
  } catch (e) {
    console.warn('[NovelForge] Could not load scenes:', e.message);
    state.scenes = [];
  }
}

function renderScenes() {
  const scenes = state.scenes;
  DOM.sceneCountBadge.textContent = scenes.length;
  renderCardList(DOM.scenesList, scenes, DOM.scenesEmpty, 'scene');
}

// ─────────────────────────────────────────────
// LOAD & RENDER — WORLD
// ─────────────────────────────────────────────
async function loadWorld() {
  try {
    state.world = await apiGet('/world');
  } catch (e) {
    console.warn('[NovelForge] Could not load world settings:', e.message);
    state.world = {};
  }
}

// ─────────────────────────────────────────────
// LOAD & RENDER — CHAPTERS
// ─────────────────────────────────────────────
async function loadChapters() {
  try {
    state.chapters = await apiGet('/chapters');
    renderChapterHistory();
    updateChapterHint();
  } catch (e) {
    console.warn('[NovelForge] Could not load chapters:', e.message);
    state.chapters = [];
  }
}

function renderChapterHistory() {
  const chapters = state.chapters;
  DOM.chapterCount.textContent = chapters.length;

  // Clear existing pills
  Array.from(DOM.historyPills.children).forEach(c => {
    if (c !== DOM.historyEmpty) c.remove();
  });

  if (chapters.length === 0) {
    DOM.historyEmpty.style.display = '';
    return;
  }
  DOM.historyEmpty.style.display = 'none';

  chapters.forEach((ch, i) => {
    const pill = document.createElement('button');
    pill.className = 'chapter-pill';
    pill.textContent = `Ch. ${ch.chapter_number}`;
    pill.title = ch.title || `Chapter ${ch.chapter_number}`;
    pill.setAttribute('role', 'listitem');
    pill.dataset.chapterNum = ch.chapter_number;
    pill.style.animationDelay = `${i * 30}ms`;

    if (state.currentChapter && state.currentChapter.chapter_number === ch.chapter_number) {
      pill.classList.add('active');
    }

    pill.addEventListener('click', () => viewChapter(ch.chapter_number));
    DOM.historyPills.appendChild(pill);
  });
}

function updateChapterHint() {
  const nextNum = (state.chapters.length || 0) + 1;
  DOM.chapterNumLabel.textContent = `CHAPTER ${nextNum}`;
  DOM.nextChapterHint.textContent = `Will generate Chapter ${nextNum}`;
}

// ─────────────────────────────────────────────
// VIEW CHAPTER
// ─────────────────────────────────────────────
async function viewChapter(number) {
  try {
    showToast(`Loading Chapter ${number}…`, 'info');
    const chapter = await apiGet(`/chapters/${number}`);
    state.currentChapter = chapter;

    // Update pill highlighting
    $$('.chapter-pill').forEach(p => {
      p.classList.toggle('active', parseInt(p.dataset.chapterNum) === number);
    });

    // Show chapter in output section
    showChapterOutput(chapter);
    showToast(`Chapter ${number}: ${chapter.title}`, 'success');
  } catch (e) {
    showToast(`Failed to load chapter ${number}: ${e.message}`, 'error');
  }
}

function showChapterOutput(chapter) {
  DOM.outputSection.hidden = false;
  DOM.outputChapterBadge.textContent = `Chapter ${chapter.chapter_number}`;
  DOM.outputChapterTitle.textContent = chapter.title || '—';
  DOM.wordCountNum.textContent = (chapter.word_count || 0).toLocaleString();

  // Format text as paragraphs
  DOM.chapterTextArea.innerHTML = '';
  if (chapter.full_text) {
    formatChapterText(DOM.chapterTextArea, chapter.full_text);
  }
  DOM.textCursor.hidden = true;

  DOM.outputSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function formatChapterText(container, text) {
  const paragraphs = text.split(/\n\n+/);
  paragraphs.forEach(para => {
    if (para.trim()) {
      const p = document.createElement('p');
      p.textContent = para.trim();
      container.appendChild(p);
    }
  });
}

// ─────────────────────────────────────────────
// GENERATE CHAPTER — MAIN FUNCTION
// ─────────────────────────────────────────────
async function generateChapter() {
  const plot = DOM.plotInput.value.trim();
  if (!plot) {
    showToast('Please describe what happens in this chapter.', 'error');
    DOM.plotInput.focus();
    return;
  }
  if (state.isGenerating) return;

  state.isGenerating = true;
  DOM.btnGenerate.disabled = true;
  DOM.btnGenerate.querySelector('.generate-text').textContent = 'Generating...';

  // Reset & show pipeline
  resetPipeline();
  DOM.pipelineSection.hidden = false;
  DOM.outputSection.hidden = true;
  DOM.multiChapterNotice.hidden = true;
  DOM.newEntities.innerHTML = '';

  // Prepare chapter number
  const chapterNumber = state.chapters.length + 1;
  const body = { plot, chapter_number: chapterNumber };

  let streamedText = '';
  let currentParagraph = null;

  try {
    const response = await fetch(`${API}/generate-chapter`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${response.statusText}`);
    }

    // Show output section with cursor as text streams
    DOM.outputSection.hidden = false;
    DOM.outputChapterBadge.textContent = `Chapter ${chapterNumber}`;
    DOM.outputChapterTitle.textContent = 'Writing...';
    DOM.chapterTextArea.innerHTML = '';
    DOM.textCursor.hidden = false;

    await parseSSEStream(response, {
      status: (data) => {
        const step = data.step;
        if (step) {
          activatePipelineStep(step, data.message || '');
          updateProgress(step);
        }
      },

      new_character: (data) => {
        addNewEntityTag('character', data.name);
        // Reload characters sidebar after a short delay
        setTimeout(loadCharacters, 300);
        showToast(`New character discovered: ${data.name}`, 'info');
      },

      new_scene: (data) => {
        addNewEntityTag('scene', data.name);
        setTimeout(loadScenes, 300);
        showToast(`New location discovered: ${data.name}`, 'info');
      },

      token: (data) => {
        const content = data.content || '';
        streamedText += content;

        // Smart paragraph splitting: detect double newlines
        if (content.includes('\n\n')) {
          // Finalize current paragraph, start new one
          if (currentParagraph) {
            const parts = streamedText.split('\n\n');
            currentParagraph.textContent = parts[0].trim();
            // Move cursor to new paragraph
            for (let i = 1; i < parts.length - 1; i++) {
              const p = document.createElement('p');
              p.textContent = parts[i].trim();
              DOM.chapterTextArea.appendChild(p);
            }
            currentParagraph = document.createElement('p');
            currentParagraph.textContent = parts[parts.length - 1];
            DOM.chapterTextArea.appendChild(currentParagraph);
            streamedText = parts[parts.length - 1];
          }
        } else {
          if (!currentParagraph) {
            currentParagraph = document.createElement('p');
            DOM.chapterTextArea.appendChild(currentParagraph);
          }
          // Append content to current paragraph (before cursor)
          currentParagraph.textContent = (currentParagraph.textContent || '') + content;
        }

        // Keep cursor at end (append after last element)
        DOM.chapterTextArea.appendChild(DOM.textCursor);
        DOM.textCursor.hidden = false;
        DOM.textCursor.scrollIntoView({ block: 'nearest' });
      },

      complete: async (data) => {
        completePipeline();
        DOM.textCursor.hidden = true;
        DOM.outputChapterTitle.textContent = data.title || `Chapter ${data.chapter_number}`;
        DOM.wordCountNum.textContent = (data.word_count || 0).toLocaleString();
        state.currentChapter = {
          chapter_number: data.chapter_number,
          title: data.title,
          word_count: data.word_count,
        };
        await loadChapters();
        showToast(`✓ Chapter ${data.chapter_number} complete — ${data.word_count?.toLocaleString()} words`, 'success');
        DOM.plotInput.value = '';
      },

      multi_chapter: (data) => {
        DOM.multiChapterNotice.hidden = false;
        DOM.multiChapterMessage.textContent = data.message || `Plot may span ${data.estimated} chapters`;
        showToast(data.message || 'Plot may span multiple chapters', 'warning');
      },

      error: (data) => {
        showToast(`Generation error: ${data.message}`, 'error');
        DOM.textCursor.hidden = true;
        setStepError();
      },
    });

  } catch (e) {
    showToast(`Failed to generate chapter: ${e.message}`, 'error');
    console.error('[NovelForge] Generation error:', e);
    DOM.textCursor.hidden = true;
    setStepError();
  } finally {
    state.isGenerating = false;
    DOM.btnGenerate.disabled = false;
    DOM.btnGenerate.querySelector('.generate-text').textContent = 'Generate Chapter';
  }
}

// ─────────────────────────────────────────────
// SSE STREAM PARSER
// ─────────────────────────────────────────────
async function parseSSEStream(response, handlers) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Keep incomplete line in buffer

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('data: ')) {
        try {
          const jsonStr = trimmed.slice(6);
          if (jsonStr === '[DONE]') continue;
          const data = JSON.parse(jsonStr);
          if (data.type && handlers[data.type]) {
            handlers[data.type](data);
          }
        } catch (e) {
          // Ignore malformed JSON lines
        }
      }
    }
  }

  // Process any remaining buffer content
  if (buffer.trim().startsWith('data: ')) {
    try {
      const data = JSON.parse(buffer.trim().slice(6));
      if (data.type && handlers[data.type]) {
        handlers[data.type](data);
      }
    } catch (e) {}
  }
}

// ─────────────────────────────────────────────
// PIPELINE CONTROL
// ─────────────────────────────────────────────
function resetPipeline() {
  for (let i = 1; i <= 7; i++) {
    const step = $(`step-${i}`);
    if (!step) continue;
    step.classList.remove('step-is-active', 'step-is-done');
    step.querySelector('.step-pending').hidden = false;
    step.querySelector('.step-active').hidden = true;
    step.querySelector('.step-done').hidden = true;
    const log = $(`step-${i}-log`);
    if (log) log.textContent = '';
  }
  DOM.pipelineProgressFill.style.width = '0%';
}

function activatePipelineStep(stepNum, message) {
  // Mark previous step as done
  if (stepNum > 1) {
    completePipelineStep(stepNum - 1);
  }

  const step = $(`step-${stepNum}`);
  if (!step) return;

  step.classList.remove('step-is-done');
  step.classList.add('step-is-active');
  step.querySelector('.step-pending').hidden = true;
  step.querySelector('.step-active').hidden = false;
  step.querySelector('.step-done').hidden = true;

  const log = $(`step-${stepNum}-log`);
  if (log && message) log.textContent = message;

  step.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function completePipelineStep(stepNum) {
  const step = $(`step-${stepNum}`);
  if (!step) return;
  step.classList.remove('step-is-active');
  step.classList.add('step-is-done');
  step.querySelector('.step-pending').hidden = true;
  step.querySelector('.step-active').hidden = true;
  step.querySelector('.step-done').hidden = false;
}

function completePipeline() {
  for (let i = 1; i <= 7; i++) {
    completePipelineStep(i);
  }
  DOM.pipelineProgressFill.style.width = '100%';

  // Fade out pipeline after a moment
  setTimeout(() => {
    DOM.pipelineSection.style.opacity = '0.4';
  }, 2000);
}

function updateProgress(step) {
  const percent = Math.round((step / 7) * 100);
  DOM.pipelineProgressFill.style.width = `${percent}%`;
}

function setStepError() {
  // Mark any active step as errored
  for (let i = 1; i <= 7; i++) {
    const step = $(`step-${i}`);
    if (step && step.classList.contains('step-is-active')) {
      step.classList.remove('step-is-active');
      step.style.borderColor = 'rgba(255,79,106,0.5)';
      step.style.background = 'rgba(255,79,106,0.08)';
    }
  }
}

function addNewEntityTag(entityType, name) {
  const tag = document.createElement('div');
  tag.className = `new-entity-tag ${entityType === 'character' ? 'new-entity-char' : 'new-entity-scene'}`;
  tag.innerHTML = `
    <span>${entityType === 'character' ? '👤' : '📍'}</span>
    <span>${escHtml(name)}</span>
  `;
  DOM.newEntities.appendChild(tag);
}

// ─────────────────────────────────────────────
// CHARACTER MODAL
// ─────────────────────────────────────────────
function openCharacterModal(slug = null) {
  state._editingCharSlug = slug;
  state._abilities = [];
  state._habits = [];
  state._relationships = {};

  const char = slug ? state.characters.find(c => c.slug === slug) : null;

  $('char-modal-title').textContent = char ? 'Edit Character' : 'New Character';
  $('char-name').value          = char?.name || '';
  $('char-type').value          = char?.type || 'main';
  $('char-age').value           = char?.age || '';
  $('char-cultivation').value   = char?.cultivation_level || '';
  $('char-appearance').value    = char?.appearance || '';
  $('char-personality').value   = char?.personality || '';
  $('char-speech').value        = char?.speech_style || '';
  $('char-backstory').value     = char?.backstory || '';
  $('char-arc').value           = char?.arc_notes || '';
  $('char-micro').value         = char?.micro_summary || '';

  // Init tag inputs
  initTagInput('abilities-input', 'abilities-tags', char?.abilities || [], '_abilities');
  initTagInput('habits-input', 'habits-tags', char?.habits || [], '_habits');

  // Init relationships
  state._relationships = { ...(char?.relationships || {}) };
  renderRelationships();

  openModal('modal-character');
}

async function saveCharacter() {
  const name = $('char-name').value.trim();
  if (!name) { showToast('Character name is required.', 'error'); return; }

  const character = {
    name,
    type:              $('char-type').value,
    age:               $('char-age').value.trim() || null,
    appearance:        $('char-appearance').value.trim(),
    personality:       $('char-personality').value.trim(),
    speech_style:      $('char-speech').value.trim(),
    abilities:         [...state._abilities],
    cultivation_level: $('char-cultivation').value.trim() || null,
    backstory:         $('char-backstory').value.trim(),
    relationships:     { ...state._relationships },
    habits:            [...state._habits],
    arc_notes:         $('char-arc').value.trim(),
    micro_summary:     $('char-micro').value.trim(),
  };

  const btn = $('btn-save-character');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  try {
    if (state._editingCharSlug) {
      await apiPut(`/characters/${state._editingCharSlug}`, { character });
      showToast(`Character "${name}" updated.`, 'success');
    } else {
      const res = await apiPost('/characters', { character });
      if (!res.ok) throw new Error('Create failed');
      showToast(`Character "${name}" created.`, 'success');
    }
    closeModal('modal-character');
    await loadCharacters();
  } catch (e) {
    showToast(`Failed to save character: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Character';
  }
}

async function deleteCharacter(slug, name) {
  if (!confirm(`Delete character "${name}"? This cannot be undone.`)) return;
  try {
    await apiDelete(`/characters/${slug}`);
    showToast(`Character "${name}" deleted.`, 'success');
    await loadCharacters();
  } catch (e) {
    showToast(`Failed to delete: ${e.message}`, 'error');
  }
}

function viewCharacterProfile(slug) {
  const char = state.characters.find(c => c.slug === slug);
  if (!char) return;

  state._profileContext = { type: 'character', slug };
  $('profile-modal-title').textContent = char.name;

  const body = $('profile-modal-body');
  body.innerHTML = `
    <div class="profile-section">
      <div class="profile-section-title">IDENTITY</div>
      <div class="profile-field"><span class="profile-field-label">Type</span><span class="profile-field-value"><span class="type-badge ${char.type === 'main' ? 'badge-main' : 'badge-temp'}">${char.type === 'main' ? 'MAIN' : 'TEMPORARY'}</span></span></div>
      <div class="profile-field"><span class="profile-field-label">Age</span><span class="profile-field-value">${escHtml(char.age || '—')}</span></div>
      <div class="profile-field"><span class="profile-field-label">Cultivation</span><span class="profile-field-value">${escHtml(char.cultivation_level || '—')}</span></div>
      <div class="profile-field"><span class="profile-field-label">Chapters</span><span class="profile-field-value font-mono">First: ${char.first_appeared_chapter ?? '?'} · Last: ${char.last_seen_chapter ?? '?'}</span></div>
    </div>
    <div class="profile-section">
      <div class="profile-section-title">APPEARANCE & PERSONALITY</div>
      <div class="profile-field"><span class="profile-field-label">Appearance</span><span class="profile-field-value">${escHtml(char.appearance || '—')}</span></div>
      <div class="profile-field"><span class="profile-field-label">Personality</span><span class="profile-field-value">${escHtml(char.personality || '—')}</span></div>
      <div class="profile-field"><span class="profile-field-label">Speech Style</span><span class="profile-field-value">${escHtml(char.speech_style || '—')}</span></div>
    </div>
    ${char.abilities?.length ? `
    <div class="profile-section">
      <div class="profile-section-title">ABILITIES</div>
      <div class="profile-tags">${char.abilities.map(a => `<span class="type-badge badge-main">${escHtml(a)}</span>`).join('')}</div>
    </div>` : ''}
    ${char.habits?.length ? `
    <div class="profile-section">
      <div class="profile-section-title">HABITS</div>
      <div class="profile-tags">${char.habits.map(h => `<span class="type-badge badge-temp">${escHtml(h)}</span>`).join('')}</div>
    </div>` : ''}
    ${char.backstory ? `
    <div class="profile-section">
      <div class="profile-section-title">BACKSTORY</div>
      <div class="profile-field-value">${escHtml(char.backstory)}</div>
    </div>` : ''}
    ${char.arc_notes ? `
    <div class="profile-section">
      <div class="profile-section-title">ARC NOTES</div>
      <div class="profile-field-value">${escHtml(char.arc_notes)}</div>
    </div>` : ''}
    ${Object.keys(char.relationships || {}).length ? `
    <div class="profile-section">
      <div class="profile-section-title">RELATIONSHIPS</div>
      ${Object.entries(char.relationships).map(([name, rel]) =>
        `<div class="profile-field"><span class="profile-field-label">${escHtml(name)}</span><span class="profile-field-value">${escHtml(rel)}</span></div>`
      ).join('')}
    </div>` : ''}
  `;

  $('btn-edit-profile').onclick = () => {
    closeModal('modal-profile');
    openCharacterModal(slug);
  };

  openModal('modal-profile');
}

// ─────────────────────────────────────────────
// SCENE MODAL
// ─────────────────────────────────────────────
function openSceneModal(slug = null) {
  state._editingSceneSlug = slug;
  state._inhabitants = [];

  const scene = slug ? state.scenes.find(s => s.slug === slug) : null;

  $('scene-modal-title').textContent = scene ? 'Edit Location' : 'New Location';
  $('scene-name').value        = scene?.name || '';
  $('scene-type').value        = scene?.scene_type || '';
  $('scene-description').value = scene?.description || '';
  $('scene-atmosphere').value  = scene?.atmosphere || '';
  $('scene-textures').value    = scene?.textures || '';
  $('scene-significance').value= scene?.significance || '';
  $('scene-micro').value       = scene?.micro_summary || '';

  initTagInput('inhabitants-input', 'inhabitants-tags', scene?.known_inhabitants || [], '_inhabitants');
  openModal('modal-scene');
}

async function saveScene() {
  const name = $('scene-name').value.trim();
  if (!name) { showToast('Location name is required.', 'error'); return; }

  const scene = {
    name,
    scene_type:         $('scene-type').value.trim(),
    description:        $('scene-description').value.trim(),
    atmosphere:         $('scene-atmosphere').value.trim(),
    textures:           $('scene-textures').value.trim(),
    known_inhabitants:  [...state._inhabitants],
    significance:       $('scene-significance').value.trim(),
    micro_summary:      $('scene-micro').value.trim(),
  };

  const btn = $('btn-save-scene');
  btn.disabled = true;
  btn.textContent = 'Saving...';

  try {
    if (state._editingSceneSlug) {
      await apiPut(`/scenes/${state._editingSceneSlug}`, { scene });
      showToast(`Location "${name}" updated.`, 'success');
    } else {
      const res = await apiPost('/scenes', { scene });
      if (!res.ok) throw new Error('Create failed');
      showToast(`Location "${name}" created.`, 'success');
    }
    closeModal('modal-scene');
    await loadScenes();
  } catch (e) {
    showToast(`Failed to save location: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Location';
  }
}

async function deleteScene(slug, name) {
  if (!confirm(`Delete location "${name}"? This cannot be undone.`)) return;
  try {
    await apiDelete(`/scenes/${slug}`);
    showToast(`Location "${name}" deleted.`, 'success');
    await loadScenes();
  } catch (e) {
    showToast(`Failed to delete: ${e.message}`, 'error');
  }
}

function viewSceneProfile(slug) {
  const scene = state.scenes.find(s => s.slug === slug);
  if (!scene) return;

  state._profileContext = { type: 'scene', slug };
  $('profile-modal-title').textContent = scene.name;

  const body = $('profile-modal-body');
  body.innerHTML = `
    <div class="profile-section">
      <div class="profile-section-title">OVERVIEW</div>
      <div class="profile-field"><span class="profile-field-label">Type</span><span class="profile-field-value"><span class="type-badge badge-scene">${escHtml(scene.scene_type || 'LOCATION')}</span></span></div>
      <div class="profile-field"><span class="profile-field-label">First Ch.</span><span class="profile-field-value">${scene.first_appeared_chapter ?? '—'}</span></div>
      <div class="profile-field"><span class="profile-field-label">Summary</span><span class="profile-field-value">${escHtml(scene.micro_summary || '—')}</span></div>
    </div>
    ${scene.description ? `
    <div class="profile-section">
      <div class="profile-section-title">DESCRIPTION</div>
      <div class="profile-field-value">${escHtml(scene.description)}</div>
    </div>` : ''}
    ${scene.atmosphere ? `
    <div class="profile-section">
      <div class="profile-section-title">ATMOSPHERE</div>
      <div class="profile-field-value">${escHtml(scene.atmosphere)}</div>
    </div>` : ''}
    ${scene.textures ? `
    <div class="profile-section">
      <div class="profile-section-title">TEXTURES & DETAILS</div>
      <div class="profile-field-value">${escHtml(scene.textures)}</div>
    </div>` : ''}
    ${scene.known_inhabitants?.length ? `
    <div class="profile-section">
      <div class="profile-section-title">KNOWN INHABITANTS</div>
      <div class="profile-tags">${scene.known_inhabitants.map(i => `<span class="type-badge badge-main">${escHtml(i)}</span>`).join('')}</div>
    </div>` : ''}
    ${scene.significance ? `
    <div class="profile-section">
      <div class="profile-section-title">SIGNIFICANCE</div>
      <div class="profile-field-value">${escHtml(scene.significance)}</div>
    </div>` : ''}
  `;

  $('btn-edit-profile').onclick = () => {
    closeModal('modal-profile');
    openSceneModal(slug);
  };

  openModal('modal-profile');
}

// ─────────────────────────────────────────────
// WORLD SETTINGS MODAL
// ─────────────────────────────────────────────
function openWorldModal() {
  const w = state.world || {};
  $('world-name').value       = w.world_name || '';
  $('world-magic').value      = w.magic_system || '';
  $('world-cultivation').value= w.cultivation_system || '';
  $('world-rules').value      = w.rules_of_the_world || '';
  $('world-lore').value       = w.lore_notes || '';

  state._genreTags   = [...(w.genre_tags || [])];
  state._professions = [...(w.professions || [])];
  state._hierarchy   = [...(w.hierarchy_levels || [])];
  state._factions    = [...(w.factions || [])];

  initTagInput('genre-tags-field', 'genre-tags', state._genreTags, '_genreTags');
  initTagInput('professions-input', 'professions-tags', state._professions, '_professions');
  initTagInput('hierarchy-input', 'hierarchy-tags', state._hierarchy, '_hierarchy');
  initTagInput('factions-input', 'factions-tags', state._factions, '_factions');

  openModal('modal-world');
}

async function saveWorld() {
  const settings = {
    world_name:         $('world-name').value.trim(),
    genre_tags:         [...state._genreTags],
    magic_system:       $('world-magic').value.trim(),
    cultivation_system: $('world-cultivation').value.trim(),
    professions:        [...state._professions],
    hierarchy_levels:   [...state._hierarchy],
    factions:           [...state._factions],
    rules_of_the_world: $('world-rules').value.trim(),
    lore_notes:         $('world-lore').value.trim(),
  };

  const btn = $('btn-save-world');
  btn.disabled = true; btn.textContent = 'Saving...';

  try {
    await apiPut('/world', { settings });
    state.world = settings;
    showToast('World settings saved.', 'success');
    closeModal('modal-world');
  } catch (e) {
    showToast(`Failed to save world: ${e.message}`, 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Save World Settings';
  }
}

// ─────────────────────────────────────────────
// NOVEL SETTINGS MODAL
// ─────────────────────────────────────────────
function openSettingsModal() {
  const m = state.novelMeta || {};
  $('meta-title').value           = m.title || '';
  $('meta-genre').value           = m.genre || '';
  $('meta-author').value          = m.author || '';
  $('meta-writer-model').value    = m.writer_model || 'gemma3:12b';
  $('meta-specialist-model').value= m.specialist_model || 'gemma3:12b';
  openModal('modal-settings');
}

async function saveSettings() {
  const meta = {
    title:            $('meta-title').value.trim(),
    genre:            $('meta-genre').value.trim(),
    author:           $('meta-author').value.trim(),
    writer_model:     $('meta-writer-model').value,
    specialist_model: $('meta-specialist-model').value,
  };

  const btn = $('btn-save-settings');
  btn.disabled = true; btn.textContent = 'Saving...';

  try {
    await apiPut('/novel-meta', { meta });
    state.novelMeta = { ...state.novelMeta, ...meta };
    renderNovelMeta();
    showToast('Settings saved.', 'success');
    closeModal('modal-settings');
  } catch (e) {
    showToast(`Failed to save settings: ${e.message}`, 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Save Settings';
  }
}

// ─────────────────────────────────────────────
// CHAPTER FULL VIEW MODAL
// ─────────────────────────────────────────────
function openChapterViewModal() {
  if (!state.currentChapter) return;
  const ch = state.currentChapter;

  $('view-chapter-badge').textContent = `Chapter ${ch.chapter_number}`;
  $('chapter-modal-title').textContent = ch.title || `Chapter ${ch.chapter_number}`;
  $('view-word-count').textContent = `${(ch.word_count || 0).toLocaleString()} words`;

  // Featured characters & scenes
  const charTags = $('view-char-tags');
  const sceneTags = $('view-scene-tags');
  charTags.innerHTML = '';
  sceneTags.innerHTML = '';

  (ch.characters_featured || []).forEach(name => {
    const tag = document.createElement('span');
    tag.className = 'featured-tag';
    tag.textContent = name;
    charTags.appendChild(tag);
  });

  (ch.scenes_featured || []).forEach(name => {
    const tag = document.createElement('span');
    tag.className = 'featured-tag';
    tag.style.background = 'rgba(245,200,66,0.1)';
    tag.style.borderColor = 'rgba(245,200,66,0.25)';
    tag.style.color = 'var(--gold)';
    tag.textContent = name;
    sceneTags.appendChild(tag);
  });

  // Text
  const viewText = $('chapter-view-text');
  viewText.innerHTML = '';

  // Try to use current text from output area, or fetch
  const currentText = DOM.chapterTextArea.innerHTML;
  if (currentText) {
    viewText.innerHTML = currentText;
  } else if (ch.full_text) {
    formatChapterText(viewText, ch.full_text);
  } else {
    // Fetch chapter text
    apiGet(`/chapters/${ch.chapter_number}`).then(fullCh => {
      if (fullCh.full_text) formatChapterText(viewText, fullCh.full_text);
    }).catch(() => {
      viewText.innerHTML = '<p style="color:var(--text-muted);font-style:italic;">Chapter text unavailable.</p>';
    });
  }

  openModal('modal-chapter');
}

// ─────────────────────────────────────────────
// EXPORT
// ─────────────────────────────────────────────
function exportNovel(format) {
  const url = `${API}/export/${format}`;
  const a = document.createElement('a');
  a.href = url;
  a.download = `novel.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast(`Exporting novel as .${format}…`, 'info');
}

// ─────────────────────────────────────────────
// MODAL SYSTEM
// ─────────────────────────────────────────────
function openModal(id) {
  // Close any open modal first
  if (state.activeModal && state.activeModal !== id) closeModal(state.activeModal);
  state.activeModal = id;
  const overlay = $(id);
  if (!overlay) return;
  overlay.hidden = false;
  overlay.removeAttribute('aria-hidden');
  document.body.style.overflow = 'hidden';

  // Focus first focusable element
  const focusable = overlay.querySelector('input, select, textarea, button:not(.modal-close)');
  if (focusable) setTimeout(() => focusable.focus(), 50);
}

function closeModal(id) {
  const overlay = $(id);
  if (!overlay) return;
  overlay.hidden = true;
  overlay.setAttribute('aria-hidden', 'true');
  if (state.activeModal === id) state.activeModal = null;
  document.body.style.overflow = '';
}

// ─────────────────────────────────────────────
// TAG INPUT COMPONENT
// ─────────────────────────────────────────────
function initTagInput(inputId, displayId, initialTags, stateKey) {
  const input = $(inputId);
  const display = $(displayId);
  if (!input || !display) return;

  state[stateKey] = [...initialTags];
  renderTags(display, stateKey);

  // Remove existing listeners by cloning
  const newInput = input.cloneNode(true);
  input.parentNode.replaceChild(newInput, input);

  newInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const val = newInput.value.trim().replace(/,$/, '');
      if (val && !state[stateKey].includes(val)) {
        state[stateKey].push(val);
        renderTags(display, stateKey);
      }
      newInput.value = '';
    } else if (e.key === 'Backspace' && newInput.value === '' && state[stateKey].length) {
      state[stateKey].pop();
      renderTags(display, stateKey);
    }
  });

  // Focus input when clicking wrapper
  const wrapper = newInput.closest('.tag-input-wrapper');
  if (wrapper) {
    wrapper.addEventListener('click', () => newInput.focus());
  }
}

function renderTags(display, stateKey) {
  display.innerHTML = '';
  state[stateKey].forEach((tag, idx) => {
    const pill = document.createElement('span');
    pill.className = 'tag-pill';
    pill.innerHTML = `${escHtml(tag)}<span class="tag-remove" data-idx="${idx}" tabindex="0" role="button" aria-label="Remove ${escHtml(tag)}">×</span>`;

    pill.querySelector('.tag-remove').addEventListener('click', (e) => {
      e.stopPropagation();
      state[stateKey].splice(idx, 1);
      renderTags(display, stateKey);
    });

    display.appendChild(pill);
  });
}

// ─────────────────────────────────────────────
// RELATIONSHIP EDITOR
// ─────────────────────────────────────────────
function renderRelationships() {
  const list = $('relationships-list');
  if (!list) return;
  list.innerHTML = '';

  Object.entries(state._relationships).forEach(([name, desc]) => {
    const row = document.createElement('div');
    row.className = 'relationship-row';
    row.innerHTML = `
      <span class="rel-name-label">${escHtml(name)}</span>
      <span class="rel-desc-label">${escHtml(desc)}</span>
      <button class="btn-rel-delete" data-rel="${escHtml(name)}" aria-label="Remove relationship with ${escHtml(name)}">✕</button>
    `;
    row.querySelector('.btn-rel-delete').addEventListener('click', (e) => {
      const relName = e.target.dataset.rel;
      delete state._relationships[relName];
      renderRelationships();
    });
    list.appendChild(row);
  });
}

// ─────────────────────────────────────────────
// NOVEL TITLE INLINE EDIT
// ─────────────────────────────────────────────
function initTitleEdit() {
  const wrapper = DOM.novelTitleWrapper;
  const display = DOM.novelTitleDisplay;
  const input   = DOM.novelTitleInput;

  wrapper.addEventListener('click', () => {
    if (!wrapper.classList.contains('editing')) {
      wrapper.classList.add('editing');
      input.value = display.textContent;
      input.style.display = 'block';
      input.focus();
      input.select();
    }
  });

  function finishEdit() {
    const val = input.value.trim();
    if (val && val !== display.textContent) {
      display.textContent = val;
      // Save to backend
      const meta = { ...state.novelMeta, title: val };
      apiPut('/novel-meta', { meta }).then(() => {
        state.novelMeta.title = val;
        document.title = `${val} — NovelForge AI`;
        showToast('Title updated.', 'success');
      }).catch(e => showToast(`Failed to update title: ${e.message}`, 'error'));
    }
    wrapper.classList.remove('editing');
    input.style.display = 'none';
  }

  input.addEventListener('blur', finishEdit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); finishEdit(); }
    if (e.key === 'Escape') {
      wrapper.classList.remove('editing');
      input.style.display = 'none';
    }
  });
}

// ─────────────────────────────────────────────
// TOAST NOTIFICATIONS
// ─────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  const icon = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' }[type] || 'ℹ';
  toast.innerHTML = `<span>${icon}</span><span>${escHtml(message)}</span>`;

  DOM.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─────────────────────────────────────────────
// UTILITY — HTML ESCAPE
// ─────────────────────────────────────────────
function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ─────────────────────────────────────────────
// STATIC EVENT BINDINGS
// ─────────────────────────────────────────────
function bindStaticEvents() {
  // Generate button
  DOM.btnGenerate.addEventListener('click', generateChapter);

  // Plot textarea — Enter + Ctrl to generate
  DOM.plotInput.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') generateChapter();
  });

  // Header buttons
  DOM.btnSettings.addEventListener('click', openSettingsModal);
  DOM.btnAddCharacter.addEventListener('click', () => openCharacterModal());
  DOM.btnAddScene.addEventListener('click', () => openSceneModal());
  DOM.btnWorld.addEventListener('click', openWorldModal);

  // Export dropdown
  DOM.btnExport.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = DOM.exportDropdown.classList.toggle('visible');
    DOM.btnExport.classList.toggle('open', open);
    DOM.btnExport.setAttribute('aria-expanded', String(open));
  });

  document.addEventListener('click', () => {
    DOM.exportDropdown.classList.remove('visible');
    DOM.btnExport.classList.remove('open');
    DOM.btnExport.setAttribute('aria-expanded', 'false');
  });

  DOM.exportTxt.addEventListener('click', () => exportNovel('txt'));
  DOM.exportMd.addEventListener('click', () => exportNovel('md'));

  // View full chapter
  DOM.btnViewFull.addEventListener('click', openChapterViewModal);

  // Save buttons
  $('btn-save-character').addEventListener('click', saveCharacter);
  $('btn-save-scene').addEventListener('click', saveScene);
  $('btn-save-world').addEventListener('click', saveWorld);
  $('btn-save-settings').addEventListener('click', saveSettings);

  // Relationship add
  $('btn-add-relationship').addEventListener('click', () => {
    const name = $('rel-name').value.trim();
    const desc = $('rel-desc').value.trim();
    if (!name) { showToast('Enter a character name for the relationship.', 'error'); return; }
    state._relationships[name] = desc;
    $('rel-name').value = '';
    $('rel-desc').value = '';
    renderRelationships();
  });

  // Close modals — close buttons and cancel buttons
  document.addEventListener('click', (e) => {
    const closeBtn = e.target.closest('[data-modal]');
    if (closeBtn && (closeBtn.classList.contains('modal-close') || closeBtn.classList.contains('btn-cancel'))) {
      closeModal(closeBtn.dataset.modal);
    }
  });

  // Close modal on overlay click
  document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay') && state.activeModal) {
      closeModal(state.activeModal);
    }
  });

  // Close modal on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && state.activeModal) {
      closeModal(state.activeModal);
    }
  });

  // Init inline title editor
  initTitleEdit();
}

// ─────────────────────────────────────────────
// KEYBOARD SHORTCUTS
// ─────────────────────────────────────────────
document.addEventListener('keydown', (e) => {
  // Alt+G — Generate chapter
  if (e.altKey && e.key === 'g') {
    e.preventDefault();
    if (!state.isGenerating) generateChapter();
  }
  // Alt+N — New character
  if (e.altKey && e.key === 'n') {
    e.preventDefault();
    openCharacterModal();
  }
  // Alt+S — Settings
  if (e.altKey && e.key === 's') {
    e.preventDefault();
    openSettingsModal();
  }
  // Alt+W — World settings
  if (e.altKey && e.key === 'w') {
    e.preventDefault();
    openWorldModal();
  }
});

// ─────────────────────────────────────────────
// CONNECTION CHECK
// ─────────────────────────────────────────────
async function checkConnection() {
  try {
    await fetch(`${API}/novel-meta`, { signal: AbortSignal.timeout(3000) });
  } catch (e) {
    showToast('⚠ Cannot connect to backend. Is the server running on port 8000?', 'error', 8000);
  }
}

// ─────────────────────────────────────────────
// BOOT
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await checkConnection();
  await init();
});

// ═══════════════════════════════════════════════════════════
// MODE SWITCHER
// ═══════════════════════════════════════════════════════════
const MODES = ['plot', 'character', 'scene', 'world'];

function switchMode(newMode) {
  MODES.forEach(m => {
    const tab   = $(`mode-tab-${m}`);
    const panel = $(`mode-panel-${m}`);
    const active = m === newMode;
    if (tab)   { tab.classList.toggle('active', active); tab.setAttribute('aria-selected', String(active)); }
    if (panel) { panel.hidden = !active; }
  });
  state.activeMode = newMode;

  // When switching to world build mode, refresh the world snapshot
  if (newMode === 'world') renderWorldSnapshot();

  // When switching to character/scene build modes, populate existing dropdowns
  if (newMode === 'character') populateExistingCharDropdown();
  if (newMode === 'scene')     populateExistingSceneDropdown();
}

function bindModeTabs() {
  MODES.forEach(m => {
    const tab = $(`mode-tab-${m}`);
    if (tab) tab.addEventListener('click', () => switchMode(m));
  });
}

// ═══════════════════════════════════════════════════════════
// WORLD SNAPSHOT (shows current world settings in World Build mode)
// ═══════════════════════════════════════════════════════════
function renderWorldSnapshot() {
  const snap = $('world-snapshot');
  if (!snap) return;
  const w = state.world || {};
  const parts = [];
  if (w.world_name)          parts.push(`<strong>World:</strong> ${w.world_name}`);
  if (w.genre_tags?.length)  parts.push(`<strong>Genre:</strong> ${w.genre_tags.join(', ')}`);
  if (w.cultivation_system)  parts.push(`<strong>Cultivation:</strong> ${w.cultivation_system.substring(0,120)}${w.cultivation_system.length>120?'…':''}`);
  if (w.magic_system)        parts.push(`<strong>Magic:</strong> ${w.magic_system.substring(0,100)}${w.magic_system.length>100?'…':''}`);
  if (w.hierarchy_levels?.length) parts.push(`<strong>Hierarchy:</strong> ${w.hierarchy_levels.join(' → ')}`);
  if (w.factions?.length)    parts.push(`<strong>Factions:</strong> ${w.factions.join(', ')}`);
  if (w.rules_of_the_world)  parts.push(`<strong>World Rules:</strong> ${w.rules_of_the_world.substring(0,120)}…`);

  if (parts.length > 0) {
    snap.innerHTML = parts.join('<br>');
    snap.classList.add('has-data');
  } else {
    snap.innerHTML = '<span class="world-snap-empty">No world settings yet — describe your world below and the AI will structure it!</span>';
    snap.classList.add('has-data');
  }
}

// ═══════════════════════════════════════════════════════════
// POPULATE EXISTING DROPDOWNS (for update-existing flow)
// ═══════════════════════════════════════════════════════════
function populateExistingCharDropdown() {
  const sel = $('build-char-existing');
  if (!sel) return;
  sel.innerHTML = '<option value="">— Create New Character —</option>';
  (state.characters || []).forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.slug;
    opt.textContent = `${c.name} (${c.type})`;
    sel.appendChild(opt);
  });
}

function populateExistingSceneDropdown() {
  const sel = $('build-scene-existing');
  if (!sel) return;
  sel.innerHTML = '<option value="">— Create New Location —</option>';
  (state.scenes || []).forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.slug;
    opt.textContent = s.name;
    sel.appendChild(opt);
  });
}

// ═══════════════════════════════════════════════════════════
// REFINE — CHARACTER BUILD
// ═══════════════════════════════════════════════════════════
async function refineCharacter() {
  const desc = $('build-char-desc')?.value.trim();
  const name = $('build-char-name')?.value.trim();
  const existingSlug = $('build-char-existing')?.value;
  const statusEl = $('refine-char-status');
  const btn = $('btn-refine-char');

  if (!desc) { showToast('Please describe the character first.', 'error'); return; }

  btn.disabled = true;
  btn.querySelector('.refine-text').textContent = 'Refining...';
  statusEl.className = 'refine-status loading';
  statusEl.textContent = '✨ Calling specialist model...';

  try {
    const payload = { description: desc };
    if (name) payload.name = name;
    if (existingSlug) payload.existing_slug = existingSlug;

    const char = await apiPost('/refine/character', payload);

    statusEl.className = 'refine-status success';
    statusEl.textContent = `✓ ${existingSlug ? 'Updated' : 'Created'}: ${char.name}`;
    showToast(`Character "${char.name}" ${existingSlug ? 'updated' : 'saved'}!`, 'success');

    // Clear form
    $('build-char-desc').value = '';
    $('build-char-name').value = '';
    if ($('build-char-existing')) $('build-char-existing').value = '';

    // Reload characters sidebar
    await loadCharacters();
    populateExistingCharDropdown();
  } catch (e) {
    statusEl.className = 'refine-status error';
    statusEl.textContent = `✗ Error: ${e.message}`;
    showToast(`Refinement failed: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.querySelector('.refine-text').textContent = 'Refine & Save Character';
    setTimeout(() => { statusEl.textContent = ''; statusEl.className = 'refine-status'; }, 5000);
  }
}

// ═══════════════════════════════════════════════════════════
// REFINE — SCENE BUILD
// ═══════════════════════════════════════════════════════════
async function refineScene() {
  const desc = $('build-scene-desc')?.value.trim();
  const name = $('build-scene-name')?.value.trim();
  const existingSlug = $('build-scene-existing')?.value;
  const statusEl = $('refine-scene-status');
  const btn = $('btn-refine-scene');

  if (!desc) { showToast('Please describe the location first.', 'error'); return; }

  btn.disabled = true;
  btn.querySelector('.refine-text').textContent = 'Refining...';
  statusEl.className = 'refine-status loading';
  statusEl.textContent = '✨ Calling specialist model...';

  try {
    const payload = { description: desc };
    if (name) payload.name = name;
    if (existingSlug) payload.existing_slug = existingSlug;

    const scene = await apiPost('/refine/scene', payload);

    statusEl.className = 'refine-status success';
    statusEl.textContent = `✓ ${existingSlug ? 'Updated' : 'Created'}: ${scene.name}`;
    showToast(`Location "${scene.name}" ${existingSlug ? 'updated' : 'saved'}!`, 'success');

    $('build-scene-desc').value = '';
    $('build-scene-name').value = '';
    if ($('build-scene-existing')) $('build-scene-existing').value = '';

    await loadScenes();
    populateExistingSceneDropdown();
  } catch (e) {
    statusEl.className = 'refine-status error';
    statusEl.textContent = `✗ Error: ${e.message}`;
    showToast(`Refinement failed: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.querySelector('.refine-text').textContent = 'Refine & Save Location';
    setTimeout(() => { statusEl.textContent = ''; statusEl.className = 'refine-status'; }, 5000);
  }
}

// ═══════════════════════════════════════════════════════════
// REFINE — WORLD BUILD
// ═══════════════════════════════════════════════════════════
async function refineWorld() {
  const desc = $('build-world-desc')?.value.trim();
  const statusEl = $('refine-world-status');
  const btn = $('btn-refine-world');

  if (!desc) { showToast('Please describe the world element first.', 'error'); return; }

  btn.disabled = true;
  btn.querySelector('.refine-text').textContent = 'Integrating...';
  statusEl.className = 'refine-status loading';
  statusEl.textContent = '✨ Analyzing and merging into world settings...';

  try {
    const updatedWorld = await apiPost('/refine/world', { description: desc });

    // Update local state
    state.world = updatedWorld;
    renderWorldSnapshot();

    statusEl.className = 'refine-status success';
    statusEl.textContent = '✓ World settings updated!';
    showToast('World settings updated!', 'success');
    $('build-world-desc').value = '';
  } catch (e) {
    statusEl.className = 'refine-status error';
    statusEl.textContent = `✗ Error: ${e.message}`;
    showToast(`World update failed: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.querySelector('.refine-text').textContent = 'Integrate into World Settings';
    setTimeout(() => { statusEl.textContent = ''; statusEl.className = 'refine-status'; }, 5000);
  }
}

// ═══════════════════════════════════════════════════════════
// DYNAMIC MODEL BROWSER
// ═══════════════════════════════════════════════════════════
let _cachedModels = null;

async function loadModels(force = false) {
  if (_cachedModels && !force) return _cachedModels;
  try {
    const data = await apiGet('/models');
    _cachedModels = data;
    return data;
  } catch (e) {
    return { installed: [], recommended: [], ollama_running: false, ollama_error: String(e) };
  }
}

function populateModelSelects(installed, currentWriter, currentSpec) {
  const writerSel = $('meta-writer-model');
  const specSel   = $('meta-specialist-model');
  if (!writerSel || !specSel) return;

  // Build option list: installed models come first
  const allModels = new Set(installed);

  // Add current selections even if not installed
  if (currentWriter) allModels.add(currentWriter);
  if (currentSpec)   allModels.add(currentSpec);

  writerSel.innerHTML = '';
  specSel.innerHTML   = '';

  [...allModels].forEach(m => {
    const isInstalled = installed.includes(m);
    const label = isInstalled ? m : `${m} (not installed)`;
    writerSel.insertAdjacentHTML('beforeend', `<option value="${m}">${label}</option>`);
    specSel.insertAdjacentHTML('beforeend',   `<option value="${m}">${label}</option>`);
  });

  if (currentWriter) writerSel.value = currentWriter;
  if (currentSpec)   specSel.value   = currentSpec;
}

function renderModelBrowser(data) {
  const grid = $('model-browser-grid');
  const dot  = $('ollama-dot');
  const statusText = $('ollama-status-text');
  if (!grid) return;

  // Ollama status
  if (dot) {
    dot.className = data.ollama_running ? 'ollama-dot running' : 'ollama-dot offline';
  }
  if (statusText) {
    if (data.ollama_running) {
      statusText.textContent = `Ollama running — ${data.installed.length} model(s) installed`;
    } else {
      statusText.textContent = `Ollama not reachable. Make sure it's running on localhost:11434`;
    }
  }

  const currentWriter = $('meta-writer-model')?.value || (state.novelMeta?.writer_model);
  const currentSpec   = $('meta-specialist-model')?.value || (state.novelMeta?.specialist_model);

  // Build merged list: recommended + any extra installed
  const recNames = (data.recommended || []).map(r => r.name);
  const extraInstalled = (data.installed || []).filter(m => !recNames.includes(m));
  const allEntries = [
    ...(data.recommended || []),
    ...extraInstalled.map(m => ({ name: m, size: '', quality: '', note: 'Installed', installed: true }))
  ];

  if (allEntries.length === 0) {
    grid.innerHTML = '<div class="model-browser-loading">No models found. Install Ollama and pull a model first.</div>';
    return;
  }

  grid.innerHTML = '';
  allEntries.forEach(model => {
    const isWriter    = model.name === currentWriter;
    const isSpec      = model.name === currentSpec;
    const isInstalled = model.installed;

    const entry = document.createElement('div');
    entry.className = `model-entry${isWriter ? ' is-writer' : ''}${isSpec ? ' is-specialist' : ''}`;

    const badges = [];
    if (isInstalled) badges.push(`<span class="model-badge-installed">✓ Installed</span>`);
    if (model.note === 'Recommended writer') badges.push(`<span class="model-badge-rec">★ Recommended</span>`);
    if (isWriter)    badges.push(`<span class="model-badge-writer">Writer</span>`);
    if (isSpec)      badges.push(`<span class="model-badge-specialist">Specialist</span>`);

    const actions = [];
    if (isInstalled) {
      if (!isWriter)  actions.push(`<button class="btn-set-writer"   data-model="${model.name}">Set Writer</button>`);
      if (!isSpec)    actions.push(`<button class="btn-set-specialist" data-model="${model.name}">Set Specialist</button>`);
    } else {
      actions.push(`<button class="btn-pull-model" data-model="${model.name}">⬇ Pull</button>`);
    }

    entry.innerHTML = `
      <div class="model-entry-info">
        <div class="model-entry-name">
          <span>${model.name}</span>
          ${badges.join('')}
        </div>
        <div class="model-entry-meta">${model.size ? `${model.size} &bull; ` : ''}${model.quality ? `${model.quality} &bull; ` : ''}${model.note || ''}</div>
        <div class="pull-progress-bar" id="pb-${model.name.replace(/[:.]/g,'_')}">
          <div class="pull-progress-fill" id="pf-${model.name.replace(/[:.]/g,'_')}"></div>
        </div>
        <div class="pull-status-text" id="ps-${model.name.replace(/[:.]/g,'_')}"></div>
      </div>
      <div class="model-entry-actions">${actions.join('')}</div>
    `;

    // Click handlers
    entry.querySelectorAll('.btn-set-writer').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const writerSel = $('meta-writer-model');
        if (writerSel) writerSel.value = model.name;
        renderModelBrowser(data); // re-render badges
      });
    });

    entry.querySelectorAll('.btn-set-specialist').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        const specSel = $('meta-specialist-model');
        if (specSel) specSel.value = model.name;
        renderModelBrowser(data);
      });
    });

    entry.querySelectorAll('.btn-pull-model').forEach(btn => {
      btn.addEventListener('click', e => {
        e.stopPropagation();
        pullModel(model.name, entry);
      });
    });

    grid.appendChild(entry);
  });
}

async function pullModel(modelName, entryEl) {
  const safeId = modelName.replace(/[:.]/g, '_');
  const progressBar  = $(`pb-${safeId}`);
  const progressFill = $(`pf-${safeId}`);
  const statusText   = $(`ps-${safeId}`);
  const pullBtn = entryEl?.querySelector('.btn-pull-model');

  if (pullBtn)      { pullBtn.disabled = true; pullBtn.textContent = 'Pulling...'; }
  if (progressBar)  { progressBar.classList.add('active'); }
  if (statusText)   { statusText.textContent = 'Starting download...'; }

  showToast(`Pulling ${modelName}... This may take a while.`, 'info', 5000);

  try {
    const response = await fetch(`${API}/models/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelName }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data: ')) continue;
        try {
          const d = JSON.parse(trimmed.slice(6));
          if (d.status === 'success') {
            if (progressFill) progressFill.style.width = '100%';
            if (statusText)   statusText.textContent = 'Download complete!';
            showToast(`✓ ${modelName} installed!`, 'success');
            // Refresh model list
            _cachedModels = null;
            await refreshModels();
            return;
          } else if (d.status === 'error') {
            if (statusText) statusText.textContent = `Error: ${d.message}`;
            showToast(`Pull failed: ${d.message}`, 'error');
            return;
          } else {
            if (progressFill && d.percent > 0) progressFill.style.width = `${d.percent}%`;
            if (statusText)   statusText.textContent = `${d.status}${d.percent > 0 ? ` — ${d.percent}%` : ''}`;
          }
        } catch (_) {}
      }
    }
  } catch (e) {
    if (statusText) statusText.textContent = `Failed: ${e.message}`;
    showToast(`Pull failed: ${e.message}`, 'error');
  } finally {
    if (pullBtn)     { pullBtn.disabled = false; pullBtn.textContent = '⬇ Pull'; }
    if (progressBar) { progressBar.classList.remove('active'); }
  }
}

async function refreshModels() {
  const data = await loadModels(true);
  const currentWriter = $('meta-writer-model')?.value || state.novelMeta?.writer_model;
  const currentSpec   = $('meta-specialist-model')?.value || state.novelMeta?.specialist_model;
  populateModelSelects(data.installed || [], currentWriter, currentSpec);
  renderModelBrowser(data);
}

// ═══════════════════════════════════════════════════════════
// WIRE UP NEW EVENT BINDINGS
// ═══════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  // Mode tabs
  bindModeTabs();

  // Refine buttons
  const btnRefineChar  = $('btn-refine-char');
  const btnRefineScene = $('btn-refine-scene');
  const btnRefineWorld = $('btn-refine-world');
  if (btnRefineChar)  btnRefineChar.addEventListener('click',  refineCharacter);
  if (btnRefineScene) btnRefineScene.addEventListener('click', refineScene);
  if (btnRefineWorld) btnRefineWorld.addEventListener('click', refineWorld);

  // Refresh models button
  const btnRefresh = $('btn-refresh-models');
  if (btnRefresh) btnRefresh.addEventListener('click', refreshModels);

  // Load models dynamically when Settings opens
  // (second listener stacks on top of the existing one — no replacement, no recursion)
  const btnSettingsEl = document.getElementById('btn-settings');
  if (btnSettingsEl) {
    btnSettingsEl.addEventListener('click', () => {
      loadModels().then(data => {
        const m = state.novelMeta || {};
        populateModelSelects(data.installed || [], m.writer_model, m.specialist_model);
        renderModelBrowser(data);
      });
    });
  }
});


