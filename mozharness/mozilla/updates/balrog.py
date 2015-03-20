from itertools import chain
import os

from mozharness.base.log import INFO


# BalrogMixin {{{1
class BalrogMixin(object):
    @staticmethod
    def _query_balrog_username(server_config, product=None):
        username = server_config["balrog_usernames"].get(product)
        if username:
            return username
        else:
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
        # XXX: hack alert, turn fake graphene platforms into real ones. This
        # was done more generically originally (bug 1140437), but it broke
        # flame-kk updates (bug 1141633)
        balrog_props["properties"]["platform"] = balrog_props["properties"]["platform"].replace("_graphene", "")
        self.dump_config(props_path, balrog_props)
        cmd = [
            self.query_exe("python"),
            submitter_script,
            "--build-properties", props_path,
            "-t", release_type,
            "--credentials-file", credentials_file,
        ]
        if self._log_level_at_least(INFO):
            cmd.append("--verbose")

        return_codes = []
        for server in c["balrog_servers"]:
            server_args = [
                "--api-root", server["balrog_api_root"],
                "--username", self._query_balrog_username(server, product)
            ]

            self.info("Calling Balrog submission script")
            return_code = self.retry(
                self.run_command, attempts=5, args=(cmd + server_args,),
            )
            if server["ignore_failures"]:
                self.info("Ignoring result, ignore_failures set to True")
            else:
                return_codes.append(return_code)
        # return the worst (max) code
        return max(return_codes)

    def submit_balrog_release_pusher(self, dirs):
        product = self.buildbot_config["properties"]["product"]
        cmd = [self.query_exe("python"), os.path.join(os.path.join(dirs['abs_tools_dir'], "scripts/updates/balrog-release-pusher.py"))]
        cmd.extend(["--build-properties", os.path.join(dirs["base_work_dir"], "balrog_props.json")])
        cmd.extend(["--buildbot-configs", "https://hg.mozilla.org/build/buildbot-configs"])
        cmd.extend(["--release-config", os.path.join(dirs['build_dir'], self.config.get("release_config_file"))])
        cmd.extend(["--credentials-file", os.path.join(dirs['base_work_dir'], self.config.get("balrog_credentials_file"))])

        return_codes = []
        for server in self.config["balrog_servers"]:

            server_args = [
                "--api-root", server["balrog_api_root"],
                "--username", self._query_balrog_username(server, product)
            ]

            self.info("Calling Balrog release pusher script")
            return_code = self.retry(
                self.run_command, args=(cmd + server_args,),
                kwargs={'cwd': dirs['abs_work_dir']}
            )
            if server["ignore_failures"]:
                self.info("Ignoring result, ignore_failures set to True")
            else:
                return_codes.append(return_code)
        # return the worst (max) code
        return max(return_codes)

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
            "--credentials-file", credentials_file,
        ]
        for r in rule_ids:
            cmd.extend(["-r", str(r)])

        if self._log_level_at_least(INFO):
            cmd.append("--verbose")

        return_codes = []
        for server in self.config["balrog_servers"]:

            server_args = [
                "--api-root", server["balrog_api_root"],
                "--username", self._query_balrog_username(server)
            ]

            cmd.append("lock")

            self.info("Calling Balrog rule locking script.")
            return_code = self.retry(
                self.run_command, attempts=5,
                args=(cmd + server_args + ['lock'],),
            )
            if server["ignore_failures"]:
                self.info("Ignoring result, ignore_failures set to True")
            else:
                return_codes.append(return_code)

        # use the worst (max) code
        if max(return_codes) != 0:
            self.return_code = 1
