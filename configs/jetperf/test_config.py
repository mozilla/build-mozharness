import os
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
