from utils.xp import calculate_xp_for_next_level, add_xp_to_user


def test_xp_thresholds():
    # See formula in calculate_xp_for_next_level definition
    assert calculate_xp_for_next_level(1) == 100
    # Level 2 -> 3: 100 * 2.828 = 282
    assert calculate_xp_for_next_level(2) == 282
    # Level 5 -> 6: 100 * 11.18 = 1118
    assert calculate_xp_for_next_level(5) == 1118


def test_add_xp_no_level_up():
    # Start: 0 XP, Lvl 1. Add 50 XP. (Need 100, so no level up)
    new_xp, new_level, leveled_up = add_xp_to_user(0, 1, 50)
    assert new_xp == 50
    assert new_level == 1
    assert leveled_up is False


def test_level_up_exact():
    # Start: 90 XP, Lvl 1. Add 10 XP. (Need 100)
    new_xp, new_level, leveled_up = add_xp_to_user(90, 1, 10)
    assert new_xp == 0
    assert new_level == 2
    assert leveled_up is True


def test_level_up_overflow():
    # Start: 90 XP, Lvl 1. Add 20 XP. (Need 100)
    # Should end up with 10 XP towards Level 3, and Level 2.
    new_xp, new_level, leveled_up = add_xp_to_user(90, 1, 20)
    assert new_xp == 10
    assert new_level == 2
    assert leveled_up is True


def test_multi_level_up():
    # Start: 0 XP, Lvl 1. Add 500 XP.
    # L1->L2 Need 100. Remainder 400. Level 2.
    # L2->L3 Need 282. Remainder 118. Level 3.
    # L3->L4 Need 100 * 3^1.5 = 100 * 5.19 = 519.
    # 118 < 519. Stop.

    new_xp, new_level, leveled_up = add_xp_to_user(0, 1, 500)
    assert new_level == 3
    assert new_xp == 118  # 500 - 100 - 282
    assert leveled_up is True
