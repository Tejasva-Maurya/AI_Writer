"""A chapter that stops halfway: the text written so far is kept as the draft when the writer fails or the browser
disconnects, and discarded on an explicit Cancel (plan 023, D-018).

TestClient buffers a whole streamed response, so a chapter that never ends can't be dropped halfway through it. The
disconnect and Cancel cases therefore call the routes directly and read the SSE generator: closing it is what Starlette
does when the browser goes away (its finally cancels the generation)."""
import asyncio

import pytest

import main
from conftest import BLOCK, sse_events
from managers import draft_manager
from models import GenerateChapterRequest, NovelMeta
from pipeline.chapter_pipeline import run_pipeline

SPECIALIST = NovelMeta().specialist_model
TIMEOUT = 5  # seconds: a failure must fail, never hang


# ── The writer fails ───────────────────────────────────────────
@pytest.mark.parametrize("review", [True, False], ids=["review", "one-click"])
def test_writer_failure_keeps_the_text_written_so_far(client, data_dir, fake_ollama, review):
    fake_ollama.chunks = ["Zz first half. ", "Zz more.", RuntimeError("Ollama crashed")]
    events = sse_events(client.post("/api/generate-chapter", json={"plot": "zz", "review": review}).text)

    error = events[-1]
    assert error["type"] == "error" and error.get("draft_saved") is True
    assert "Ollama crashed" in error["message"] and "5 words written so far are kept as a draft" in error["message"]
    draft = draft_manager.load()
    assert draft.full_text == "Zz first half. Zz more." and draft.plot_input == "zz"
    assert not (data_dir / "chapters" / "001.json").exists()
    assert ("chat", SPECIALIST, 0) not in fake_ollama.calls  # step 7 never runs on unfinished text


def test_writer_failure_before_any_text_saves_nothing(client, fake_ollama):
    fake_ollama.chunks = [RuntimeError("model 'zz' not found")]
    error = sse_events(client.post("/api/generate-chapter", json={"plot": "zz", "review": True}).text)[-1]
    assert error["type"] == "error" and "draft_saved" not in error
    assert draft_manager.load() is None


# ── The browser goes away vs Cancel (through the routes) ───────
async def _start_and_read_until_text():
    """POST /api/generate-chapter and read its SSE stream until the first token. Returns the stream."""
    response = await main.generate_chapter(GenerateChapterRequest(plot="zz", review=True))
    stream = response.body_iterator

    async def first_token():
        async for event in stream:
            if '"type": "token"' in event:
                return

    await asyncio.wait_for(first_token(), TIMEOUT)
    return stream


async def _generation_ended():
    task = main._generation["task"]
    await asyncio.wait_for(asyncio.wait({task}), TIMEOUT)
    assert task.cancelled() or task.done()
    assert main._busy_reason() is None  # the guard is free again


@pytest.fixture
def fresh_guard():
    main._generation["task"] = None
    main._job["kind"] = None
    yield
    main._generation["task"] = None
    main._job["kind"] = None


def test_closed_tab_keeps_the_partial_chapter(fake_ollama, fresh_guard):
    fake_ollama.chunks = ["Zz partial text. ", BLOCK]

    async def scenario():
        stream = await _start_and_read_until_text()
        await stream.aclose()  # the browser went away
        await _generation_ended()

    asyncio.run(scenario())
    assert draft_manager.load().full_text == "Zz partial text. "


def test_explicit_cancel_discards_the_partial_chapter(fake_ollama, fresh_guard):
    fake_ollama.chunks = ["Zz partial text. ", BLOCK]

    async def scenario():
        stream = await _start_and_read_until_text()
        assert await main.cancel_generation() == {"cancelled": True}
        await stream.aclose()  # the page then drops the finished stream too
        await _generation_ended()

    asyncio.run(scenario())
    assert draft_manager.load() is None


# ── run_pipeline on its own ────────────────────────────────────
def _cancel_while_writing(keep_partial_on_cancel):
    async def scenario():
        written = asyncio.Event()

        async def consume():
            async for event in run_pipeline("zz", 1, NovelMeta(), review=True,
                                            keep_partial_on_cancel=keep_partial_on_cancel):
                if '"type": "token"' in event:
                    written.set()

        task = asyncio.create_task(consume())
        waiter = asyncio.create_task(written.wait())
        done, _ = await asyncio.wait({task, waiter}, timeout=TIMEOUT, return_when=asyncio.FIRST_COMPLETED)
        assert waiter in done, task.exception() if task.done() else "no token in time"
        await asyncio.sleep(0)  # let the writer reach the blocking chunk
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, TIMEOUT)  # the cancel is not swallowed

    asyncio.run(scenario())


@pytest.mark.parametrize("keep,kept", [(lambda: True, True), (lambda: False, False), (None, False)],
                         ids=["keep", "discard", "default"])
def test_pipeline_keeps_partial_text_on_cancel_only_when_asked(fake_ollama, keep, kept):
    fake_ollama.chunks = ["Zz partial. ", BLOCK]
    _cancel_while_writing(keep)
    draft = draft_manager.load()
    assert (draft.full_text if draft else None) == ("Zz partial. " if kept else None)


def test_a_failed_save_while_cancelling_does_not_swallow_the_cancel(fake_ollama, monkeypatch):
    fake_ollama.chunks = ["Zz partial. ", BLOCK]

    def disk_full(draft):
        raise OSError("disk full")

    monkeypatch.setattr(draft_manager, "save", disk_full)
    _cancel_while_writing(lambda: True)  # raises CancelledError, not OSError or an error event
    assert draft_manager.load() is None
