# This config contains dev values that will replace
# the values specified in the production config
# if specified like this (order matters):
# --cfg marionette/automation_emulator_config.py
# --cfg marionette/automation_emulator_config_dev.py
config = {
    "tooltool_servers": ["https://secure.pub.build.mozilla.org/tooltool/pvt/build"],
    "exes": {},
    "find_links": ["http://pypi.pub.build.mozilla.org/pub",],
    "default_actions": [
        'clobber',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-marionette',
    ],
}
