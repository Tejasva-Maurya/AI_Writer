# Testing NovelForge AI on a machine with Ollama

> **What this is:** a hands-on test guide with copy-paste prompts and a checklist, for running the tool against **real local models**.
> **Why:** the development machine has no Ollama. Since plan 019, every LLM-dependent feature was checked only with a fake `ollama` stub, so prose quality, timing and VRAM behaviour are still unverified.
> **Applies to:** `main` from 2026-11-27 (plans 019–026). **Time needed:** about 2–3 hours for everything; T1–T7 alone take about 1 hour.

Contents: [1 Machine](#1-the-machine) · [2 Setup](#2-setup-on-the-test-machine) · [3 Record](#3-test-record) · [4 Tests T1–T14](#4-test-sessions) · [5 Quality rubric](#5-prose-quality-rubric) · [6 Checklist](#6-checklist) · [7 Report back](#7-what-to-send-back-and-cleanup)

---

## 1. The machine

| Need | Details |
|---|---|
| **OS** | Windows 10/11 is the main target (`app/start.bat`). macOS and Linux work with the manual start (§2.4). |
| **Python** | 3.11 or newer. On Windows, tick **Add Python to PATH** during installation. |
| **Ollama** | Installed and running (`ollama --version`). The app talks to `http://127.0.0.1:11434`, or to `OLLAMA_HOST` if you set it. |
| **GPU / RAM** | The defaults are writer `gemma3:12b` (about a 7 GB download) and specialist `phi4-mini:3.8b` (about 2.3 GB). The writer runs with a **32k context** (`num_ctx` 32768), which needs a lot more memory than the download size. A 16 GB+ GPU should hold it fully. On 8–12 GB, part of it may run on the CPU, which is slower but works. `ollama ps` shows the split. |
| **Smaller GPU** | Use writer `llama3.1:8b` or `qwen2.5:7b` with specialist `phi4-mini:3.8b`. On very low-end machines, `phi4-mini:3.8b` can also be the writer, at lower quality. |
| **Disk** | About 10 GB for the two default models. |

**Data safety.** The novel lives in `data/`, which is **not in git** (D-014), so a fresh clone starts with an **empty novel**. That is exactly what you want for testing.
- Don't copy a real `data/` folder onto the test machine.
- If you must test with real content, copy it and test on the copy only.

## 2. Setup on the test machine

### 2.1 Get the code
```powershell
git clone https://github.com/Tejasva-Maurya/AI_Writer.git
```
```powershell
cd AI_Writer
```
Note the commit you test: `git log --oneline -1`.

### 2.2 Pull the models
```powershell
ollama pull gemma3:12b
```
```powershell
ollama pull phi4-mini:3.8b
```
You can also pull them later from **⚙ Settings → Available Models → ⬇ Pull**; that is test T1.

### 2.3 Start, Windows
Double-click **`app\start.bat`**. It:
1. finds Python;
2. installs or upgrades the dependencies (`ollama` must be ≥ 0.4);
3. starts the server in a minimised window named **NovelForge-Backend**;
4. waits for `/api/health`;
5. opens **http://127.0.0.1:8000**.

Keep the **NovelForge-Backend** window: its log is part of the test results. To stop the server, close that window.

### 2.4 Start, any OS (manual)
```powershell
python -m venv venv
```
```powershell
venv\Scripts\activate
```
(macOS/Linux: `source venv/bin/activate`.)
```powershell
pip install -r app/requirements.txt
```
```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --app-dir app/backend
```
Then open **http://127.0.0.1:8000** (`localhost` works too).

### 2.5 Smoke checks
```powershell
curl http://127.0.0.1:8000/api/health
```
Expected: `{"status":"ok", ...}`.
```powershell
curl http://127.0.0.1:8000/api/models
```
Expected: `"ollama_running": true`, with both models in `installed`.
```powershell
ollama ps
```
Expected: nothing loaded yet.

### 2.6 Optional: the automated tests
They need no Ollama. They show whether the machine itself is sane.
```powershell
pip install -r app/requirements-dev.txt
```
```powershell
python -m pytest app/tests
```
Expected: every test passes (146 on 2026-11-27).
```powershell
python -m ruff check app
```
Expected: `All checks passed!`

## 3. Test record

Copy this block into a file such as `test-results.md`, and fill it in as you go:

```text
Date / tester:
Commit tested (git log --oneline -1):
OS:                         Python:                  Ollama version:
GPU + VRAM:                 System RAM:
Writer model:               Specialist model:
Time to first token, chapter 1 (s):
Chapter 1: words / total time (s):
Approve (step 7) time (s):
ollama ps at step 6 (SIZE, PROCESSOR):
Failed checks (IDs from section 6):
Notes:
```

A stopwatch is enough for the times. While a chapter is written, the pipeline panel shows the step that runs, and the word counter moves.

---

## 4. Test sessions

Run the tests in order: later ones use the characters and chapters made earlier.

- **Text in code blocks** is meant to be pasted as it is.
- **"Expect"** says what should happen.
- **"Note"** says what to write in your record.
- Each test has check IDs (`T4.3` …) that match the checklist in §6.

### T1 — Settings and models
1. Open **⚙ Settings** (or `Alt+S`).
   - **Expect:** the status line says "Ollama running — N model(s) installed".
2. Set the novel title:
   ```text
   The Lantern Wharf: Test?
   ```
   Genre `Fantasy light novel`, author `Tester`.
3. Writer Model = `gemma3:12b`, Specialist Model = `phi4-mini:3.8b`. **Review each chapter as a draft before saving** = **on**. **Save Settings**.
4. *Optional:* in **Available Models**, press **⬇ Pull** on a recommended model you don't have.
   - **Expect:** progress, then success, and the model shows as installed.
   - Then stop Ollama (see T8) and press **⬇ Pull** on another one. **Expect:** an error, not a false success. Start Ollama again.
5. Reload the page.
   - **Expect:** the settings are kept, and the header shows the title.

### T2 — World Build
**World Build** tab. Paste this, then press **Integrate into World Settings**:
```text
The Ninefold Lantern Realm floats above an endless sea of clouds. People cultivate a "lantern flame" in their chest, in nine stages from Spark (1) to Sun-Heart (9); each stage lets you hold a hotter flame and shape it into tools or weapons. Three factions: the Wharf Guild (merchants and sky-ship crews, practical and neutral), the Ember Court (aristocrats who hoard flame-crystals) and the Ashen Choir (outlawed monks who believe flame should be shared). Rules: flame can be passed to another person only by touch and only once a day; overusing it leaves grey ash marks on the skin. History: 200 years ago the Great Dimming put out half the lanterns of the realm, and nobody knows why.
```
- **Expect:** the snapshot shows the world name, the 9-stage system, the 3 factions and the rules. Existing fields are merged, not wiped.
- **Note:** the time taken, and anything invented or missing.
- Then run `ollama ps`. **Expect:** the specialist is loaded and stays about 5 minutes.

### T3 — Characters and a location (Build tabs)
**Character Build** tab. For each character, type the **name** in the name field, paste the description, and press **Refine & Save Character**.

Name `Mei Ashgrove`:
```text
17-year-old apprentice lantern-smith at Cinder Wharf. Small and quick, soot on her cheeks, always chewing a liquorice root. Stubborn and curious; talks fast when nervous. Flame stage Spark 3, very low for her age, but she can feel cracks in other people's flames. Orphan raised by the old smith Tobin. Secretly keeps a dead lantern from the Great Dimming that sometimes flickers. Wants to join a sky-ship crew. Speaks plainly and uses wharf slang ("dim it", "bright work").
```

Name `Captain Rho Tanvir`:
```text
Captain of the sky-ship Wren, member of the Wharf Guild. Mid-forties, tall, one burnt hand; laughs loudly but watches everyone. Flame stage Ember 6. Former soldier of the Ember Court who deserted after a massacre he won't talk about. Fair, but hard on cowards. Owes Tobin a life debt. Calls everyone "sparrow".
```

Name `林雪` (a non-ASCII name test):
```text
A quiet Ashen Choir runaway, about twenty, shaved head, grey ash marks up both arms from overusing her flame. Flame stage Glow 4. Speaks rarely and formally. She hides at Cinder Wharf and trades healing for food. She knows a chant that can relight a dead lantern, but it costs a year of the singer's life.
```

**Scene Build** tab. Name `Cinder Wharf`, then **Refine & Save Location**:
```text
A crooked harbour of wooden piers bolted onto the edge of a floating island. Sky-ships dock in the clouds below and are winched up in nets. It smells of tar, hot metal and rain. Lantern-smith forges glow orange along the main pier day and night. At the far end is Tobin's forge, half collapsed, with a back room full of broken lanterns. Dangerous at night: Ember Court tax collectors patrol with flame-dogs.
```

**Update Existing:** in Character Build, pick **Update Existing = Mei Ashgrove**, leave the name empty, paste this and refine:
```text
She now has a thin burn scar across her left palm from a forge accident.
```
- **Expect:**
  - 3 character cards (Mei and Rho under Main Cast, depending on the AI's type) and 1 location card.
  - `林雪` works everywhere: card, View, Edit.
  - The update adds the scar and keeps everything else, with the same name and file.
- **Note:** the profile quality (does it keep your facts? invent too much?) and the time per refine.

### T4 — Chapter 1, review mode, with @-mentions
**Plot Writing** tab. Paste this plot. Then insert the names as **@-mentions**: delete the plain name, type `@Mei` and press **Enter**, and do the same for `@Cinder` and `@Rho`.
```text
Mei Ashgrove is finishing a lantern repair late at night in Cinder Wharf when Ember Court tax collectors and their flame-dogs arrive to seize Tobin's forge for unpaid taxes. Mei hides the dead lantern from the Great Dimming under the floorboards. Captain Rho Tanvir steps in, pays part of the debt, and offers Mei a place on his ship if she can fix the Wren's failing engine-lantern by dawn. End the chapter as Mei sees the dead lantern flicker for the first time in years.
```
Press **▶ Generate Chapter** (or `Ctrl+Enter`). In a terminal, run `ollama ps` **at each step**:

| When | Expect in `ollama ps` |
|---|---|
| Steps 1–3 (Analyze Plot, Extract Entities, Build Profiles) | the specialist |
| Step 5 (Prepare Model) | the specialist **gone** (unloaded), the writer loading |
| Step 6 (Write Chapter, the text streams) | the writer only. Note SIZE and PROCESSOR (GPU/CPU split) |
| After the draft opens | the writer stays about 5 minutes. The specialist isn't loaded |

- **Expect:**
  - The text streams in paragraphs, then the chapter opens as **Draft · Chapter 1** in an editor. Step 7 says "Waiting for your approval".
  - Mei, Rho and Cinder Wharf are used with their profiles, even if the AI would have missed them; that's what @-mentions are for.
  - Tobin (named in the plot, no profile) may be created as a new character: there's a toast "New character discovered".
- **Note:** the time to the first token, the total time, the word count, and the quality score (§5).

### T5 — Draft review: edit, AI rewrite, reload, approve
1. **Edit:** change one word in the draft.
   - **Expect:** "Saved" appears after about 1 second.
2. **AI rewrite 1:** select one paragraph that has Rho's dialogue. In the instruction box, paste this and press **Enter**:
   ```text
   make Rho's dialogue gruffer and shorter, keep the same meaning
   ```
   - **Expect:** **only the selection** changes, the text around it is untouched, and the style matches.
3. **AI rewrite 2:** select a descriptive paragraph:
   ```text
   rewrite from Mei's point of view with more sensory detail (smell, heat, sound), same events
   ```
4. **↶ Undo rewrite:**
   - **Expect:** the last rewrite is undone.
   - Press it again. **Expect:** the first rewrite is undone too.
5. **Reload the page (F5).**
   - **Expect:** the draft comes back with your edits.
6. Type a title in the title box, or leave it empty. Press **✓ Approve & save**.
   - **Expect:** "Summarizing and updating character records…". `ollama ps` shows the specialist loading, then **unloading** when it's done (`keep_alive=0`).
   - Then a "Chapter 1 saved" toast, and the chapter shows in the reading view, with pill **Ch. 1** in the history bar.
7. **⛶ Full View:**
   - **Expect:** the featured characters and locations as tags, and **Prompt used** showing your plot.
   - **↺ Use this prompt again** puts it back into the plot box. Clear the box afterwards.
8. **Profiles:** open Mei's card.
   - **Expect:** her arc notes are updated from chapter 1, and "last seen" is chapter 1.
- **Note:** the rewrite quality (did it follow the instruction? touch only the selection?), the approve time, and the summary accuracy (Full View has no summary; the profile changes show what step 7 understood).

### T6 — Chapter 2: new character, then the multi-chapter notice
Plot (insert `@Mei` and `@Rho` as mentions):
```text
On board the Wren, Mei fights to fix the engine-lantern while the ship climbs through a storm. She meets the ship's cook, Old Bartholomew Finch, a gossip who knows every rumour in the realm, and learns that Rho once served the Ember Court. Mei uses her ability to feel cracks in flames to find the fault, but has to give some of her own flame to restart the engine, which leaves her first grey ash mark. End with Rho quietly thanking her.
```
- **Expect:**
  - A toast "New character discovered: Bartholomew Finch" (and maybe a new location, the Wren).
  - The text continues from chapter 1, with the same names and facts.
  - Approve it. Mei's last seen becomes 2, and "ash mark" may show up in her profile.

Next, the **multi-chapter plot** (don't approve this one):
```text
Mei, Rho and Lin Xue travel to the Ember Court capital, sneak into the crystal vaults, discover that the Great Dimming was caused by the Court draining the realm's lanterns, escape in a sky-chase, lose the Wren, and finally relight the dead lantern in front of the whole realm.
```
- **Expect:** a notice "Plot may span N chapters. Writing Chapter 3 now.", and only one chapter is written.
- Then **🗑 Discard** the draft. **Expect:** it asks whether to delete the profiles it created; answer as you like.

### T7 — Chapter 3, and one-click mode
Turn **review off**: ⚙ Settings → untick **Review each chapter as a draft before saving** → Save. Plot (insert `@林雪` by typing `@林` and pressing **Enter**, and `@Mei` the same way):
```text
The Wren docks back at Cinder Wharf. Mei finds 林雪 hiding in Tobin's back room, healing the injured Tobin. 林雪 recognises the dead lantern and tells Mei about the relighting chant and its price. Mei must decide whether to tell Rho. End with flame-dogs sniffing at the forge door.
```
- **Expect:** no draft. Step 7 runs right after writing, the chapter saves at once, and **Ch. 3** appears.
- **Expect:** `林雪` is used correctly (the @-list matches Chinese characters).
- Turn **review back on** afterwards.

### T8 — Stopping halfway (Cancel, closed tab, Ollama stopped)
How to **stop Ollama**:
- Windows: right-click the Ollama tray icon → Quit, or run `taskkill /IM ollama.exe /F`.
- macOS: quit the menu-bar app.
- Linux: `sudo systemctl stop ollama`.

How to **start it again**: open the Ollama app, or run `ollama serve`.

Use this plot for every run (no approval needed):
```text
Night at Cinder Wharf: Mei teaches 林雪 wharf slang while repairing lanterns, and they start to trust each other.
```
1. **✕ Cancel while writing** (after some words appear).
   - **Expect:** "Generation cancelled", "Cancelled (not saved)", and **no** draft.
2. **Close or reload the tab while writing.** Then open the app again.
   - **Expect:** a draft with the words written so far. The backend log says "stopped while writing: N words kept as a draft". Discard it.
3. **Stop Ollama while writing.**
   - **Expect:** a toast "Generation error: Writer error: … The N words written so far are kept as a draft…", and the draft opens with that text.
   - Start Ollama again, then finish the text by hand or with **✨ Rewrite selection**, or discard it.
4. **Stop Ollama during Approve:** generate a draft, press **✓ Approve & save**, and stop Ollama within a second.
   - **Expect:** "Could not approve the draft: Could not finalize the chapter: … The draft is kept: approve it again to retry."
   - Start Ollama again → **✓ Approve & save** → it saves.
5. **Stop Ollama before Generate:**
   - **Expect:** a "Generation error: Pipeline error: …" toast at step 1, and nothing saved.
   - Start Ollama again afterwards.

### T9 — One AI job at a time
1. Open a **second tab** on the app. Start a generation in tab 1, then press Generate in tab 2.
   - **Expect:** "A chapter is already being generated. Wait for it to finish or cancel it."
2. While tab 1 generates, press **Refine & Save Character** in a Build tab.
   - **Expect:** a 409 message in the Build tab, and no second model loaded next to the writer (`ollama ps`).
3. While a draft is being approved in tab 1, press Generate in tab 2. (In tab 1 itself, the draft's buttons are disabled while it is approved.)
   - **Expect:** "The draft is being approved. Wait for it to finish."

### T10 — Regenerate an earlier chapter
You need at least chapters 1–3 and no open draft. For check T10.2, turn **review off** in ⚙ Settings first, and back on after this test. Open **Ch. 1** from the history bar, then press **⟳ Regenerate** in its header (or **⟳ Regenerate this chapter** in the Full View).
- **Expect:** the chapter's prompt in the plot box, a notice "⟳ Regenerating Chapter 1 …", and the button **Regenerate Chapter 1**.

Change the prompt to:
```text
Mei Ashgrove is finishing a lantern repair late at night in Cinder Wharf when Ember Court tax collectors and their flame-dogs arrive to seize Tobin's forge. This time Rho does not pay: Mei bargains with the chief collector herself, trading a perfectly repaired lantern for one week's delay, while Captain Rho Tanvir watches from the shadows and then offers her the job on the Wren. End as Mei sees the dead lantern flicker for the first time in years.
```
Press **Regenerate Chapter 1**.
- **Expect:**
  - It opens as a draft, even if review were off.
  - The output title says "New version: approving replaces the saved chapter".
- **The key quality check:** the new chapter 1 must **not** reveal or foreshadow later events: no Bartholomew Finch, no ash mark, no 林雪, no relighting chant. It has to stay consistent with them.
- Press **✓ Approve & save**.
  - **Expect:** a confirmation that says the current text is kept as an older version (the newest 5 are kept).
  - Then a warning toast: "Chapter 1 comes before chapter 3: arc notes, levels, relationships and location significance were kept as the later chapters describe them; only new abilities were added."
- Mei's card still says last seen 3: her profile is not rolled back.
- **✕ New chapter instead** (try it once, before generating) leaves regenerate mode.
- **Note:** the no-foreshadowing result (pass/fail with quotes), and the quality compared with the original.

### T11 — Older versions: read, restore, delete
1. Open **Ch. 1** → **⛶ Full View**.
   - **Expect:** **Older versions (1)** with "Replaced {date} · "title" · N words".
2. **Read:**
   - **Expect:** the badge "Chapter 1 · older version", and the old text (Rho pays the debt).
   - **← Current version** goes back.
3. **↺ Restore** (confirm):
   - **Expect:** the old text is the saved chapter 1 again, the reading view updates, and Older versions still shows 1 (now the bargaining version).
4. **🗑 Delete** that version (confirm):
   - **Expect:** "Older versions" disappears.
5. **Restore during a generation:** start a generation in another tab, then press Restore.
   - **Expect:** "Could not restore the older version: A chapter is already being generated…".
6. *Optional, slow (6 generations):* regenerate chapter 3 six times, approving each.
   - **Expect:** only **5** older versions, and the oldest has gone.
   - The backend log shows "Deleted the oldest kept version …".

### T12 — Export
**📤 Export → Export as .txt**, then **Export as .md**.
- **Expect:** chapters 1–3 in order with their titles, and `林雪` intact.
- **Expect:** no drafts and no older versions in the file.
- **Expect:** the file is named from the title, with spaces and characters like `:` `?` replaced by `_`. For example `The_Lantern_Wharf__Test_.txt`.

### T13 — Layout and accessibility basics
- Make the browser window narrow (about 400 px), or use the phone mode of the dev tools.
  - **Expect:** no horizontal scrolling. The chapter header buttons, the regenerate notice and the Full View header wrap instead of overlapping.
- Open the browser console (F12).
  - **Expect:** no red errors during T4–T11.
- Shortcuts:
  - `Alt+G` generates, `Alt+N` makes a new character, `Alt+S` opens settings, `Alt+W` opens world settings, `Esc` closes a modal.
  - The shortcuts also work with Caps Lock on.

### T14 — Short soak: 5 chapters in a row
Write chapters 4–8, approving each. Use any plots that continue the story, for example:
```text
Mei tells Rho about 林雪 and the chant; they argue, and Rho reveals what happened at the massacre he deserted from.
```
```text
Tax collectors raid the forge; 林雪 is captured and Mei must decide whether to use the dead lantern to save her.
```
- **Expect:**
  - Names, flame stages and facts stay consistent across chapters.
  - The summaries of older chapters keep the story on track; the prompt gets tiered summaries.
  - Times stay roughly constant.
- **Note:** quality drift (a §5 score per chapter), the time per chapter, and anything repeated or forgotten.

---

## 5. Prose quality rubric

Score each generated chapter or rewrite from 1 to 5 (5 is best):

| # | Criterion | What a 5 looks like |
|---|---|---|
| Q1 | **Follows the plot** | Every plot point happens, in order, and the requested ending is there |
| Q2 | **Continuity** | Names, stages, places and earlier events match the profiles and earlier chapters |
| Q3 | **Characters** | Voices match the profiles (Mei's slang, Rho's "sparrow", 林雪 formal and sparse) |
| Q4 | **No leaks** | No JSON, no prompt text, no "As an AI…", no "Chapter summary:" lines, no English headings in odd places |
| Q5 | **Prose** | Readable light-novel prose, with dialogue, pacing and a hook at the end; little repetition |
| Q6 | **Length** | A chapter-sized text (not 200 words, not cut off mid-sentence) |
| Q7 | **Rewrite precision** (T5) | Only the selection changed, the instruction was followed, and it joins the surrounding text seamlessly |
| Q8 | **No foreshadowing** (T10) | The regenerated earlier chapter shows nothing from later chapters |

## 6. Checklist

Tick each line and note the failures in your record. A check **passes** only if the "Expect" in its test happened.

**Setup**
- [ ] S1 `start.bat`, or the manual start, works, and the dependencies install
- [ ] S2 `/api/health` ok; `/api/models` says `ollama_running: true` with both models
- [ ] S3 (optional) `pytest` all pass; `ruff` clean

**T1 Settings and models**
- [ ] T1.1 The status line shows Ollama running and the model count
- [ ] T1.2 Title, genre, author and models are saved, and survive a reload
- [ ] T1.3 (optional) Pull downloads a model; a pull with Ollama stopped reports an error, not a false success

**T2–T3 Build tabs**
- [ ] T2.1 World Build merges the world description into World Settings without wiping fields
- [ ] T3.1 Three characters and one location created, with sensible profiles
- [ ] T3.2 `林雪` works on its card, View and Edit
- [ ] T3.3 Update Existing adds the scar and keeps the rest (same name, no duplicate)

**T4–T5 Chapter 1 and draft review**
- [ ] T4.1 The text streams; the chapter opens as **Draft · Chapter 1**
- [ ] T4.2 `ollama ps`: specialist at steps 1–3, unloaded at step 5, writer only at step 6
- [ ] T4.3 The @-mentioned entities are used with their profiles
- [ ] T5.1 Edits autosave; a reload brings the draft back
- [ ] T5.2 The AI rewrite changes only the selection and follows the instruction
- [ ] T5.3 Undo goes back one rewrite at a time
- [ ] T5.4 Approve saves the chapter; the specialist unloads afterwards
- [ ] T5.5 The Full View shows tags and **Prompt used**; **↺ Use this prompt again** works
- [ ] T5.6 Mei's profile is updated (arc notes, last seen 1)

**T6–T7 More chapters**
- [ ] T6.1 A new character is discovered and created
- [ ] T6.2 Chapter 2 is consistent with chapter 1
- [ ] T6.3 The multi-chapter notice appears; only one chapter is written; Discard offers to delete the new profiles
- [ ] T7.1 One-click mode saves at once, without a draft
- [ ] T7.2 The `@林` mention works, and 林雪 is written correctly

**T8 Stopping halfway**
- [ ] T8.1 Cancel while writing → no draft
- [ ] T8.2 A closed or reloaded tab while writing → the partial draft opens on the next visit
- [ ] T8.3 Ollama stopped while writing → a toast with the word count, and the partial draft opens
- [ ] T8.4 Ollama stopped during Approve → the draft is kept, and approving again works
- [ ] T8.5 Ollama stopped before Generate → a "Pipeline error" toast, and nothing saved

**T9 One job at a time**
- [ ] T9.1 A second tab's Generate gets "already being generated"
- [ ] T9.2 A refine during a generation gets 409; no second model is loaded
- [ ] T9.3 A rewrite or generation during Approve gets "being approved"

**T10–T11 Regenerate and older versions**
- [ ] T10.1 **⟳ Regenerate** loads the prompt, and the notice and button show the chapter
- [ ] T10.2 With review off, a regeneration still opens as a draft
- [ ] T10.3 **No foreshadowing** of chapters 2–3 in the new chapter 1
- [ ] T10.4 Approve asks, then shows the "comes before chapter 3" warning; Mei's last seen stays 3
- [ ] T11.1 **Older versions (1)** is listed; **Read** shows the old text; **← Current version** goes back
- [ ] T11.2 **↺ Restore** swaps the texts; the reading view updates
- [ ] T11.3 **🗑 Delete** removes the version
- [ ] T11.4 Restore during a generation is refused with a message
- [ ] T11.5 (optional) Only the newest 5 versions are kept

**T12–T14 Export, layout, soak**
- [ ] T12.1 The `.txt` and `.md` exports have all chapters in order, without drafts or versions, and a safe filename
- [ ] T13.1 A narrow window has no overlap or horizontal scroll
- [ ] T13.2 The console has no errors; the shortcuts work (also with Caps Lock)
- [ ] T14.1 Five chapters in a row stay consistent; times are stable

**Quality**
- [ ] Q Average rubric score ≥ 3.5 for chapters, and ≥ 4 for rewrite precision (Q7) and no foreshadowing (Q8)

## 7. What to send back, and cleanup

Send back (zip it):
1. **The test record** (§3) and **the checklist** with ticks. For each failure, give the check ID, what happened and a screenshot.
2. **The backend log.** Copy the NovelForge-Backend window's text, or the terminal running uvicorn. Warnings like "Skipped unreadable …", "Could not update character …" or "Specialist … reply has no JSON object" matter.
3. **The browser console** output: red errors, and "[NovelForge] Pipeline warning" lines.
4. **`ollama ps`** output from step 6 (T4), and the GPU model.
5. **A copy of the test `data/` folder.** Only the test novel: it shows the profiles, summaries and older versions as they were saved.

Defects found this way become new known issues (`KI-046` onwards) in [technical/09](technical/09-known-issues-and-tech-debt.md).

**Cleanup:**
- Close the NovelForge-Backend window, or press Ctrl+C in the terminal.
- Delete the test `data/` folder, or keep it for comparison.
- Remove models you don't need: `ollama rm <name>`.

See also: [user guide](user-guide.md) · [technical/07 Setup & Usage](technical/07-setup-and-usage.md) · [technical/08 FAQ & Troubleshooting](technical/08-faq-and-troubleshooting.md)
