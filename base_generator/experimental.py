from __future__ import annotations

from urllib.parse import parse_qs, urlparse

LAYOUT_ACTIONS = {"OpenLayout", "OpenPlayerLayout", "OpenClanProfile", "OpenPlayerProfile"}


def analyze_layout_link(link: str) -> dict:
    parsed = urlparse(link)
    query = parse_qs(parsed.query)
    action = (query.get("action") or [""])[0]

    findings = []
    warnings = []

    if action in LAYOUT_ACTIONS:
        findings.append(f"Detected Clash deep-link action: {action}.")

    if action in {"OpenLayout", "OpenPlayerLayout"}:
        findings.append("Appears to be a layout import/share link.")
    elif "OpenLayout" in link or "OpenPlayerLayout" in link:
        findings.append("Contains layout action text, but action parsing should be verified.")
    else:
        warnings.append("This does not look like a layout import link yet.")

    if "id" in query:
        findings.append("Contains an id/token parameter that may reference or encode layout data.")

    if "tag" in query:
        findings.append("Contains a tag parameter, likely tying the link to a player/clan/layout owner.")

    token_lengths = {key: [len(value) for value in values] for key, values in query.items()}

    return {
        "host": parsed.netloc,
        "path": parsed.path,
        "action": action or "unknown",
        "query_keys": sorted(list(query.keys())),
        "token_lengths": token_lengths,
        "findings": findings,
        "warnings": warnings,
        "notes": [
            "Supercell does not publicly document a supported layout-generation API.",
            "This tool inspects visible URL structure only; it does not decode private server tokens.",
            "If tiny in-game layout edits produce totally different id values, the link is probably server-tokenized or heavily encoded.",
        ],
    }


def compare_layout_links(link_a: str, link_b: str) -> dict:
    a = analyze_layout_link(link_a)
    b = analyze_layout_link(link_b)

    keys_a = set(a["query_keys"])
    keys_b = set(b["query_keys"])
    all_keys = keys_a | keys_b
    shared = sorted(keys_a & keys_b)

    parsed_a = parse_qs(urlparse(link_a).query)
    parsed_b = parse_qs(urlparse(link_b).query)
    changed_values = []
    identical_values = []

    for key in shared:
        value_a = parsed_a.get(key, [""])[0]
        value_b = parsed_b.get(key, [""])[0]
        if value_a == value_b:
            identical_values.append(key)
        else:
            changed_values.append({"key": key, "len_a": len(value_a), "len_b": len(value_b)})

    key_similarity = round((len(shared) / max(len(all_keys), 1)) * 100, 2)

    observations = [
        "Share the same layout twice and compare links. If the id changes, links are likely server-issued tokens.",
        "Move one building by one tile and compare. If most token values change, the format is likely encoded/signed.",
        "If only small predictable sections change, deterministic generation may be researchable.",
    ]

    return {
        "key_similarity_percent": key_similarity,
        "shared_query_keys": shared,
        "only_in_a": sorted(keys_a - keys_b),
        "only_in_b": sorted(keys_b - keys_a),
        "identical_value_keys": identical_values,
        "changed_value_keys": changed_values,
        "analysis_a": a,
        "analysis_b": b,
        "observations": observations,
    }


def official_link_generation_status() -> dict:
    return {
        "can_generate_official_link": False,
        "status": "research_required",
        "safe_current_workflow": "/basegen -> build manually in Clash -> Share Layout in Clash -> /savebase",
        "blocked_by": "No public Supercell endpoint is known for turning arbitrary placement coordinates into official import links.",
        "needed_evidence": [
            "Two links from the exact same layout shared at different times.",
            "Two links where only one building moved one tile.",
            "One link from a completely different layout.",
        ],
    }
