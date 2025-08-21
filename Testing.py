from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

def classify_run(now: datetime | None = None, tz: str = "America/Toronto") -> str:
    """
    Returns one of:
      - 'clWeekendCatchup'  (Monday @ 09:00)
      - 'clMorningCatchup'  (Tue–Fri @ 09:00)
      - 'clDayend'          (any day @ 16:30)
      - 'clInterval'        (otherwise)
    """
    # Resolve "now" in the desired timezone
    if now is None:
        now = datetime.now(ZoneInfo(tz))
    else:
        z = ZoneInfo(tz)
        now = now if now.tzinfo else now.replace(tzinfo=z)
        now = now.astimezone(z)

    hh = now.hour
    mm = now.minute
    wd = now.weekday()  # Monday=0 ... Sunday=6

    if hh == 9 and wd == 0:
        return "clWeekendCatchup"
    if hh == 9 and wd != 0:
        return "clMorningCatchup"
    if hh == 16 and mm == 30:
        return "clDayend"
    return "clInterval"

# Example: set your variable=
run_label = classify_run()
print(run_label)
tz = "America/Toronto"
now = datetime.now(ZoneInfo(tz))
print(now)