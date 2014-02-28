#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import urllib
import urllib2
import base64
import traceback

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.script import BaseScript
from mozharness.mozilla.purge import PurgeMixin


class BouncerSubmitter(BaseScript, PurgeMixin):
    config_options = [
        [["--repo"], {
            "dest": "repo",
            "help": "Specify source repo, e.g. releases/mozilla-beta",
        }],
        [["--revision"], {
            "dest": "revision",
            "help": "Source revision/tag used to fetch shipped-locales",
        }],
        [["--product-name"], {
            "dest": "product-name",
            "help": "Override product if needed, e.g. for EUBallot",
        }],
        [["--version"], {
            "dest": "version",
            "help": "Current version",
        }],
        [["--previous-version"], {
            "dest": "prev_versions",
            "action": "extend",
            "help": "Previous version(s)",
        }],
        [['--platform'], {
            "dest": "platforms",
            "action": "extend",
            "help": "Buildbot platform name(s)",
        }],
        [["--bouncer-api-prefix"], {
            "dest": "bouncer-api-prefix",
            "help": "Bouncer admin API URL prefix",
        }],
        [["--credentials-file"], {
            "dest": "credentials_file",
            "help": "File containing Bouncer credentials",
        }],
        [["--no-locales"], {
            "dest": "no-locales",
            "action": "store_true",
            "default": False,
            "help": "Do not add locales, e.g. for EUBallot",
        }],
    ]

    def __init__(self, require_config_file=True):
        BaseScript.__init__(self,
                            config_options=self.config_options,
                            require_config_file=require_config_file,
                            # other stuff
                            all_actions=[
                                'clobber',
                                'download-shipped-locales',
                                'add-product',
                                'add-ssl-only-product',
                                'add-complete-updates',
                                'add-partial-updates',
                            ],
                            default_actions=[
                                'clobber',
                                'download-shipped-locales',
                                'add-product',
                                'add-ssl-only-product',
                                'add-complete-updates',
                                'add-partial-updates',
                            ],
                            )
        self.locales = None
        self.credentials = None

    def _pre_config_lock(self, rw_config):
        super(BouncerSubmitter, self)._pre_config_lock(rw_config)

        for opt in ["version", "platforms",
                    "platform-config", "credentials_file",
                    "bouncer-api-prefix"]:
            if opt not in self.config:
                self.fatal("%s must be specified" % opt)

        if not self.config["no-locales"]:
            for opt in ["revision", "repo"]:
                if opt not in self.config:
                    self.fatal("%s must be specified" % opt)

        for p in self.config["platforms"]:
            if p not in self.config["platform-config"]:
                self.fatal("%s is not in platform-config" % p)

    def query_shipped_locales_path(self):
        dirs = self.query_abs_dirs()
        return os.path.join(dirs["abs_work_dir"], "shipped-locales")

    def download_shipped_locales(self):
        if not self.config.get("shipped-locales-url"):
            self.info("Not downloading shipped-locales")
            return
        if self.config["no-locales"]:
            self.info("No need to download shipped-locales")
            return
        replace_dict = {"revision": self.config["revision"],
                        "repo": self.config["repo"]}
        url = self.config["shipped-locales-url"] % replace_dict
        dirs = self.query_abs_dirs()
        self.mkdir_p(dirs["abs_work_dir"])
        if not self.download_file(url=url,
                                  file_name=self.query_shipped_locales_path()):
            self.fatal("Unable to fetch shipped-locales from %s" % url)
        # populate the list
        self.query_shipped_locales()

    def query_shipped_locales(self):
        if self.config["no-locales"]:
            return None
        if self.locales:
            return self.locales
        content = self.read_from_file(self.query_shipped_locales_path())
        locales = []
        for line in content.splitlines():
            locale = line.split()[0]
            if locale:
                locales.append(locale)
        self.locales = locales
        return self.locales

    def query_credentials(self):
        if self.credentials:
            return self.credentials
        global_dict = {}
        local_dict = {}
        execfile(self.config["credentials_file"], global_dict, local_dict)
        self.credentials = (local_dict["tuxedoUsername"],
                            local_dict["tuxedoPassword"])
        return self.credentials

    def api_call(self, route, data):
        api_prefix = self.config["bouncer-api-prefix"]
        api_url = "%s/%s" % (api_prefix, route)
        request = urllib2.Request(api_url)
        post_data = urllib.urlencode(data, doseq=True)
        request.add_data(post_data)
        credentials = self.query_credentials()
        if credentials:
            auth = base64.encodestring('%s:%s' % credentials)
            request.add_header("Authorization", "Basic %s" % auth.strip())
        try:
            self.info("Submitting to %s" % api_url)
            self.info("POST data: %s" % post_data)
            res = urllib2.urlopen(request, timeout=60).read()
            self.info("Server response")
            self.info(res)
        except urllib2.URLError:
            traceback.print_exc(file=sys.stdout)
            self.fatal("Cannot access %s POST data:\n%s" % (api_url,
                                                            post_data))

    def api_add_product(self, product_name, ssl_only=False):
        data = {
            "product": product_name,
        }
        if self.locales:
            data["languages"] = self.locales
        if ssl_only:
            # Send "true" as a string
            data["ssl_only"] = "true"
        self.api_call("product_add/", data)

    def api_add_location(self, product_name, bouncer_platform, path):
        data = {
            "product": product_name,
            "os": bouncer_platform,
            "path": path,
        }
        self.api_call("location_add/", data)

    def add_locations(self, product_name, path_type, prev_version=None):
        platforms = self.config["platforms"]
        replace_dict = {
            "version": self.config["version"],
            "prev_version": prev_version,
        }
        for p in platforms:
            c = self.config["platform-config"][p]
            if path_type not in c:
                self.fatal("Cannot find %s for %s" % (path_type, p))
            path = c[path_type] % replace_dict
            bouncer_platform = c["bouncer-platform"]
            self.api_add_location(product_name, bouncer_platform, path)

    def add_product(self):
        version = self.config["version"]
        product_name = self.config["product-name"] % dict(version=version)
        self.api_add_product(product_name)
        self.add_locations(product_name, "installer")

    def add_ssl_only_product(self):
        if not self.config.get("add-ssl-only-product"):
            self.info("SSL-only product disabled. Skipping...")
            return
        product_name = self.config.get("ssl-only-product-name")
        if not product_name:
            self.warning("Skipping SSL-only product")
            return
        version = self.config["version"]
        product_name = product_name % dict(version=version)
        self.api_add_product(product_name, ssl_only=True)
        self.add_locations(product_name, "installer")

    def add_complete_updates(self):
        product_name = self.config.get("complete-updates-product-name")
        if not product_name:
            self.warning("Skipping complete updates")
            return
        version = self.config["version"]
        product_name = product_name % dict(version=version)
        self.api_add_product(product_name)
        self.add_locations(product_name, "complete-mar")

    def add_partial_updates(self):
        product_name = self.config.get("partial-updates-product-name")
        if not product_name:
            self.warning("Skipping partial updates")
            return
        prev_versions = self.config.get("prev_versions")
        if not prev_versions:
            self.warning("No previous version set")
            return
        version = self.config["version"]
        for prev_version in prev_versions:
            _product_name = product_name % dict(version=version,
                                                prev_version=prev_version)
            self.api_add_product(_product_name)
            self.add_locations(_product_name, "partial-mar", prev_version)


if __name__ == '__main__':
    myScript = BouncerSubmitter()
    myScript.run_and_exit()
