import os
import sys
from datetime import datetime

config = {

    "datazilla_urls": ['file://%s.json' % (os.path.join(os.getcwd(),
                                                        datetime.now().strftime("%Y%m%d_%H%M")))],

    "default_actions": [
        'clobber',
        'pull',
        'build',
        'create-virtualenv',
        'test',
        'baseline',
        ],
}

# need to specify pywin32 location for windows
# https://bugzilla.mozilla.org/show_bug.cgi?id=786885
# logic from https://hg.mozilla.org/build/talos/file/1c5976f92643/setup.py
if os.name == 'nt':
    base_link = "http://superb-sea2.dl.sourceforge.net/project/pywin32/pywin32/Build216/pywin32-216.%s-py%s.exe"
    python_version = '%d.%d' % sys.version_info[0:2]
    if sys.maxsize > 2**32:  # is 64bits?
        platform_name = 'win-amd64'
    else:
        platform_name = 'win32'
    config['pywin32_url'] = base_link % (platform_name, python_version)
    config['virtualenv_modules'] = ['pywin32', 'talos', 'mozinstall']
    print 'On windows: %s' % config
