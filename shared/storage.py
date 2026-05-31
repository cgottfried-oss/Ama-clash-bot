from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Callable

_file_lock = asyncio.Lock()


async def safe_load_json(path: str, default: Any | None = None) -> Any:
    """Load JSON without blocking the event loop."""
    async with _file_lock:
        fallback = {} if default is None else default
        if not os.path.exists(path):
            return fallback

        def _read() -> Any:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"[JSON LOAD ERROR] Invalid JSON in {path}: {e}")
                return fallback
            except Exception as e:
                print(f"[JSON LOAD ERROR] Could not read {path}: {e}")
                return fallback

        return await asyncio.to_thread(_read)


async def safe_save_json(path: str, data: Any) -> None:
    """Save JSON without blocking the event loop.

    Writes atomically: data is written to a temp file in the same directory,
    then os.replace() swaps it into place. os.replace is atomic on POSIX, so a
    crash mid-write can never leave a half-written (corrupt) JSON file that
    would wipe state on next load.
    """
    async with _file_lock:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        def _write() -> None:
            try:
                tmp_path = f"{path}.tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, path)
            except Exception as e:
                print(f"Error saving JSON to {path}: {e}")

        await asyncio.to_thread(_write)


async def update_json_file(path: str, update_fn: Callable[[Any], Any], default: Any | None = None) -> Any:
    """Safely load, modify, and save a JSON file under one shared lock."""
    async with _file_lock:
        fallback = {} if default is None else default
        if not os.path.exists(path):
            data = fallback
        else:
            def _read() -> Any:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except json.JSONDecodeError as e:
                    print(f"[JSON LOAD ERROR] Invalid JSON in {path}: {e}")
                    return fallback
                except Exception as e:
                    print(f"[JSON LOAD ERROR] Could not read {path}: {e}")
                    return fallback
            data = await asyncio.to_thread(_read)

        updated_data = update_fn(data)
        if updated_data is None:
            updated_data = data

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        def _write() -> None:
            try:
                tmp_path = f"{path}.tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(updated_data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, path)
            except Exception as e:
                print(f"Error saving JSON to {path}: {e}")

        await asyncio.to_thread(_write)
        return updated_data
