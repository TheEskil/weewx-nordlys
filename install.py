"""Installer for the Nordlys skin (weectl extension install)."""

from weecfg.extension import ExtensionInstaller


def loader():
    return NordlysInstaller()


class NordlysInstaller(ExtensionInstaller):
    def __init__(self):
        super().__init__(
            version='0.4.0',
            name='nordlys',
            description='Nordlys - a clean, minimal, config-first weewx skin',
            author='Eskil Aronsen',
            author_email='eskil.aronsen@gmail.com',
            config={
                'StdReport': {
                    'NordlysReport': {
                        'skin': 'Nordlys',
                        'enable': 'true',
                        'HTML_ROOT': 'nordlys',
                    },
                },
            },
            files=[
                ('bin/user/nordlys', ['bin/user/nordlys/__init__.py']),
                (
                    'skins/Nordlys',
                    [
                        'skins/Nordlys/skin.conf',
                        'skins/Nordlys/page.html.tmpl',
                        'skins/Nordlys/week-%Y-%m-%d.html.tmpl',
                        'skins/Nordlys/month-%Y-%m.html.tmpl',
                        'skins/Nordlys/year-%Y.html.tmpl',
                        'skins/Nordlys/climate-%Y.json.tmpl',
                        'skins/Nordlys/nordlys.webmanifest.tmpl',
                        'skins/Nordlys/robots.txt.tmpl',
                        'skins/Nordlys/sitemap.xml.tmpl',
                        'skins/Nordlys/sw.js',
                        'skins/Nordlys/icon.svg',
                        'skins/Nordlys/og-image.png',
                    ],
                ),
                (
                    'skins/Nordlys/NOAA',
                    [
                        'skins/Nordlys/NOAA/NOAA-%Y-%m.txt.tmpl',
                        'skins/Nordlys/NOAA/NOAA-%Y.txt.tmpl',
                    ],
                ),
                (
                    # Read by NordlysCardGenerator to render OG cards; not
                    # served (kept out of the web root / copy_once).
                    'skins/Nordlys/fonts',
                    [
                        'skins/Nordlys/fonts/Inter-Regular.ttf',
                        'skins/Nordlys/fonts/Inter-Bold.ttf',
                        'skins/Nordlys/fonts/OFL.txt',
                    ],
                ),
                (
                    'skins/Nordlys/dist',
                    [
                        'skins/Nordlys/dist/nordlys.js',
                        'skins/Nordlys/dist/nordlys.css',
                        'skins/Nordlys/dist/nordlys.mqtt.esm.js',
                    ],
                ),
            ],
        )
