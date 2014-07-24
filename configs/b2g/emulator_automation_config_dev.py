# This config contains dev values that will replace
# the values specified in the production config
# if specified like this (order matters):
# --cfg b2g/emulation_automation_config.py
# --cfg b2g/emulation_automation_config_dev.py
config = {
    "busybox_url": "https://secure.pub.build.mozilla.org/tooltool/pvt/build/sha512/0748e900821820f1a42e2f1f3fa4d9002ef257c351b9e6b78e7de0ddd0202eace351f440372fbb1ae0b7e69e8361b036f6bd3362df99e67fc585082a311fc0df",
    "xre_url": "https://secure.pub.build.mozilla.org/tooltool/pvt/build/sha512/263f4e8796c25543f64ba36e53d5c4ab8ed4d4e919226037ac0988761d34791b038ce96a8ae434f0153f9c2061204086decdbff18bdced42f3849156ae4dc9a4",
    "tooltool_servers": ["https://secure.pub.build.mozilla.org/tooltool/pvt/build/"],
    "exes": {},
    "find_links": ["http://pypi.pub.build.mozilla.org/pub",],
    "default_actions": [
        'clobber',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'run-tests',
    ],
}
