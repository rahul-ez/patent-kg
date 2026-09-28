"""Group repeated publication text in search results without deleting patents."""

from __future__ import annotations

import hashlib


def _normalized(value: str) -> str:
    return " ".join((value or "").lower().split())


def _content_key(hit: dict) -> str | None:
    title = _normalized(hit.get("title", ""))
    abstract = _normalized(hit.get("abstract", ""))
    if not title or not abstract:
        return None
    return hashlib.md5(f"{title} {abstract}".encode("utf-8")).hexdigest()


def group_identical_publications(hits: list[dict]) -> list[dict]:
    """Keep the highest-ranked hit for each exact text and expose matched variants.

    Input is already GNN-ranked, or semantic-ranked when GNN is unavailable.
    Only identical normalized title and *full* abstract are grouped. Distinct
    patent IDs remain available in ``related_publications`` for inspection.
    """
    groups: dict[str, dict] = {}
    seen_ids: set[str] = set()
    visible: list[dict] = []
    for hit in hits:
        patent_id = hit.get("patent_id", "")
        if patent_id and patent_id in seen_ids:
            continue
        if patent_id:
            seen_ids.add(patent_id)
        key = _content_key(hit)
        if key is not None and key in groups:
            groups[key]["related_publications"].append({
                "patent_id": patent_id,
                "url": hit.get("url", ""),
                "domain": hit.get("domain", ""),
                "jurisdiction": hit.get("jurisdiction", ""),
                "source": hit.get("source", ""),
                "semantic_score": hit.get("semantic_score"),
                "combined_score": hit.get("combined_score"),
            })
            continue
        representative = hit.copy()
        representative["related_publications"] = []
        if key is not None:
            groups[key] = representative
        visible.append(representative)
    for rank, hit in enumerate(visible, start=1):
        hit["rank"] = rank
    return visible
