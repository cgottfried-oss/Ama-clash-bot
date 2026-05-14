from __future__ import annotations

GRID_SIZE = 13
CENTER_INDEX = GRID_SIZE // 2


def to_center_offset(row: int, col: int) -> tuple[int, int]:
    x = col - CENTER_INDEX
    y = row - CENTER_INDEX
    return x, y


def offset_text(row: int, col: int) -> str:
    x, y = to_center_offset(row, col)
    horizontal = "center" if x == 0 else f"{abs(x)} {'right' if x > 0 else 'left'}"
    vertical = "center" if y == 0 else f"{abs(y)} {'down' if y > 0 else 'up'}"

    if x == 0 and y == 0:
        return "center"

    if x == 0:
        return vertical

    if y == 0:
        return horizontal

    return f"{horizontal}, {vertical}"
