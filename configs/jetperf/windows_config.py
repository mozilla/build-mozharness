# This is a template config file for jetperf production

config = {

    "datazilla_urls": ['http://10.8.73.32/jetperf/load_test'],

    "virtualenv_path": 'c:/talos-slave/test/build/venv',
    "virtualenv_python_dll": 'c:/mozilla-build/python25/python25.dll',

    "exes": {
        'python': 'c:/mozilla-build/python25/python',
        'virtualenv': ['c:/mozilla-build/python25/python', 'c:/mozilla-build/buildbotve/virtualenv.py'],
        'hg': 'c:/mozilla-build/hg/hg',
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
