from datetime import datetime, timedelta, timezone

import pytest

from tests.factories import UserFactory
from utils.streaks import update_user_streak


@pytest.fixture
def user():
    return UserFactory.build(timezone="UTC")


def test_first_activity(user):
    user.last_activity_date = None
    user.current_streak = 0

    update_user_streak(user)

    assert user.current_streak == 1
    assert user.last_activity_date is not None


def test_same_day_activity_utc(user):
    now = datetime.now(timezone.utc)
    user.last_activity_date = now - timedelta(hours=1)
    user.current_streak = 5

    update_user_streak(user)

    # Needs update because timestamp changed
    # Streak should NOT change
    assert user.current_streak == 5


def test_consecutive_day_activity_utc(user):
    # Set last activity to yesterday
    now = datetime.now(timezone.utc)
    user.last_activity_date = now - timedelta(days=1)
    user.current_streak = 5

    update_user_streak(user)

    assert user.current_streak == 6


def test_missed_day_activity_utc(user):
    # Set last activity to 2 days ago
    now = datetime.now(timezone.utc)
    user.last_activity_date = now - timedelta(days=2)
    user.current_streak = 5

    update_user_streak(user)

    assert user.current_streak == 1


def test_timezone_late_night():
    # User is in Tokyo (JST, UTC+9).
    # Case: It is Tuesday 01:00 AM in Tokyo. (Monday 16:00 UTC).
    # LAST ACTIVITY: Monday 23:00 PM in Tokyo. (Monday 14:00 UTC).
    # Result: Same day activity (Monday vs Tuesday? No wait).
    # Monday 23:00 -> Date is Monday.
    # Tuesday 01:00 -> Date is Tuesday.
    # This is a new day, so streak should increment.

    user = UserFactory.build(timezone="Asia/Tokyo")

    # "Now" = Monday 16:00 UTC = Tuesday 01:00 JST
    now_utc = datetime(2023, 10, 24, 16, 0, 0, tzinfo=timezone.utc)

    # Last activity = Monday 14:00 UTC = Monday 23:00 JST
    user.last_activity_date = datetime(2023, 10, 24, 14, 0, 0, tzinfo=timezone.utc)
    user.current_streak = 5

    update_user_streak(user, now=now_utc)

    assert user.current_streak == 6


def test_timezone_same_day():
    # User is in New York (EST, UTC-5).
    # Case: It is Monday 23:00 in NY (Tuesday 04:00 UTC).
    # LAST ACTIVITY: Monday 10:00 in NY (Monday 15:00 UTC).
    # Result: Same day, so streak should not increment.

    user = UserFactory.build(timezone="America/New_York")

    # "Now" = Tuesday 03:00 UTC = Monday 23:00 EDT
    now_utc = datetime(2023, 10, 24, 3, 0, 0, tzinfo=timezone.utc)

    # Last activity = Monday 15:00 UTC = Monday 10:00 EST
    user.last_activity_date = datetime(2023, 10, 23, 15, 0, 0, tzinfo=timezone.utc)
    user.current_streak = 5

    update_user_streak(user, now=now_utc)

    assert user.current_streak == 5
