# This is a template config file for gaia smoketests production.

config = {
    # Values for the foopies
    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },
    "virtualenv_path": "venv",
    "find_links": ["http://puppetagain.pub.build.mozilla.org/data/python/packages"],
    "buildbot_json_path": "buildprops.json",
    "mozpool_api_url": "http://mobile-imaging-001.p1.releng.scl1.mozilla.com",
    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'create-virtualenv',
        'download-and-extract',
        'request-device',
        'run-test',
        'close-request',
    ],
}
