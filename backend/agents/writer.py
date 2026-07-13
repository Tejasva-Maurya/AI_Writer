"""
Writer Agent — main large model (default: gemma3:12b)
Streams chapter text via SSE. Uses keep_alive=300 to stay warm between chapters.
"""
import ollama
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
