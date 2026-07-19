#!/usr/bin/env python
"""Generate a synthetic weewx archive database for Nordlys development.

Writes N days of 5-minute METRICWX records with plausible, deterministic
coastal-Norway summer weather (no randomness, so regenerating the database
always produces the same data and screenshots stay comparable).

Usage: .venv/bin/python dev/gen_test_db.py <database-path> [days]
"""

import math
import sys
import time

import weewx
from weewx.manager import DaySummaryManager
import weewx.schemas.wview_extended

INTERVAL_SECONDS = 300
DEFAULT_DAYS = 7

TWO_PI = 2 * math.pi


def _day_fraction(ts):
    local = time.localtime(ts)
    return (local.tm_hour * 3600 + local.tm_min * 60 + local.tm_sec) / 86400.0


def _dewpoint(temp_c, humidity):
    a, b = 17.62, 243.12
    gamma = (a * temp_c) / (b + temp_c) + math.log(humidity / 100.0)
    return (b * gamma) / (a - gamma)


def synth_record(ts):
    day_frac = _day_fraction(ts)
    diurnal = math.sin(TWO_PI * (day_frac - 0.375))
    slow = math.sin(TWO_PI * ts / (86400 * 3.2))
    medium = math.sin(TWO_PI * ts / (86400 * 1.7))

    out_temp = 12.5 + 3.0 * diurnal + 1.5 * slow
    humidity = min(97.0, max(55.0, 80.0 - 12.0 * diurnal + 5.0 * medium))
    barometer = 1013.0 + 6.0 * slow - 2.0 * medium

    wind_speed = max(
        0.0, 4.0 + 2.0 * math.sin(TWO_PI * ts / 5400) + 2.0 * medium
    )
    wind_gust = wind_speed * 1.6
    wind_dir = (210 + 50 * medium + 15 * math.sin(TWO_PI * ts / 3600)) % 360

    # A rain band passes every ~2.6 days.
    raining = math.sin(TWO_PI * ts / (86400 * 2.6)) > 0.86
    rain = 0.2 if raining else 0.0
    rain_rate = rain * 3600 / INTERVAL_SECONDS

    # Midnight sun territory in July: long, flat solar curve.
    solar = max(0.0, math.sin(math.pi * (day_frac - 0.13) / 0.74))
    radiation = 620.0 * solar * (0.75 if raining else 1.0)
    uv = radiation / 175.0

    dewpoint = _dewpoint(out_temp, humidity)
    app_temp = out_temp - 0.7 * wind_speed * 0.35 + 0.3 * (humidity - 70) / 10

    return {
        'dateTime': ts,
        'usUnits': weewx.METRICWX,
        'interval': INTERVAL_SECONDS // 60,
        'outTemp': round(out_temp, 2),
        'outHumidity': round(humidity, 1),
        'barometer': round(barometer, 2),
        'pressure': round(barometer - 0.7, 2),
        'windSpeed': round(wind_speed, 2),
        'windGust': round(wind_gust, 2),
        'windDir': round(wind_dir, 1),
        'rain': rain,
        'rainRate': round(rain_rate, 2),
        'radiation': round(radiation, 1),
        'UV': round(uv, 2),
        'dewpoint': round(dewpoint, 2),
        'appTemp': round(app_temp, 2),
    }


def generate(db_path, days=DEFAULT_DAYS):
    now = int(time.time() / INTERVAL_SECONDS) * INTERVAL_SECONDS
    start = now - days * 86400
    records = [
        synth_record(ts)
        for ts in range(start, now + INTERVAL_SECONDS, INTERVAL_SECONDS)
    ]

    db_dict = {'driver': 'weedb.sqlite', 'database_name': db_path}
    with DaySummaryManager.open_with_create(
        db_dict, schema=weewx.schemas.wview_extended.schema
    ) as manager:
        manager.addRecord(records)
    return len(records)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    n_days = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DAYS
    count = generate(path, n_days)
    print(f'Wrote {count} records ({n_days} days) to {path}')
