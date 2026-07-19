"""Installer for the Nordlys skin (weectl extension install)."""

from weecfg.extension import ExtensionInstaller


def loader():
    return NordlysInstaller()


class NordlysInstaller(ExtensionInstaller):
    def __init__(self):
        super().__init__(
            version='0.1.0',
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
                        'skins/Nordlys/index.html.tmpl',
                        'skins/Nordlys/nordlys.webmanifest.tmpl',
                        'skins/Nordlys/sw.js',
                        'skins/Nordlys/icon.svg',
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
