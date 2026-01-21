"""Formatting helpers for user-facing output."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


DEFAULT_UNPLACED_LABEL = "(unplaced)"
DEFAULT_EMPTY_MESSAGE = "(storage is empty)"


def normalize_location_label(location: Any, *, unplaced_label: str = "склад") -> str:
    if location is None or location == "null":
        return unplaced_label
    return str(location)


def render_inventory_table(
    snapshot: Dict[str, Dict[str, int]],
    *,
    max_width: Optional[int] = None,
    unplaced_label: str = DEFAULT_UNPLACED_LABEL,
    empty_message: str = DEFAULT_EMPTY_MESSAGE,
) -> List[str]:
    if not snapshot:
        return [empty_message]

    rows = []
    for item_id in sorted(snapshot.keys()):
        locations = snapshot[item_id]
        for location_key in sorted(locations.keys(), key=lambda value: str(value)):
            qty = locations[location_key]
            item_display = _truncate_text(str(item_id), max_width)
            location_display = normalize_location_label(location_key, unplaced_label=unplaced_label)
            location_display = _truncate_text(location_display, max_width)
            rows.append((item_display, location_display, qty))

    item_width = max([len("Item")] + [len(row[0]) for row in rows])
    location_width = max([len("Location")] + [len(row[1]) for row in rows])
    qty_width = max([len("Qty")] + [len(str(row[2])) for row in rows])

    header = f"{'Item':<{item_width}}  {'Location':<{location_width}}  {'Qty':>{qty_width}}"
    separator = f"{'-' * item_width}  {'-' * location_width}  {'-' * qty_width}"
    lines = [header, separator]
    for item_display, location_display, qty in rows:
        lines.append(f"{item_display:<{item_width}}  {location_display:<{location_width}}  {qty:>{qty_width}}")
    return lines


def _truncate_text(value: str, max_width: Optional[int]) -> str:
    if max_width is None:
        return value
    if max_width < 4:
        return value[:max_width]
    return value if len(value) <= max_width else value[: max_width - 3] + "..."
