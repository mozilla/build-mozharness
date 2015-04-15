#!/usr/bin/env python

from b2g_build import B2GBuild
import os.path

class B2GLightsaber(B2GBuild):
    all_actions = [
        'clobber',
        'checkout-sources',
        'checkout-lightsaber',
        'get-blobs',
        'update-source-manifest',
        'build',
        'build-symbols',
        'make-updates',
        'build-update-testdata',
        'prep-upload',
        'upload',
        'make-socorro-json',
        'upload-source-manifest',
        'submit-to-balrog',
    ]

    def __init__(self, require_config_file=False, config={},
                 all_actions=all_actions,
                 default_actions=B2GBuild.default_actions):
        super(B2GLightsaber, self).__init__(require_config_file, config, all_actions, default_actions)

    def checkout_lightsaber(self):
        dirs = self.query_abs_dirs()
        lightsaber_dir = os.path.join(dirs['base_work_dir'] , 'lightsaber')
        self.rmtree(lightsaber_dir)
        lightsaber_repo = {'vcs': 'tc_vcs', 'repo': 'http://github.com/fxos/lightsaber', 'dest': lightsaber_dir}
        self.vcs_checkout_repos([lightsaber_repo])
        return self.run_command(os.path.join(lightsaber_dir, 'replace-B2G.sh'), env=self.query_env(), cwd=lightsaber_dir)

# main {{{1
if __name__ == '__main__':
    myScript = B2GLightsaber()
    myScript.run_and_exit()
