from __future__ import annotations

import asyncio
import io
import os
import tempfile

import discord
from playwright.async_api import async_playwright

from renderers.emoji_icons import prepare_render_html

_BROWSER = None
_PLAYWRIGHT = None
_RENDER_LOCK = asyncio.Lock()

DEFAULT_BROWSER_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-setuid-sandbox",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
]


async def _get_browser():
    global _BROWSER, _PLAYWRIGHT

    if _BROWSER is not None:
        try:
            if _BROWSER.is_connected():
                return _BROWSER
        except Exception:
            _BROWSER = None

    if _PLAYWRIGHT is None:
        _PLAYWRIGHT = await async_playwright().start()

    _BROWSER = await _PLAYWRIGHT.chromium.launch(
        headless=True,
        args=DEFAULT_BROWSER_ARGS,
    )
    return _BROWSER


async def close_playwright_renderer():
    global _BROWSER, _PLAYWRIGHT

    if _BROWSER is not None:
        try:
            await _BROWSER.close()
        except Exception:
            pass
        _BROWSER = None

    if _PLAYWRIGHT is not None:
        try:
            await _PLAYWRIGHT.stop()
        except Exception:
            pass
        _PLAYWRIGHT = None

async def render_html_to_png_bytes(
    html_content: str,
    *,
    width: int = 920,
    height: int = 980,
    selector: str = ".container",
    wait_ms: int = 500,
    device_scale_factor: int = 2,
    timeout_ms: int = 15000,
) -> bytes:
    try:
        return await asyncio.wait_for(
            _render_html_to_png_bytes_locked(
                html_content,
                width=width,
                height=height,
                selector=selector,
                wait_ms=wait_ms,
                device_scale_factor=device_scale_factor,
                timeout_ms=timeout_ms,
            ),
            timeout=45,
        )
    except asyncio.TimeoutError:
        raise RuntimeError("Playwright render timed out after 45 seconds")

async def _render_html_to_png_bytes_locked(
    html_content: str,
    *,
    width: int,
    height: int,
    selector: str,
    wait_ms: int,
    device_scale_factor: int,
    timeout_ms: int,
) -> bytes:
    async with _RENDER_LOCK:
        browser = await _get_browser()
        page = await browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=device_scale_factor,
        )

        try:
            page.set_default_timeout(timeout_ms)

            # 🔥 GLOBAL ICON + RARITY PROCESSING
            html_content = prepare_render_html(html_content)

            await page.set_content(
                html_content,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )

            if wait_ms:
                await page.wait_for_timeout(wait_ms)

            element = await page.query_selector(selector)
            if element is None and selector != ".container":
                element = await page.query_selector(".container")
            if element is None:
                element = await page.query_selector(".wrap")
            if element is None:
                element = await page.query_selector("body")

            text_check = (await element.inner_text()).strip()
            if not text_check:
                print("[PLAYWRIGHT_RENDER_WARNING] Selected element has no visible text.")
                print("[PLAYWRIGHT_RENDER_WARNING] Selector:", selector)

            return await element.screenshot(type="png", timeout=timeout_ms)

        finally:
            await page.close()
    
async def render_html_to_png_buffer(
    html_content: str,
    *,
    width: int = 920,
    height: int = 980,
    selector: str = ".container",
    wait_ms: int = 500,
    device_scale_factor: int = 2,
    timeout_ms: int = 15000,
) -> io.BytesIO:
    png = await render_html_to_png_bytes(
        html_content,
        width=width,
        height=height,
        selector=selector,
        wait_ms=wait_ms,
        device_scale_factor=device_scale_factor,
        timeout_ms=timeout_ms,
    )

    buffer = io.BytesIO(png)
    buffer.seek(0)
    return buffer


async def render_html_to_discord_file(
    html_content: str,
    filename: str,
    *,
    width: int = 920,
    height: int = 980,
    selector: str = ".container",
    wait_ms: int = 500,
    device_scale_factor: int = 2,
    timeout_ms: int = 15000,
) -> discord.File:
    png = await render_html_to_png_bytes(
        html_content,
        width=width,
        height=height,
        selector=selector,
        wait_ms=wait_ms,
        device_scale_factor=device_scale_factor,
        timeout_ms=timeout_ms,
    )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    try:
        tmp.write(png)
        tmp.flush()
        tmp.close()
        return discord.File(tmp.name, filename=filename)
    except Exception:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        raise
