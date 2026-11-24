"""
Writer Agent — main large model (default: gemma3:12b)
Streams chapter text via SSE, and rewrites a selected passage of a draft (plan 019).
Uses keep_alive=300 to stay warm between chapters and rewrites.
"""
try:
    import ollama
except ImportError:  # the server must still start without it (KI-003)
    ollama = None
from typing import AsyncGenerator, Tuple

WRITER_SYSTEM = """You are a master light novel author. Write compelling, immersive fiction.

Your writing must feature:
- Vivid scene descriptions with rich sensory details (sight, sound, smell, texture)
- Deep character emotions and revealing internal monologue  
- Dynamic, personality-driven dialogue with subtext
- Proper pacing: tension → action → reflection → new tension
- Smooth scene transitions
- Powerful chapter-ending hook or cliffhanger
- Show don't tell — demonstrate character traits through actions
- Light novel style: readable, exciting, anime-influenced prose

Target: approximately 2000 words.
Write in third person limited perspective unless the world settings specify otherwise.
DO NOT add chapter numbers, chapter titles, or meta-commentary.
Begin the narrative immediately."""


async def stream_chapter(
    master_prompt: str,
    plot: str,
    chapter_number: int,
    model: str
) -> AsyncGenerator[Tuple[str, str], None]:
    """
    Async generator yielding (event_type, content) tuples.
    event_type: 'token' | 'error'
    """
    if ollama is None:
        yield ("error", "ollama Python package not installed: run pip install -r app/requirements.txt")
        return
    user_prompt = f"""{master_prompt}

=== YOUR WRITING TASK ===
Chapter Number: {chapter_number}
Chapter Plot: {plot}

Write approximately 2000 words of polished light novel prose. 
Include: character introductions (if new), scene setting, emotions, internal thoughts, 
dialogue, action, and end with a compelling hook.
Begin writing now:"""

    try:
        client = ollama.AsyncClient()
        async for chunk in await client.chat(
            model=model,
            messages=[
                {"role": "system", "content": WRITER_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            stream=True,
            keep_alive=300,
            options={"num_ctx": 32768, "temperature": 0.8, "top_p": 0.9}
        ):
            if chunk.message and chunk.message.content:
                yield ("token", chunk.message.content)
    except Exception as e:
        yield ("error", str(e))


REVISE_SYSTEM = """You are a master light novel editor. You rewrite one marked passage of a chapter draft.
Follow the author's instruction, and keep the style, tense, point of view and names of the surrounding text.
The rewritten passage must fit seamlessly between the text before and the text after it.
Output ONLY the new passage: no title, no quotes around it, no notes, no "Here is" preamble."""

# How much of the surrounding draft goes into the prompt (characters). The chapter normally fits whole;
# the limits only matter for very long drafts, so the prompt stays well inside num_ctx.
_REVISE_BEFORE_CHARS = 12000
_REVISE_AFTER_CHARS = 6000


def _clean_passage(text: str) -> str:
    """The model's reply without surrounding whitespace or a ``` fence around it."""
    text = (text or "").strip()
    if text.startswith("```") and text.endswith("```") and len(text) >= 6:
        text = text[3:-3]
        first, _, rest = text.partition("\n")
        if rest and first.strip().isalpha():  # a language tag such as ```text
            text = rest
    return text.strip()


async def revise_passage(before: str, passage: str, after: str, instruction: str, plot: str, model: str) -> str:
    """Rewrite one passage of a draft by the author's instruction (plan 019). Returns the replacement text and raises on
    failure, so an error can never end up in the chapter. Same context size as the writer, so the draft is not cut."""
    if ollama is None:
        raise RuntimeError("ollama Python package not installed: run pip install -r app/requirements.txt")
    user_prompt = f"""CHAPTER PLOT: {plot}

=== TEXT BEFORE THE PASSAGE ===
{before[-_REVISE_BEFORE_CHARS:]}

=== PASSAGE TO REWRITE ===
{passage}

=== TEXT AFTER THE PASSAGE ===
{after[:_REVISE_AFTER_CHARS]}

=== AUTHOR'S INSTRUCTION ===
{instruction}

Rewrite only the PASSAGE TO REWRITE so that it follows the instruction. Return only the new passage."""

    response = await ollama.AsyncClient().chat(
        model=model,
        messages=[
            {"role": "system", "content": REVISE_SYSTEM},
            {"role": "user", "content": user_prompt}
        ],
        keep_alive=300,
        options={"num_ctx": 32768, "temperature": 0.7, "top_p": 0.9}
    )
    return _clean_passage(response.message.content or "")
