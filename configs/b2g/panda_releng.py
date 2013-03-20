# This is a template config file for gaia UI tests on production.
import socket

config = {
    # Values for the foopies
    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },
    "find_links": ["http://repos/python/packages"],
    "pip_index": False,
    "buildbot_json_path": "buildprops.json",
    "test_type": "b2g-wifi-qemu-carrier-sdcard-camera-antenna-xfail+panda",
    "mobile_imaging_format": "http://mobile-imaging-%03i.p%i.releng.scl1.mozilla.com",
    "mozpool_assignee": socket.gethostname(),
    "default_actions": [
        'clobber',
        'read-buildbot-config',
        'pull',
        'create-virtualenv',
        'download-and-extract',
        'request-device',
        'run-test',
        'close-request',
    ],
}
