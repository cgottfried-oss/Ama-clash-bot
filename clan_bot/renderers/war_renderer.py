from __future__ import annotations

from clan_bot.renderers.html_renderer import render_html_to_png_buffer


def replace_placeholders(template: str, values: dict) -> str:
    html = template
    for key, value in values.items():
        html = html.replace("{{" + str(key) + "}}", str(value))
    return html


async def render_war_template_to_png(
    *,
    template_path: str,
    values: dict,
    width: int = 1000,
    height: int = 1400,
):
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    html = replace_placeholders(template, values)

    return await render_html_to_png_buffer(
        html,
        width=width,
        height=height,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )


async def render_final_war_template_to_png(
    *,
    template_path: str,
    values: dict,
    width: int = 1000,
    height: int = 1000,
):
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    html = replace_placeholders(template, values)

    return await render_html_to_png_buffer(
        html,
        width=width,
        height=height,
        selector="body",
        wait_ms=700,
        timeout_ms=15000,
    )