from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs

LAYOUT_PATTERNS = {
    "open_layout": r"OpenLayout",
    "open_player_layout": r"OpenPlayerLayout",
    "tag": r"tag=",
}


def analyze_layout_link(link: str) -> dict:
    parsed = urlparse(link)
    query = parse_qs(parsed.query)

    findings = []

    if "OpenLayout" in link:
        findings.append("Appears to be a clan/shared layout deep link.")

    if "OpenPlayerLayout" in link:
        findings.append("Appears to be a player village layout link.")

    if "id" in query:
        findings.append("Contains a layout identifier/token parameter.")

    if "tag" in query:
        findings.append("Contains a player or clan tag parameter.")

    token_lengths = []
    for values in query.values():
        for value in values:
            token_lengths.append(len(value))

    return {
        "host": parsed.netloc,
        "path": parsed.path,
        "query_keys": sorted(list(query.keys())),
        "token_lengths": token_lengths,
        "findings": findings,
        "notes": [
            "Supercell does not publicly document a supported layout-generation API.",
            "This tool only inspects visible URL structure and metadata.",
            "Generating arbitrary live import links may break across Clash updates.",
        ],
    }
