/* ═══════════════════════════════════════════════════════════════
   NovelForge AI — Application Logic
   Pure Vanilla JS  |  No external dependencies
   ═══════════════════════════════════════════════════════════════ */

const API = '/api';  // same origin as the page, so the server needs no CORS (KI-010, KI-021)

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
  draft: null,         // the chapter draft waiting for review (GET /api/draft), plan 019
  regenerate: null,    // the saved chapter the plot box writes a new version of: { chapter_number, title }, plan 024
  isGenerating: false,
  activeModal: null,
  _mentions: [],       // entities picked with @ in the plot box: { kind, slug, name }
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
  // Edit modals: the slug being edited, null = create mode
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
  btnCancelGenerate: $('btn-cancel-generate'),
  regenerateNotice:  $('regenerate-notice'),
  regenerateNoticeText: $('regenerate-notice-text'),

  // Center - Pipeline
  pipelineSection:   $('pipeline-section'),
  pipelineProgressFill: $('pipeline-progress-fill'),
  newEntities:       $('new-entities'),

  // Center - Output
  outputSection:     $('output-section'),
  outputChapterBadge:$('output-chapter-badge'),
  outputChapterTitle:$('output-chapter-title'),
  wordCountNum:      $('word-count-num'),
  outputBody:        $('output-body'),
  chapterTextArea:   $('chapter-text-area'),
  textCursor:        $('text-cursor'),
  btnViewFull:       $('btn-view-full'),
  btnRegenerateChapter: $('btn-regenerate-chapter'),
  multiChapterNotice:$('multi-chapter-notice'),
  multiChapterMessage:$('multi-chapter-message'),

  // Center - Draft review (plan 019)
  draftPanel:        $('draft-panel'),
  draftEditor:       $('draft-editor'),
  draftInstruction:  $('draft-instruction'),
  btnDraftRewrite:   $('btn-draft-rewrite'),
  btnDraftUndo:      $('btn-draft-undo'),
  draftSelection:    $('draft-selection'),
  draftTitle:        $('draft-title'),
  draftSaveStatus:   $('draft-save-status'),
  btnDraftDiscard:   $('btn-draft-discard'),
  btnDraftApprove:   $('btn-draft-approve'),
  mentionList:       $('mention-list'),

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
  await loadDraft();  // a draft left from the last visit opens again (plan 019)
  updateChapterHint();
  console.log('[NovelForge] Ready.');
}

// ─────────────────────────────────────────────
// API HELPERS
// ─────────────────────────────────────────────
// A failed call throws an Error that also carries the HTTP `status` and the server's `detail` message (plan 019)
function apiError(message, status, text = '') {
  const err = new Error(message);
  err.status = status;
  try {
    const detail = JSON.parse(text).detail;
    if (typeof detail === 'string') err.detail = detail;
  } catch (_) { /* not JSON */ }
  return err;
}

// The server's own words for a failed call, for toasts
function errorText(e) {
  return e.detail || e.message;
}

async function apiGet(path) {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw apiError(`GET ${path} failed: ${res.status} ${res.statusText}`, res.status, await res.text());
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
    throw apiError(`POST ${path} failed: ${res.status} — ${text}`, res.status, text);
  }
  return res.json();
}

// options.keepalive lets the request finish while the page closes (the draft's last autosave)
async function apiPut(path, body, options = {}) {
  const res = await fetch(`${API}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    keepalive: Boolean(options.keepalive),
  });
  if (!res.ok) {
    const text = await res.text();
    throw apiError(`PUT ${path} failed: ${res.status} — ${text}`, res.status, text);
  }
  return res.json();
}

async function apiDelete(path) {
  const res = await fetch(`${API}${path}`, { method: 'DELETE' });
  if (!res.ok) throw apiError(`DELETE ${path} failed: ${res.status}`, res.status, await res.text());
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
      specialist_model: 'phi4-mini:3.8b',  // the backend default (models.py NovelMeta), KI-028
      review_drafts: true,                 // the backend default too (plan 019)
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
    // Whether the open draft replaces a saved chapter may have changed
    if (state.draft) DOM.outputChapterTitle.textContent = draftHeading(state.draft, DOM.draftTitle.value.trim());
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

// Highest existing chapter number + 1, like the backend's get_next_number() (KI-008)
function nextChapterNumber() {
  return state.chapters.reduce((max, ch) => Math.max(max, ch.chapter_number), 0) + 1;
}

function updateChapterHint() {
  const regen = state.regenerate;
  const num = regen ? regen.chapter_number : nextChapterNumber();
  DOM.chapterNumLabel.textContent = `CHAPTER ${num}`;
  DOM.nextChapterHint.textContent = state.draft
    ? `Draft of Chapter ${state.draft.chapter_number} is waiting for review`
    : regen ? `Will regenerate Chapter ${num} as a draft` : `Will generate Chapter ${num}`;
}

const generateLabel = () => state.regenerate ? `Regenerate Chapter ${state.regenerate.chapter_number}` : 'Generate Chapter';

// ─────────────────────────────────────────────
// REGENERATE A SAVED CHAPTER (plan 024)
// ─────────────────────────────────────────────
// The chapter's prompt goes into the plot box, and Generate writes a new version of it. That version always opens as a
// draft, so the saved chapter stays as it is until the draft is approved, and Discard keeps it (D-019).
function startRegeneration(number) {
  const chapter = state.chapters.find(ch => ch.chapter_number === number);
  if (!chapter) return;
  if (state.isGenerating) {
    showToast('Wait until the running generation has finished.', 'error');
    return;
  }
  const prompt = (chapter.plot_input || '').trim();
  const current = DOM.plotInput.value.trim();
  if (prompt && current && current !== prompt &&
      !confirm(`Replace the text in the plot box with the prompt of Chapter ${number}?`)) return;
  if (state.activeModal === 'modal-chapter') closeModal('modal-chapter');
  switchMode('plot');
  if (prompt) {  // a chapter without a saved prompt keeps what the plot box holds
    DOM.plotInput.value = prompt;
    state._mentions = [];
  }
  state.regenerate = { chapter_number: number, title: chapter.title || '' };
  updateRegenerateUi();
  DOM.plotInput.focus();
  showToast(prompt ? `Change the prompt if you like, then press Regenerate Chapter ${number}.`
                   : `Describe what the new Chapter ${number} should tell, then press Regenerate Chapter ${number}.`, 'info', 6000);
}

function stopRegeneration() {
  if (!state.regenerate) return;
  state.regenerate = null;
  updateRegenerateUi();
}

function updateRegenerateUi() {
  const regen = state.regenerate;
  DOM.regenerateNotice.hidden = !regen;
  if (regen) {
    DOM.regenerateNoticeText.textContent = `⟳ Regenerating Chapter ${regen.chapter_number}` +
      (regen.title ? ` · "${regen.title}"` : '') + '. The saved chapter stays until you approve the new draft.';
  }
  if (!state.isGenerating) DOM.btnGenerate.querySelector('.generate-text').textContent = generateLabel();
  updateChapterHint();
}

// Approving a draft whose number is a saved chapter replaces that chapter
const replacesSavedChapter = (draft) => state.chapters.some(ch => ch.chapter_number === draft.chapter_number);
// The output title of a draft: its own title, else what approving it does
const draftHeading = (draft, title = draft.title) => title ||
  (replacesSavedChapter(draft) ? 'New version: approving replaces the saved chapter' : 'Review, edit, then approve');

// ─────────────────────────────────────────────
// VIEW CHAPTER
// ─────────────────────────────────────────────
async function viewChapter(number) {
  try {
    showToast(`Loading Chapter ${number}…`, 'info');
    const chapter = await apiGet(`/chapters/${number}`);

    // Update pill highlighting
    $$('.chapter-pill').forEach(p => {
      p.classList.toggle('active', parseInt(p.dataset.chapterNum) === number);
    });

    // While a draft is open it keeps the output section: show the chapter in the Full View instead (plan 019)
    if (state.draft) {
      openChapterViewModal(chapter);
      return;
    }

    // Show chapter in output section
    state.currentChapter = chapter;
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
  DOM.btnRegenerateChapter.hidden = false;  // a saved chapter is shown (plan 024)

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
  const regen = state.regenerate;  // a new version of a saved chapter (plan 024)
  // One draft at a time: a new chapter needs the waiting draft approved or discarded first (plan 019)
  if (state.draft && !(await discardDraft(
    `A draft of Chapter ${state.draft.chapter_number} is waiting for review.\n\n` +
    (regen ? `Discard it and regenerate Chapter ${regen.chapter_number}?` : 'Discard it and generate a new chapter?')))) {
    return;
  }

  state.isGenerating = true;
  DOM.btnGenerate.disabled = true;
  DOM.btnGenerate.querySelector('.generate-text').textContent = 'Generating...';
  DOM.btnCancelGenerate.hidden = false;
  DOM.btnRegenerateChapter.hidden = true;

  // Reset & show pipeline
  resetPipeline();
  DOM.pipelineSection.hidden = false;
  DOM.outputSection.hidden = true;
  DOM.outputBody.hidden = false;
  DOM.multiChapterNotice.hidden = true;
  DOM.newEntities.innerHTML = '';

  // A new chapter is numbered by the backend (highest on disk + 1), so this number is for display only; a regeneration
  // sends the number of the chapter it rewrites
  const chapterNumber = regen ? regen.chapter_number : nextChapterNumber();
  // review: stop after writing and open the chapter as a draft. Tags: the @-picked entities still named in the plot
  const body = { plot, review: state.novelMeta.review_drafts !== false, ...taggedEntities(plot) };
  // A regeneration is always a draft, whatever the setting: the saved chapter stays until it is approved (D-019)
  if (regen) Object.assign(body, { chapter_number: regen.chapter_number, review: true });

  let streamedText = '';
  let currentParagraph = null;

  try {
    const response = await fetch(`${API}/generate-chapter`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      // e.g. 409 while another generation is running (KI-031): show the server's message
      const err = await response.json().catch(() => ({}));
      throw new Error(typeof err.detail === 'string' ? err.detail : `Server returned ${response.status}: ${response.statusText}`);
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
          // Finalize current paragraph, start new one (a first chunk may already contain \n\n: KI-032)
          if (!currentParagraph) {
            currentParagraph = document.createElement('p');
            DOM.chapterTextArea.appendChild(currentParagraph);
          }
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

      // Review mode: the chapter is written and saved as a draft; step 7 waits for Approve (plan 019)
      draft_complete: (data) => {
        DOM.textCursor.hidden = true;
        showAwaitingApproval();
        showDraft({
          chapter_number: data.chapter_number,
          plot_input: plot,
          full_text: data.full_text || '',
          title: '',
          characters_featured: data.characters || [],
          scenes_featured: data.scenes || [],
          new_characters: data.new_characters || [],
          new_scenes: data.new_scenes || [],
        });
        showToast(`Draft of Chapter ${data.chapter_number} is ready: edit it, then Approve to ` +
                  (replacesSavedChapter(data) ? 'replace the saved chapter.' : 'save it.'), 'info', 6000);
      },

      complete: async (data) => {
        completePipeline();
        DOM.textCursor.hidden = true;
        DOM.outputChapterBadge.textContent = `Chapter ${data.chapter_number}`;
        DOM.outputChapterTitle.textContent = data.title || `Chapter ${data.chapter_number}`;
        DOM.wordCountNum.textContent = (data.word_count || 0).toLocaleString();
        state.currentChapter = {
          chapter_number: data.chapter_number,
          title: data.title,
          word_count: data.word_count,
          characters_featured: data.characters || [],  // Full View tags (KI-032)
          scenes_featured: data.scenes || [],
          plot_input: plot,                            // Full View "Prompt used" (plan 019)
        };
        DOM.btnRegenerateChapter.hidden = false;      // a saved chapter is shown (plan 024)
        await Promise.all([loadChapters(), loadCharacters(), loadNovelMeta()]); // step 7 updated profiles and total_chapters
        showToast(`✓ Chapter ${data.chapter_number} complete — ${data.word_count?.toLocaleString()} words`, 'success');
        DOM.plotInput.value = '';
        state._mentions = [];
      },

      multi_chapter: (data) => {
        DOM.multiChapterNotice.hidden = false;
        DOM.multiChapterMessage.textContent = data.message || `Plot may span ${data.estimated} chapters`;
        showToast(data.message || 'Plot may span multiple chapters', 'warning');
      },

      // Non-fatal problems (a profile or update that couldn't be saved, a failed unload): show them (KI-018)
      warning: (data) => {
        console.warn('[NovelForge] Pipeline warning:', data.message);
        showToast(data.message || 'Something went wrong in this step', 'warning', 6000);
      },

      error: (data) => {
        DOM.textCursor.hidden = true;
        if (data.cancelled) {  // the user pressed Cancel: nothing went wrong (KI-031)
          resetPipeline();
          DOM.outputChapterTitle.textContent = 'Cancelled (not saved)';
          showToast('Generation cancelled', 'info');
          loadDraft();  // cancelled during step 7: the written chapter is kept as a draft (KI-041)
          return;
        }
        showToast(`Generation error: ${data.message}`, 'error', data.draft_saved ? 10000 : 4000);
        setStepError();
        loadDraft();  // a failed summary keeps the written chapter as a draft (KI-041)
      },
    });

  } catch (e) {
    showToast(`Failed to generate chapter: ${errorText(e)}`, 'error');
    console.error('[NovelForge] Generation error:', e);
    DOM.textCursor.hidden = true;
    setStepError();
    loadDraft();  // e.g. 409 because a draft was made in another tab: show it
  } finally {
    state.isGenerating = false;
    DOM.btnGenerate.disabled = false;
    DOM.btnGenerate.querySelector('.generate-text').textContent = generateLabel();
    DOM.btnCancelGenerate.hidden = true;
    DOM.btnCancelGenerate.disabled = false;
  }
}

// Stops the running generation; its stream then ends with a cancelled `error` event (KI-031)
async function cancelGeneration() {
  DOM.btnCancelGenerate.disabled = true;
  try {
    const res = await apiPost('/generate-chapter/cancel', {});
    if (!res.cancelled) DOM.btnCancelGenerate.disabled = false;  // nothing was running yet
  } catch (e) {
    showToast(`Could not cancel: ${e.message}`, 'error');
    DOM.btnCancelGenerate.disabled = false;
  }
}

// ─────────────────────────────────────────────
// DRAFT REVIEW (plan 019): edit, rewrite, approve or discard
// ─────────────────────────────────────────────
let _draftSaveTimer = null;            // pending autosave
let _draftSaveChain = Promise.resolve(); // autosaves run one after another, so an older one can't win
let _draftUndo = [];                   // { before, after } text around each AI rewrite, newest last

const countWords = (text) => text.split(/\s+/).filter(Boolean).length;  // like Python's len(text.split())

async function loadDraft() {
  try {
    const draft = await apiGet('/draft');  // null when no draft waits
    if (draft) {
      if (!state.draft) showToast(`Draft of Chapter ${draft.chapter_number} is waiting for review.`, 'info', 6000);
      showDraft(draft);
    }
  } catch (e) {
    console.warn('[NovelForge] Could not load the draft:', e.message);
  }
  updateChapterHint();
}

function showDraft(draft) {
  state.draft = draft;
  _draftUndo = [];
  DOM.outputSection.hidden = false;
  DOM.outputBody.hidden = true;
  DOM.draftPanel.hidden = false;
  DOM.textCursor.hidden = true;
  DOM.btnRegenerateChapter.hidden = true;
  stopRegeneration();  // the draft carries the chapter number now (plan 024)
  DOM.outputChapterBadge.textContent = `Draft · Chapter ${draft.chapter_number}`;
  DOM.outputChapterTitle.textContent = draftHeading(draft);
  DOM.draftEditor.value = draft.full_text || '';
  DOM.draftTitle.value = draft.title || '';
  DOM.draftInstruction.value = '';
  setDraftBusy(false);
  setDraftSaveStatus('Saved');
  updateDraftCounts();
  updateChapterHint();
}

function hideDraft() {
  clearTimeout(_draftSaveTimer);
  _draftSaveTimer = null;
  state.draft = null;
  _draftUndo = [];
  DOM.draftPanel.hidden = true;
  DOM.outputBody.hidden = false;
  updateChapterHint();
}

function setDraftSaveStatus(text, isError = false) {
  DOM.draftSaveStatus.textContent = text;
  DOM.draftSaveStatus.classList.toggle('is-error', isError);
}

function setDraftBusy(busy, message = '') {
  DOM.draftEditor.readOnly = busy;  // the selection's offsets must not move while the AI works
  [DOM.btnDraftRewrite, DOM.btnDraftApprove, DOM.btnDraftDiscard, DOM.draftInstruction, DOM.draftTitle]
    .forEach(el => { el.disabled = busy; });
  DOM.btnDraftUndo.disabled = busy || _draftUndo.length === 0;
  if (message) setDraftSaveStatus(message);
}

// Word count in the header, and what the rewrite would replace
function updateDraftCounts() {
  const editor = DOM.draftEditor;
  DOM.wordCountNum.textContent = countWords(editor.value).toLocaleString();
  const selected = editor.value.slice(editor.selectionStart, editor.selectionEnd);
  DOM.draftSelection.textContent = selected.trim()
    ? `Selected ${countWords(selected)} word(s): “${selected.trim().replace(/\s+/g, ' ').slice(0, 80)}${selected.length > 80 ? '…' : ''}”`
    : 'Select text in the draft to rewrite it with AI, or edit it directly.';
}

function draftBody() {
  return { full_text: DOM.draftEditor.value, title: DOM.draftTitle.value.trim() };
}

function scheduleDraftSave() {
  if (!state.draft) return;
  setDraftSaveStatus('Unsaved changes…');
  clearTimeout(_draftSaveTimer);
  _draftSaveTimer = setTimeout(saveDraftNow, 1000);
}

function saveDraftNow() {
  clearTimeout(_draftSaveTimer);
  _draftSaveTimer = null;
  _draftSaveChain = _draftSaveChain.then(async () => {
    if (!state.draft) return;
    setDraftSaveStatus('Saving…');
    try {
      state.draft = await apiPut('/draft', draftBody());  // reads the editor now, so the newest text is saved
      setDraftSaveStatus('Saved');
    } catch (e) {
      setDraftSaveStatus(`Not saved: ${errorText(e)}`, true);
    }
  });
  return _draftSaveChain;
}

async function rewriteSelection() {
  if (!state.draft) return;
  const editor = DOM.draftEditor;
  const start = editor.selectionStart;
  const end = editor.selectionEnd;
  const text = editor.value;
  const instruction = DOM.draftInstruction.value.trim();
  if (end <= start || !text.slice(start, end).trim()) {
    showToast('Select the text you want to rewrite first.', 'warning');
    editor.focus();
    return;
  }
  if (!instruction) {
    showToast('Describe how the selected text should change.', 'warning');
    DOM.draftInstruction.focus();
    return;
  }

  setDraftBusy(true, 'Rewriting the selection…');
  try {
    const res = await apiPost('/draft/rewrite', {
      before: text.slice(0, start), passage: text.slice(start, end), after: text.slice(end), instruction,
    });
    editor.setRangeText(res.replacement, start, end, 'select');  // the new text stays selected
    _draftUndo.push({ before: text, after: editor.value });
    DOM.draftInstruction.value = '';
    saveDraftNow();
    showToast('Selection rewritten. "Undo rewrite" brings the old text back.', 'success');
  } catch (e) {
    showToast(`Rewrite failed: ${errorText(e)}`, 'error', 6000);
    setDraftSaveStatus(_draftSaveTimer ? 'Unsaved changes…' : 'Saved');
  } finally {
    setDraftBusy(false);
    editor.focus();
    updateDraftCounts();
  }
}

function undoRewrite() {
  const last = _draftUndo[_draftUndo.length - 1];
  if (!last) return;
  if (DOM.draftEditor.value !== last.after &&
      !confirm('Undo the last rewrite? Edits you made after it are undone too.')) return;
  _draftUndo.pop();
  DOM.draftEditor.value = last.before;
  DOM.btnDraftUndo.disabled = _draftUndo.length === 0;
  updateDraftCounts();
  saveDraftNow();
}

// Returns true when no draft is left. `question` replaces the default confirmation text.
async function discardDraft(question = null) {
  const draft = state.draft;
  if (!draft) return true;
  if (!confirm(question || `Discard the draft of Chapter ${draft.chapter_number}? Its text is deleted and can't be recovered.`)) {
    return false;
  }
  clearTimeout(_draftSaveTimer);
  _draftSaveTimer = null;
  await _draftSaveChain;
  try {
    await apiDelete('/draft');
  } catch (e) {
    if (e.status !== 404) {  // 404: already gone
      showToast(`Could not discard the draft: ${errorText(e)}`, 'error');
      return false;
    }
  }
  hideDraft();
  DOM.outputSection.hidden = true;
  DOM.pipelineSection.hidden = true;

  // Step 3 created profiles for this draft: offer to remove the ones that still exist
  const created = [
    ...(draft.new_characters || []).map(slug => ({ kind: 'character', item: state.characters.find(c => c.slug === slug) })),
    ...(draft.new_scenes || []).map(slug => ({ kind: 'scene', item: state.scenes.find(s => s.slug === slug) })),
  ].filter(entry => entry.item);
  if (created.length && confirm(`This draft created ${created.length} new profile(s): ` +
      `${created.map(entry => entry.item.name).join(', ')}.\n\nDelete them too?`)) {
    for (const { kind, item } of created) {
      try {
        await apiDelete(`/${kind === 'character' ? 'characters' : 'scenes'}/${item.slug}`);
      } catch (e) {
        if (e.status !== 404) showToast(`Could not delete "${item.name}": ${errorText(e)}`, 'error');
      }
    }
    await Promise.all([loadCharacters(), loadScenes()]);
  }
  showToast('Draft discarded.', 'info');
  return true;
}

async function approveDraft() {
  if (!state.draft) return;
  const body = draftBody();
  if (!body.full_text.trim()) {
    showToast('The draft is empty: write something or discard it.', 'error');
    return;
  }
  // A regenerated chapter replaces the saved one, also when the draft is left from an earlier visit (plan 024)
  const number = state.draft.chapter_number;
  const saved = state.chapters.find(ch => ch.chapter_number === number);
  if (saved && !confirm(`Approving replaces the saved Chapter ${number}` + (saved.title ? ` ("${saved.title}")` : '') +
      ' with this draft. The current text is kept as an older version in its Full View (the newest 5 are kept).' +
      '\n\nReplace it?')) {
    return;
  }
  clearTimeout(_draftSaveTimer);
  _draftSaveTimer = null;
  await _draftSaveChain;
  setDraftBusy(true, 'Summarizing and updating character records…');
  DOM.btnDraftApprove.textContent = 'Approving…';
  showApprovalStep();
  try {
    const res = await apiPost('/draft/approve', body);
    const chapter = res.chapter;
    hideDraft();
    completePipeline();
    state.currentChapter = chapter;
    showChapterOutput(chapter);
    (res.warnings || []).forEach(message => showToast(message, 'warning', 6000));
    await Promise.all([loadChapters(), loadCharacters(), loadScenes(), loadNovelMeta()]);  // step 7 updated them
    DOM.plotInput.value = '';
    state._mentions = [];
    showToast(`Chapter ${chapter.chapter_number} saved — ${(chapter.word_count || 0).toLocaleString()} words`, 'success');
  } catch (e) {
    setStepError();
    setDraftBusy(false);
    setDraftSaveStatus('Not approved: the draft is kept', true);
    showToast(`Could not approve the draft: ${errorText(e)}`, 'error', 8000);
  } finally {
    DOM.btnDraftApprove.textContent = '✓ Approve & save';
  }
}

// Pipeline panel: steps 1-6 done, step 7 waits for Approve
function showAwaitingApproval() {
  for (let i = 1; i <= 6; i++) completePipelineStep(i);
  updateProgress(6);
  const log = $('step-7-log');
  if (log) log.textContent = 'Waiting for your approval';
}

// Pipeline panel while Approve runs step 7
function showApprovalStep() {
  resetPipeline();
  DOM.pipelineSection.hidden = false;
  for (let i = 1; i <= 6; i++) completePipelineStep(i);
  activatePipelineStep(7, 'Summarizing and updating character records...');
  updateProgress(6);
}

// The draft shown in the Full View
function draftAsChapter() {
  const draft = state.draft;
  return {
    chapter_number: draft.chapter_number,
    title: DOM.draftTitle.value.trim() || `Draft of Chapter ${draft.chapter_number}`,
    full_text: DOM.draftEditor.value,
    word_count: countWords(DOM.draftEditor.value),
    plot_input: draft.plot_input,
    characters_featured: draft.characters_featured || [],
    scenes_featured: draft.scenes_featured || [],
    is_draft: true,  // no ⟳ Regenerate in the Full View (plan 024)
  };
}

function bindDraftEvents() {
  const editor = DOM.draftEditor;
  editor.addEventListener('input', () => { updateDraftCounts(); scheduleDraftSave(); });
  ['select', 'keyup', 'mouseup'].forEach(type => editor.addEventListener(type, updateDraftCounts));
  DOM.draftTitle.addEventListener('input', scheduleDraftSave);
  DOM.draftInstruction.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); rewriteSelection(); }
  });
  DOM.btnDraftRewrite.addEventListener('click', rewriteSelection);
  DOM.btnDraftUndo.addEventListener('click', undoRewrite);
  DOM.btnDraftDiscard.addEventListener('click', () => discardDraft());
  DOM.btnDraftApprove.addEventListener('click', approveDraft);
  // Closing the tab within a second of typing: send the last change anyway
  window.addEventListener('pagehide', () => {
    if (_draftSaveTimer && state.draft) {
      clearTimeout(_draftSaveTimer);
      _draftSaveTimer = null;
      apiPut('/draft', draftBody(), { keepalive: true }).catch(() => {});
    }
  });
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
let _pipelineFadeTimer = null;  // completePipeline's pending fade

function resetPipeline() {
  // Undo the previous run's fade and red error step (KI-024)
  clearTimeout(_pipelineFadeTimer);
  DOM.pipelineSection.style.opacity = '';
  for (let i = 1; i <= 7; i++) {
    const step = $(`step-${i}`);
    if (!step) continue;
    step.style.borderColor = '';
    step.style.background = '';
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
  _pipelineFadeTimer = setTimeout(() => {
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

  // Edit keeps fields the modal does not show (chapter tracking). Create sends slug '' and the server derives it.
  const existing = state._editingCharSlug ? state.characters.find(c => c.slug === state._editingCharSlug) : null;
  const character = {
    ...existing,
    slug:              state._editingCharSlug || '',
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
      await apiPost('/characters', { character });
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

  // Edit keeps fields the modal does not show (first_appeared_chapter). Create sends slug '' and the server derives it.
  const existing = state._editingSceneSlug ? state.scenes.find(s => s.slug === state._editingSceneSlug) : null;
  const scene = {
    ...existing,
    slug:               state._editingSceneSlug || '',
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
      await apiPost('/scenes', { scene });
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
  $('meta-review-drafts').checked = m.review_drafts !== false;  // plan 019
  // Fill the model lists now, then refresh them from Ollama. The button and Alt+S both come here (KI-006).
  populateModelSelects(_cachedModels?.installed || [], m.writer_model, m.specialist_model);
  loadModels().then(data => {
    populateModelSelects(data.installed || [],
      $('meta-writer-model').value || m.writer_model, $('meta-specialist-model').value || m.specialist_model);
    renderModelBrowser(data);
  });
  openModal('modal-settings');
}

async function saveSettings() {
  // PUT is a full replace: keep the fields the form does not show (total_chapters, created_at) (KI-007)
  const meta = {
    ...state.novelMeta,
    title:            $('meta-title').value.trim(),
    genre:            $('meta-genre').value.trim(),
    author:           $('meta-author').value.trim(),
    writer_model:     $('meta-writer-model').value || state.novelMeta.writer_model,
    specialist_model: $('meta-specialist-model').value || state.novelMeta.specialist_model,
    review_drafts:    $('meta-review-drafts').checked,
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
// Shows `ch` (default: the chapter in the output section). A draft or a history chapter can be passed in (plan 019).
function openChapterViewModal(ch = state.currentChapter) {
  if (!ch) return;

  $('view-chapter-badge').textContent = ch.is_version ? `Chapter ${ch.chapter_number} · older version`
                                                      : `Chapter ${ch.chapter_number}`;
  $('chapter-modal-title').textContent = ch.title || `Chapter ${ch.chapter_number}`;
  $('view-word-count').textContent = `${(ch.word_count || 0).toLocaleString()} words`;

  // ⟳ Regenerate for a saved chapter, not for the draft (plan 024) or an older version (plan 025)
  const isSaved = !ch.is_draft && !ch.is_version && state.chapters.some(c => c.chapter_number === ch.chapter_number);
  const regenerateBtn = $('btn-view-regenerate');
  regenerateBtn.hidden = !isSaved;
  regenerateBtn.dataset.chapterNum = ch.chapter_number;

  // Older versions (plan 025): the list for a saved chapter, the notice while one of them is read
  _viewedInModal = { number: ch.chapter_number, versionId: ch.is_version ? ch.version_id : null };
  $('view-version-notice').hidden = !ch.is_version;
  if (ch.is_version) $('view-version-notice-text').textContent = `Older version, replaced ${formatDateTime(ch.replaced_at)}.`;
  $('view-versions-box').hidden = true;
  if (isSaved) loadChapterVersions(ch.chapter_number);

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

  // The plot the chapter was written from, ready to reuse (plan 019)
  const prompt = (ch.plot_input || '').trim();
  const promptBox = $('view-prompt-box');
  promptBox.hidden = !prompt;
  promptBox.open = false;
  $('view-prompt-text').textContent = prompt;

  // Text
  const viewText = $('chapter-view-text');
  viewText.innerHTML = '';

  // The chapter's own text, else the output area's (just generated), else fetch it
  const currentText = ch === state.currentChapter ? DOM.chapterTextArea.innerHTML : '';
  if (ch.full_text) {
    formatChapterText(viewText, ch.full_text);
  } else if (currentText) {
    viewText.innerHTML = currentText;
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

// "Use this prompt again": the Full View's prompt goes back into the plot box (plan 019)
function reusePrompt() {
  const prompt = $('view-prompt-text').textContent;
  const current = DOM.plotInput.value.trim();
  if (current && current !== prompt.trim() && !confirm('Replace the text in the plot box with this prompt?')) return;
  closeModal('modal-chapter');
  switchMode('plot');
  DOM.plotInput.value = prompt;
  state._mentions = [];
  DOM.plotInput.focus();
  showToast('Prompt copied into the plot box.', 'info');
}

// ─────────────────────────────────────────────
// OLDER CHAPTER VERSIONS (plan 025)
// ─────────────────────────────────────────────
// The texts a regenerated chapter replaced (the newest 5 are kept): listed in the Full View, to read, restore or
// delete (D-020)
let _viewedInModal = null;  // what the Full View shows: { number, versionId } (versionId null = the saved chapter)

const formatDateTime = (iso) => {
  const date = new Date(iso);
  return isNaN(date) ? (iso || 'at an unknown time') : date.toLocaleString();
};

async function loadChapterVersions(number) {
  try {
    const versions = await apiGet(`/chapters/${number}/versions`);  // newest first, without the text
    // The Full View may show something else by now
    if (!_viewedInModal || _viewedInModal.number !== number || _viewedInModal.versionId) return;
    renderChapterVersions(number, versions);
  } catch (e) {
    console.warn('[NovelForge] Could not load the older versions:', e.message);
  }
}

function renderChapterVersions(number, versions) {
  const box = $('view-versions-box');
  const list = $('view-versions-list');
  list.innerHTML = '';
  box.hidden = versions.length === 0;
  $('view-versions-summary').textContent = `Older versions (${versions.length})`;
  versions.forEach(version => {
    const item = document.createElement('li');
    item.className = 'chapter-version-item';
    const meta = document.createElement('span');
    meta.className = 'chapter-version-meta';
    meta.textContent = `Replaced ${formatDateTime(version.replaced_at)} · "${version.title || `Chapter ${number}`}" · ` +
                       `${(version.word_count || 0).toLocaleString()} words`;
    item.appendChild(meta);
    [['Read', openChapterVersion], ['↺ Restore', restoreChapterVersion], ['🗑 Delete', deleteChapterVersion]]
      .forEach(([label, action]) => {
        const btn = document.createElement('button');
        btn.className = 'btn-small';
        btn.textContent = label;
        btn.addEventListener('click', () => action(number, version.version_id));
        item.appendChild(btn);
      });
    list.appendChild(item);
  });
}

async function openChapterVersion(number, versionId) {
  try {
    const version = await apiGet(`/chapters/${number}/versions/${versionId}`);
    openChapterViewModal({ ...version, is_version: true });
  } catch (e) {
    showToast(`Could not open the older version: ${errorText(e)}`, 'error');
  }
}

async function showSavedChapterInModal(number) {
  try {
    openChapterViewModal(await apiGet(`/chapters/${number}`));
  } catch (e) {
    closeModal('modal-chapter');
    showToast(`Could not load Chapter ${number}: ${errorText(e)}`, 'error');
  }
}

async function restoreChapterVersion(number, versionId) {
  if (!confirm(`Restore this older version of Chapter ${number}? It becomes the saved chapter again, and the current ` +
               'text is kept as an older version.')) return;
  try {
    const res = await apiPost(`/chapters/${number}/versions/${versionId}/restore`, {});
    await loadChapters();
    if (!state.draft && state.currentChapter && state.currentChapter.chapter_number === number) {
      state.currentChapter = res.chapter;  // the output section shows this chapter: show the restored text there too
      showChapterOutput(res.chapter);
    }
    openChapterViewModal(res.chapter);
    showToast(`Chapter ${number} restored. The text it replaced is kept as an older version.`, 'success', 6000);
  } catch (e) {
    showToast(`Could not restore the older version: ${errorText(e)}`, 'error', 6000);  // e.g. 409 while the AI works
  }
}

async function deleteChapterVersion(number, versionId) {
  if (!confirm(`Delete this older version of Chapter ${number}? It can't be recovered.`)) return;
  try {
    await apiDelete(`/chapters/${number}/versions/${versionId}`);
  } catch (e) {
    if (e.status !== 404) {  // 404: already gone
      showToast(`Could not delete the older version: ${errorText(e)}`, 'error');
      return;
    }
  }
  showToast('Older version deleted.', 'info');
  if (_viewedInModal && _viewedInModal.versionId === versionId) await showSavedChapterInModal(number);
  else loadChapterVersions(number);
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
  DOM.btnCancelGenerate.addEventListener('click', cancelGeneration);

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

  // View full chapter (or the draft being reviewed)
  DOM.btnViewFull.addEventListener('click', () => openChapterViewModal(state.draft ? draftAsChapter() : undefined));
  $('btn-reuse-prompt').addEventListener('click', reusePrompt);

  // ⟳ Regenerate a saved chapter (plan 024)
  DOM.btnRegenerateChapter.addEventListener('click', () => {
    if (state.currentChapter) startRegeneration(state.currentChapter.chapter_number);
  });
  $('btn-view-regenerate').addEventListener('click', (e) => startRegeneration(Number(e.currentTarget.dataset.chapterNum)));
  $('btn-regenerate-stop').addEventListener('click', () => {
    stopRegeneration();
    showToast('Back to writing the next new chapter.', 'info');
  });

  // The notice while the Full View shows an older version (plan 025)
  $('btn-version-current').addEventListener('click', () => {
    if (_viewedInModal) showSavedChapterInModal(_viewedInModal.number);
  });
  $('btn-version-restore').addEventListener('click', () => {
    if (_viewedInModal?.versionId) restoreChapterVersion(_viewedInModal.number, _viewedInModal.versionId);
  });
  $('btn-version-delete').addEventListener('click', () => {
    if (_viewedInModal?.versionId) deleteChapterVersion(_viewedInModal.number, _viewedInModal.versionId);
  });

  // Draft review and @-mentions (plan 019)
  bindDraftEvents();
  initMentions();

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
  const key = (e.key || '').toLowerCase();  // also with Caps Lock or Shift (KI-032)
  // Alt+G — Generate chapter
  if (e.altKey && key === 'g') {
    e.preventDefault();
    if (!state.isGenerating) generateChapter();
  }
  // Alt+N — New character
  if (e.altKey && key === 'n') {
    e.preventDefault();
    openCharacterModal();
  }
  // Alt+S — Settings
  if (e.altKey && key === 's') {
    e.preventDefault();
    openSettingsModal();
  }
  // Alt+W — World settings
  if (e.altKey && key === 'w') {
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
  // World fields can come from LLM output: escape every value (KI-011)
  if (w.world_name)          parts.push(`<strong>World:</strong> ${escHtml(w.world_name)}`);
  if (w.genre_tags?.length)  parts.push(`<strong>Genre:</strong> ${w.genre_tags.map(escHtml).join(', ')}`);
  if (w.cultivation_system)  parts.push(`<strong>Cultivation:</strong> ${escHtml(w.cultivation_system.substring(0,120))}${w.cultivation_system.length>120?'…':''}`);
  if (w.magic_system)        parts.push(`<strong>Magic:</strong> ${escHtml(w.magic_system.substring(0,100))}${w.magic_system.length>100?'…':''}`);
  if (w.hierarchy_levels?.length) parts.push(`<strong>Hierarchy:</strong> ${w.hierarchy_levels.map(escHtml).join(' → ')}`);
  if (w.factions?.length)    parts.push(`<strong>Factions:</strong> ${w.factions.map(escHtml).join(', ')}`);
  if (w.rules_of_the_world)  parts.push(`<strong>World Rules:</strong> ${escHtml(w.rules_of_the_world.substring(0,120))}…`);

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
    statusEl.textContent = `✗ Error: ${errorText(e)}`;  // the server's words, e.g. the 409 while a chapter is written
    showToast(`Refinement failed: ${errorText(e)}`, 'error');
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
    statusEl.textContent = `✗ Error: ${errorText(e)}`;  // the server's words, e.g. the 409 while a chapter is written
    showToast(`Refinement failed: ${errorText(e)}`, 'error');
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
    statusEl.textContent = `✗ Error: ${errorText(e)}`;
    showToast(`World update failed: ${errorText(e)}`, 'error');
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
    writerSel.insertAdjacentHTML('beforeend', `<option value="${escHtml(m)}">${escHtml(label)}</option>`);
    specSel.insertAdjacentHTML('beforeend',   `<option value="${escHtml(m)}">${escHtml(label)}</option>`);
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
      statusText.textContent = `Ollama not reachable: ${data.ollama_error || 'no response'}`;  // names the address tried (KI-033)
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

    // Model names come from Ollama: escape them everywhere (KI-011). pullModel looks the ids up unescaped.
    const name = escHtml(model.name);
    const safeId = escHtml(model.name.replace(/[:.]/g,'_'));
    const actions = [];
    if (isInstalled) {
      if (!isWriter)  actions.push(`<button class="btn-set-writer"   data-model="${name}">Set Writer</button>`);
      if (!isSpec)    actions.push(`<button class="btn-set-specialist" data-model="${name}">Set Specialist</button>`);
    } else {
      actions.push(`<button class="btn-pull-model" data-model="${name}">⬇ Pull</button>`);
    }

    entry.innerHTML = `
      <div class="model-entry-info">
        <div class="model-entry-name">
          <span>${name}</span>
          ${badges.join('')}
        </div>
        <div class="model-entry-meta">${model.size ? `${escHtml(model.size)} &bull; ` : ''}${model.quality ? `${escHtml(model.quality)} &bull; ` : ''}${escHtml(model.note || '')}</div>
        <div class="pull-progress-bar" id="pb-${safeId}">
          <div class="pull-progress-fill" id="pf-${safeId}"></div>
        </div>
        <div class="pull-status-text" id="ps-${safeId}"></div>
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
});


// ═══════════════════════════════════════════════════════════
// @-MENTIONS IN THE PLOT BOX (plan 019)
// Type @ at the start of a word: pick a character or location to insert its exact name. Picked entities are sent
// with the generation, so the writer gets their full profiles.
// ═══════════════════════════════════════════════════════════
// "@" at the start or after a space or opening punctuation, then up to 40 name characters (any script)
const MENTION_RE = /(^|[\s([{"“‘«—–])@([\p{L}\p{M}\p{N}_' -]{0,40})$/u;
const MENTION_LIMIT = 8;
const mention = { start: -1, items: [], active: 0 };

function initMentions() {
  const box = DOM.plotInput;
  box.addEventListener('input', updateMentions);
  box.addEventListener('click', updateMentions);
  box.addEventListener('keyup', (e) => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'Home' || e.key === 'End') updateMentions();
  });
  box.addEventListener('blur', closeMentions);
  box.addEventListener('keydown', (e) => {
    if (DOM.mentionList.hidden || e.ctrlKey || e.altKey || e.metaKey) return;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const n = mention.items.length;
      mention.active = (mention.active + (e.key === 'ArrowDown' ? 1 : n - 1)) % n;
      renderMentions();
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      pickMention(mention.active);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      closeMentions();
    }
  });
  window.addEventListener('resize', closeMentions);
}

// Characters and locations whose name matches the typed text: name starts with it, then a word does, then contains it
function mentionCandidates(query) {
  const q = query.trim().toLocaleLowerCase();
  const all = [
    ...state.characters.map(c => ({ kind: 'character', slug: c.slug, name: c.name })),
    ...state.scenes.map(s => ({ kind: 'scene', slug: s.slug, name: s.name })),
  ];
  const rank = (name) => {
    const n = name.toLocaleLowerCase();
    if (!q || n.startsWith(q)) return 0;
    if (n.split(/\s+/).some(word => word.startsWith(q))) return 1;
    return n.includes(q) ? 2 : -1;
  };
  return all
    .map(item => ({ ...item, rank: rank(item.name) }))
    .filter(item => item.rank >= 0)
    .sort((a, b) => a.rank - b.rank || a.name.localeCompare(b.name))
    .slice(0, MENTION_LIMIT);
}

function updateMentions() {
  const box = DOM.plotInput;
  if (box.selectionStart !== box.selectionEnd) return closeMentions();
  const match = box.value.slice(0, box.selectionStart).match(MENTION_RE);
  if (!match) return closeMentions();
  const items = mentionCandidates(match[2]);
  if (!items.length) return closeMentions();
  mention.start = match.index + match[1].length;  // where the "@" is
  mention.items = items;
  mention.active = 0;  // the best match first; ↑/↓ move from there
  renderMentions();
  placeMentions();
}

function renderMentions() {
  const list = DOM.mentionList;
  list.innerHTML = mention.items.map((item, i) => `
    <div class="mention-item mention-${item.kind}" role="option" id="mention-opt-${i}"
         aria-selected="${i === mention.active}" data-index="${i}">
      <span aria-hidden="true">${item.kind === 'character' ? '👤' : '📍'}</span>
      <span class="mention-name">${escHtml(item.name)}</span>
      <span class="mention-kind">${item.kind === 'character' ? 'Character' : 'Location'}</span>
    </div>`).join('');
  list.querySelectorAll('.mention-item').forEach(el => {
    // mousedown, not click: the plot box keeps its focus and caret
    el.addEventListener('mousedown', (e) => { e.preventDefault(); pickMention(Number(el.dataset.index)); });
  });
  list.hidden = false;
  DOM.plotInput.setAttribute('aria-activedescendant', `mention-opt-${mention.active}`);
  $(`mention-opt-${mention.active}`)?.scrollIntoView({ block: 'nearest' });
}

// Below the caret, kept inside the plot box's width
function placeMentions() {
  const box = DOM.plotInput;
  const list = DOM.mentionList;
  const caret = caretPosition(box, mention.start);
  const top = Math.min(caret.top + caret.lineHeight, box.clientHeight) + box.offsetTop + 4;
  const maxLeft = Math.max(0, box.offsetWidth - list.offsetWidth);
  list.style.top = `${top}px`;
  list.style.left = `${Math.min(Math.max(0, caret.left + box.offsetLeft), maxLeft)}px`;
}

// Caret coordinates inside a textarea: a hidden copy with the same text metrics, measured at `index`
function caretPosition(textarea, index) {
  const style = getComputedStyle(textarea);
  const mirror = document.createElement('div');
  ['boxSizing', 'width', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft', 'borderTopWidth',
   'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth', 'fontFamily', 'fontSize', 'fontWeight', 'fontStyle',
   'letterSpacing', 'lineHeight', 'textTransform', 'wordSpacing', 'textIndent', 'tabSize']
    .forEach(prop => { mirror.style[prop] = style[prop]; });
  Object.assign(mirror.style, { position: 'absolute', visibility: 'hidden', top: '0', left: '-9999px',
    whiteSpace: 'pre-wrap', overflowWrap: 'break-word' });
  mirror.textContent = textarea.value.slice(0, index);
  const marker = document.createElement('span');
  marker.textContent = '\u200b';  // zero-width: marks the caret without moving it
  mirror.appendChild(marker);
  document.body.appendChild(mirror);
  const position = {
    top: marker.offsetTop - textarea.scrollTop,
    left: marker.offsetLeft - textarea.scrollLeft,
    lineHeight: parseFloat(style.lineHeight) || parseFloat(style.fontSize) * 1.5,
  };
  mirror.remove();
  return position;
}

function pickMention(index) {
  const item = mention.items[index];
  if (!item) return;
  const box = DOM.plotInput;
  const end = box.selectionStart;
  const after = box.value.slice(end);
  const insert = item.name + (/^\s/.test(after) ? '' : ' ');
  box.setRangeText(insert, mention.start, end, 'end');
  if (!state._mentions.some(m => m.kind === item.kind && m.slug === item.slug)) {
    state._mentions.push({ kind: item.kind, slug: item.slug, name: item.name });
  }
  closeMentions();
  box.focus();
}

function closeMentions() {
  if (DOM.mentionList.hidden) return;
  DOM.mentionList.hidden = true;
  DOM.mentionList.innerHTML = '';
  DOM.plotInput.removeAttribute('aria-activedescendant');
  mention.items = [];
  mention.active = 0;
}

// The picked entities whose name is still in the plot and that still exist, for POST /api/generate-chapter
function taggedEntities(plot) {
  const text = plot.toLocaleLowerCase();
  const stillThere = (m, list) => text.includes(m.name.toLocaleLowerCase()) && list.some(e => e.slug === m.slug);
  return {
    tagged_characters: state._mentions.filter(m => m.kind === 'character' && stillThere(m, state.characters)).map(m => m.slug),
    tagged_scenes: state._mentions.filter(m => m.kind === 'scene' && stillThere(m, state.scenes)).map(m => m.slug),
  };
}
