from itertools import chain
import os

from mozharness.base.log import INFO

# BalrogMixin {{{1
class BalrogMixin(object):
    def submit_balrog_updates(self, release_type="nightly"):
        c = self.config
        dirs = self.query_abs_dirs()
        props_path = os.path.join(c["work_dir"], "balrog_props.json")
        credentials_file = os.path.join(
            c["work_dir"], c["balrog_credentials_file"]
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
            "--username", c["balrog_username"],
            "-t", release_type,
            "--credentials-file", credentials_file,
        ]
        if self._log_level_at_least(INFO):
            cmd.append("--verbose")

        self.info("Calling Balrog submission script")
        self.retry(
            self.run_command, args=(cmd,),
            kwargs={
                "halt_on_failure": False,
                "fatal_exit_code": 3,
            },
        )
