#!/usr/bin/env python
"""Bootstrap a local weewx station data area for Nordlys development.

Creates dev/weewx/ (gitignored) with:
  - a weewx.conf for a metricwx station at Aldersundet, Lurøy
  - the Nordlys report enabled, pointing at the repo's skins/ directory
  - the repo's search-list extension symlinked into bin/user/
  - a synthetic archive database (dev/gen_test_db.py)

Idempotent: safe to re-run; regenerates the database only if missing.
Run reports afterwards with:
  .venv/bin/weectl report run --config dev/weewx/weewx.conf

Usage: .venv/bin/python dev/setup.py
"""

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEWX_ROOT = os.path.join(REPO_ROOT, 'dev', 'weewx')
CONFIG_PATH = os.path.join(WEEWX_ROOT, 'weewx.conf')
DB_PATH = os.path.join(WEEWX_ROOT, 'archive', 'weewx.sdb')
WEECTL = os.path.join(REPO_ROOT, '.venv', 'bin', 'weectl')


def create_station():
    if os.path.exists(CONFIG_PATH):
        print(f'Station data area exists: {WEEWX_ROOT}')
        return
    subprocess.run(
        [
            WEECTL, 'station', 'create', WEEWX_ROOT,
            '--no-prompt',
            '--driver=weewx.drivers.simulator',
            '--location=Aldersundet, Lurøy, Norway',
            '--altitude=6,meter',
            '--latitude=66.401',
            '--longitude=13.121',
            '--units=metricwx',
            '--register=n',
        ],
        check=True,
    )


def patch_config():
    from configobj import ConfigObj

    config = ConfigObj(CONFIG_PATH, encoding='utf-8', file_error=True)
    reports = config['StdReport']
    if 'SeasonsReport' in reports:
        reports['SeasonsReport']['enable'] = 'false'
    # Note: weewx resolves skin.conf via the top-level [StdReport] SKIN_ROOT
    # only (per-report SKIN_ROOT is not honored for skin.conf), so the repo
    # skin is symlinked into the station's skins/ directory instead.
    reports['NordlysReport'] = {
        'skin': 'Nordlys',
        'enable': 'true',
        'HTML_ROOT': 'public_html/nordlys',
        # Nordic convention: report pressure as hPa (numerically = mbar).
        'Units': {'Groups': {'group_pressure': 'hPa'}},
    }
    # Log to the console so weectl report run failures are visible.
    config['Logging'] = {'root': {'handlers': ['console']}}
    config.write()
    print('Patched weewx.conf: SeasonsReport off, NordlysReport on')


def link_extension():
    links = [
        (
            os.path.join(WEEWX_ROOT, 'bin', 'user', 'nordlys'),
            os.path.join(REPO_ROOT, 'bin', 'user', 'nordlys'),
        ),
        (
            os.path.join(WEEWX_ROOT, 'skins', 'Nordlys'),
            os.path.join(REPO_ROOT, 'skins', 'Nordlys'),
        ),
    ]
    for link, target in links:
        if not os.path.islink(link):
            os.symlink(target, link)
            print(f'Symlinked {link} -> {target}')


def generate_db():
    if os.path.exists(DB_PATH):
        print(f'Database exists: {DB_PATH}')
        return
    sys.path.insert(0, os.path.join(REPO_ROOT, 'dev'))
    from gen_test_db import generate

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    count = generate(DB_PATH)
    print(f'Generated {count} synthetic archive records in {DB_PATH}')


if __name__ == '__main__':
    create_station()
    patch_config()
    link_extension()
    generate_db()
    print('Done. Next: .venv/bin/weectl report run --config dev/weewx/weewx.conf')
