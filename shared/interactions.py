from __future__ import annotations

from typing import Any


async def safe_respond(interaction: Any, *args: Any, **kwargs: Any):
    """Respond to a slash-command interaction regardless of ack state.

    Discord requires the FIRST reply to an interaction to use
    interaction.response.* (send_message or defer), and every reply AFTER an
    ack/defer to use interaction.followup.send. Mixing them up raises errors
    ("already acknowledged" or "Unknown interaction"). This helper inspects
    interaction.response.is_done() and routes automatically, so:

      * commands can safely call defer() up front (preventing the 3-second
        timeout / 10062 errors on slow operations), and
      * every existing response call keeps working without manual conversion.

    It accepts the same positional/keyword args as both send_message and
    followup.send (content, embed, embeds, file, files, view, ephemeral, ...).
    """
    try:
        if interaction.response.is_done():
            return await interaction.followup.send(*args, **kwargs)
        return await interaction.response.send_message(*args, **kwargs)
    except Exception:
        # Best-effort fallback: if the primary path failed (e.g. a race between
        # is_done() and the actual send), try the followup channel once.
        try:
            return await interaction.followup.send(*args, **kwargs)
        except Exception:
            return None
