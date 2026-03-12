from __future__ import annotations

from typing import Iterable, List

from .nodes import Evidence


def merge_evidence(*groups: Iterable[Evidence]) -> List[Evidence]:
    """
    Merge multiple iterables of Evidence objects, de-duplicating by
    (file_path, line_start, line_end, method).
    """
    seen = set()
    merged: List[Evidence] = []
    for group in groups:
        for ev in group:
            key = (ev.file_path, ev.line_start, ev.line_end, ev.method)
            if key in seen:
                continue
            seen.add(key)
            merged.append(ev)
    return merged

