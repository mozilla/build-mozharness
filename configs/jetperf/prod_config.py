# This is a template config file for jetperf production

config = {

    "datazilla_urls": ['https://datazilla.mozilla.org/jetperf'],

    "exes": {
        'python': '/tools/buildbot/bin/python',
        'virtualenv': ['/tools/buildbot/bin/python', '/tools/misc-python/virtualenv.py'],
    },

    "find_links": [
        "http://repos/python/packages",
        "http://releng-puppet2.srv.releng.use1.mozilla.com/python/packages/",
        "http://releng-puppet1.srv.releng.use1.mozilla.com/python/packages/",
        "http://releng-puppet2.build.mtv1.mozilla.com/python/packages/",
        "http://releng-puppet2.srv.releng.usw2.mozilla.com/python/packages/",
        "http://releng-puppet1.srv.releng.usw2.mozilla.com/python/packages/",
        "http://releng-puppet2.srv.releng.scl3.mozilla.com/python/packages/",
        "http://releng-puppet2.build.scl1.mozilla.com/python/packages/",
        "http://puppetagain.pub.build.mozilla.org/data/python/packages/",
    ],
    "pip_index": False,

    "default_actions": [
        'clobber',
        'pull',
        'build',
        'download-and-extract',
        'create-virtualenv',
        'install',
        'test',
        'baseline',
        'report-tbpl-status'
        ],
}
