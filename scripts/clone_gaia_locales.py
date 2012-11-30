#!/usr/bin/env python
# Mozilla licence shtuff

import sys
import os

# load modules from parent dir
sys.path.insert(1, os.path.dirname(sys.path[0]))

# import the guts
from mozharness.base.config import parse_config_file
from mozharness.base.script import BaseScript
from mozharness.base.vcs.vcsbase import VCSMixin
from mozharness.mozilla.l10n.locales import GaiaLocalesMixin

class CloneGaiaLocales(BaseScript, VCSMixin, GaiaLocalesMixin):
    config_options = [
        [["--gaia-languages-file"], {
            "dest": "gaia_languages_file",
            "help": "languages file for gaia multilocale profile",
        }],
        [["--gaia-l10n-root"], {
            "dest": "gaia_l10n_root",
            "help": "root location for gaia l10n repos",
        }],
        [["--gaia-l10n-base-dir"], {
            "dest": "gaia_l10n_base_dir",
            "help": "dir to clone l10n repos into, relative to the work directory",
        }],
        [["--gaia-l10n-vcs"], {
            "dest": "gaia_l10n_vcs",
            "help": "vcs to use for gaia l10n",
        }],
    ]

    def __init__(self, require_config_file=False):
        BaseScript.__init__(self,
                            config_options=self.config_options,
                            all_actions=[
                                'checkout-gaia-l10n',
                            ],
                            default_actions=[
                                'checkout-gaia-l10n',
                            ],
                            require_config_file=require_config_file,

                            # Default configuration
                            config={
                                'gaia_l10n_vcs': 'hg',
                                'vcs_share_base': os.environ.get('HG_SHARE_BASE_DIR'),
                            },
                            )

    def _pre_config_lock(self, rw_config):
        super(CloneGaiaLocales, self)._pre_config_lock(rw_config)

        if 'gaia_languages_file' not in self.config:
            self.fatal('Must specify --gaia-languages-file!')

        if 'gaia_l10n_root' not in self.config:
            self.fatal('Must specify --gaia-l10n-root!')

    def query_abs_dirs(self):
        if self.abs_dirs:
            return self.abs_dirs
        abs_dirs = super(CloneGaiaLocales, self).query_abs_dirs()

        c = self.config
        dirs = {
            'src': os.path.join(c['work_dir'], 'gecko'),
            'work_dir': os.path.abspath(c['work_dir']),
            'gaia_l10n_base_dir': os.path.join(os.path.abspath(c['work_dir']), self.config['gaia_l10n_base_dir'])
        }

        abs_dirs.update(dirs)
        self.abs_dirs = abs_dirs
        return self.abs_dirs

    # Actions {{{2
    def checkout_gaia_l10n(self):
        languages_file = self.config['gaia_languages_file']
        l10n_base_dir = self.query_abs_dirs()['gaia_l10n_base_dir']
        l10n_config = {
            'root': self.config['gaia_l10n_root'],
            'vcs': self.config['gaia_l10n_vcs'],
        }

        self.pull_gaia_locale_source(l10n_config, parse_config_file(languages_file).keys(), l10n_base_dir)


# main {{{1
if __name__ == '__main__':
    myScript = CloneGaiaLocales()
    myScript.run()
