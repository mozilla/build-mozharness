import unittest

from mozharness.base.python import VirtualenvMixin, virtualenv_config_options
from mozharness.base.script import BaseScript
from mozharness.mozilla.testing.mozpool import MozpoolMixin

MIN_TEST_DEVICES = 20
# reduce limit to speed up unit test runs, increase limit to increase device coverage
MAX_DEVICES_TO_CHECK = 10
TEST_DEVICE1 = 'device1'
TEST_DEVICE2 = 'device2'
TEST_ASSIGNEE = 'test@example.com'
TEST_B2GBASE = 'https://pvtbuilds.mozilla.org/pub/mozilla.org/b2g/tinderbox-builds/mozilla-central-panda/20121127133607/'

class BaseMozpoolTest(unittest.TestCase, VirtualenvMixin, MozpoolMixin, BaseScript):

    def setup(self):
        self.config_options = virtualenv_config_options + [[
            ["--mozpool-api-url"],
            {"action": "store",
             "dest": "mozpool_api_url",
             "help": "Specify the URL of the mozpool api"
            }
        ]]
        BaseScript.__init__(
            self, config_options=self.config_options,
            all_actions=[
                'create-virtualenv',
                'run-tests',
            ],
            default_actions=[
                'run-tests',
            ],
            config={
                'virtualenv_modules': ['requests'],
                'mozpool_api_url': "http://localhost:8080",
                'global_retries': 1,
            },
            require_config_file=False,
        )
        self.mph = self.query_mozpool_handler()

