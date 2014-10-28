from itertools import chain
import os

from mozharness.base.log import INFO

# BalrogMixin {{{1
class BalrogMixin(object):
    def _query_balrog_username(self, product=None):
        c = self.config
        if "balrog_username" in c:
            return c["balrog_username"]

        if "balrog_usernames" in c and product in c["balrog_usernames"]:
            return c["balrog_usernames"][product]

        raise KeyError("Couldn't find balrog username.")

    def submit_balrog_updates(self, release_type="nightly"):
        c = self.config
        dirs = self.query_abs_dirs()
        product = self.buildbot_config["properties"]["product"]
        props_path = os.path.join(dirs["base_work_dir"], "balrog_props.json")
        credentials_file = os.path.join(
            dirs["base_work_dir"], c["balrog_credentials_file"]
        )
        submitter_script = os.path.join(
            dirs["abs_tools_dir"], "scripts", "updates", "balrog-submitter.py"
        )
        self.set_buildbot_property(
            "hashType", c.get("hash_type", "sha512"), write_to_file=True
        )

        balrog_props = dict(properties=dict(chain(
            self.buildbot_config["properties"].items(),
            self.buildbot_properties.items(),
        )))
        self.dump_config(props_path, balrog_props)
        cmd = [
            self.query_exe("python"),
            submitter_script,
            "--build-properties", props_path,
            "--api-root", c["balrog_api_root"],
            "--username", self._query_balrog_username(product),
            "-t", release_type,
            "--credentials-file", credentials_file,
        ]
        if self._log_level_at_least(INFO):
            cmd.append("--verbose")

        self.info("Calling Balrog submission script")
        return_code = self.retry(
            self.run_command, attempts=5, args=(cmd,),
        )
        if return_code not in [0]:
            self.return_code = 1

    def lock_balrog_rules(self, rule_ids):
        c = self.config
        dirs = self.query_abs_dirs()
        submitter_script = os.path.join(
            dirs["abs_tools_dir"], "scripts", "updates", "balrog-nightly-locker.py"
        )
        credentials_file = os.path.join(
            dirs["base_work_dir"], c["balrog_credentials_file"]
        )

        cmd = [
            self.query_exe("python"),
            submitter_script,
            "--api-root", c["balrog_api_root"],
            "--username", self._query_balrog_username(),
            "--credentials-file", credentials_file,
        ]
        for r in rule_ids:
            cmd.extend(["-r", str(r)])

        if self._log_level_at_least(INFO):
            cmd.append("--verbose")

        cmd.append("lock")

        self.info("Calling Balrog rule locking script.")
        return_code = self.retry(
            self.run_command, attempts=5, args=(cmd,),
        )
        if return_code not in [0]:
            self.return_code = 1
