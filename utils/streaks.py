from datetime import datetime, timedelta, timezone
import zoneinfo
from models.users import User


def update_user_streak(user: User, now: datetime | None = None):
    """
    Updates the user's streak based on their last activity date.
    """

    try:
        user_tz = zoneinfo.ZoneInfo(user.timezone)
    except Exception:
        # Fallback to UTC if timezone is invalid
        user_tz = timezone.utc

    if now is None:
        now_utc = datetime.now(timezone.utc)
    else:
        # Ensure 'now' is UTC
        now_utc = now.astimezone(timezone.utc)

    now_user = now_utc.astimezone(user_tz)
    today = now_user.date()

    if user.last_activity_date is not None:
        # Ensure last_activity_date is timezone-aware (UTC) before converting
        last_activity_utc = user.last_activity_date.replace(tzinfo=timezone.utc)
        last_activity_user = last_activity_utc.astimezone(user_tz)
        last_date = last_activity_user.date()
    else:
        last_date = None

    if last_date is None:
        user.current_streak = 1
    elif last_date == today:
        # Do nothing to streak, but we will update the timestamp
        pass
    elif last_date == today - timedelta(days=1):
        # If the last activity was yesterday, increment the streak
        user.current_streak += 1
    else:
        user.current_streak = 1

    user.last_activity_date = now_utc
