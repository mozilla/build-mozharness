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
        [["--version"], {
            "dest": "version",
            "help": "Current version",
        }],
        [["--previous-version"], {
            "dest": "prev_versions",
            "action": "extend",
            "help": "Previous version(s)",
        }],
        [["--bouncer-api-prefix"], {
            "dest": "bouncer-api-prefix",
            "help": "Bouncer admin API URL prefix",
        }],
        [["--credentials-file"], {
            "dest": "credentials_file",
            "help": "File containing Bouncer credentials",
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
                                'submit',
                            ],
                            default_actions=[
                                'clobber',
                                'download-shipped-locales',
                                'submit',
                            ],
                            )
        self.locales = None
        self.credentials = None

    def _pre_config_lock(self, rw_config):
        super(BouncerSubmitter, self)._pre_config_lock(rw_config)

        for opt in ["version", "credentials_file", "bouncer-api-prefix"]:
            if opt not in self.config:
                self.fatal("%s must be specified" % opt)
        if self.need_shipped_locales():
            for opt in ["shipped-locales-url", "repo", "revision"]:
                if opt not in self.config:
                    self.fatal("%s must be specified" % opt)

    def need_shipped_locales(self):
        return any(e.get("add-locales") for e in
                   self.config["products"].values())

    def query_shipped_locales_path(self):
        dirs = self.query_abs_dirs()
        return os.path.join(dirs["abs_work_dir"], "shipped-locales")

    def download_shipped_locales(self):
        if not self.need_shipped_locales():
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
        self.load_shipped_locales()

    def load_shipped_locales(self):
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
        except urllib2.HTTPError as e:
            self.critical("Cannot access %s POST data:\n%s" % (api_url,
                                                               post_data))
            traceback.print_exc(file=sys.stdout)
            self.critical("Returned page source:")
            self.fatal(e.read())
        except urllib2.URLError:
            traceback.print_exc(file=sys.stdout)
            self.fatal("Cannot access %s POST data:\n%s" % (api_url,
                                                            post_data))

    def api_add_product(self, product_name, add_locales, ssl_only=False):
        data = {
            "product": product_name,
        }
        if self.locales and add_locales:
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

    def submit(self):
        version = self.config["version"]
        for product, pr_config in sorted(self.config["products"].items()):
            self.info("Adding %s..." % product)
            product_name = pr_config["product-name"] % dict(version=version)
            self.api_add_product(
                product_name=product_name,
                add_locales=pr_config.get("add-locales"),
                ssl_only=pr_config.get("ssl-only"))
            self.info("Adding paths...")
            for platform, pl_config in sorted(pr_config["paths"].items()):
                bouncer_platform = pl_config["bouncer-platform"]
                path = pl_config["path"] % dict(version=version)
                self.info("%s (%s): %s" % (platform, bouncer_platform, path))
                self.api_add_location(product_name, bouncer_platform, path)

        # Add partial updates
        if "partials" in self.config and self.config.get("prev_versions"):
            self.submit_partials()

    def submit_partials(self):
        part_config = self.config["partials"]
        product_name = part_config["product-name"]
        version = self.config["version"]
        prev_versions = self.config.get("prev_versions")
        for prev_version in prev_versions:
            _product_name = product_name % dict(version=version,
                                                prev_version=prev_version)
            self.info("Adding partial updates for %s" % _product_name)
            self.api_add_product(
                product_name=_product_name,
                add_locales=part_config.get("add-locales"),
                ssl_only=part_config.get("ssl-only"))
            for platform, pl_config in sorted(part_config["paths"].items()):
                bouncer_platform = pl_config["bouncer-platform"]
                path = pl_config["path"] % dict(version=version,
                                                prev_version=prev_version)
                self.info("%s (%s): %s" % (platform, bouncer_platform, path))
                self.api_add_location(product_name, bouncer_platform, path)


if __name__ == '__main__':
    myScript = BouncerSubmitter()
    myScript.run_and_exit()
