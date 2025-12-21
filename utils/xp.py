from typing import Tuple


def calculate_xp_for_next_level(level: int) -> int:
    """
    Calculates the total XP required to reach the NEXT level.
    Formula: Base (100) * (Level ^ 1.5)

    Example:
    Level 1 -> 2: 100 * (1^1.5) = 100 XP
    Level 2 -> 3: 100 * (2^1.5) = ~282 XP
    """
    return int(100 * (level**1.5))


def add_xp_to_user(
    current_xp: int, current_level: int, xp_to_add: int
) -> Tuple[int, int, bool]:
    """
    Adds XP to a user and handles leveling up.
    Returns: (new_xp, new_level, leveled_up)
    """
    new_xp = current_xp + xp_to_add
    new_level = current_level
    leveled_up = False

    while True:
        xp_needed = calculate_xp_for_next_level(new_level)
        if new_xp >= xp_needed:
            new_xp -= xp_needed
            new_level += 1
            leveled_up = True
        else:
            break

    return new_xp, new_level, leveled_up
