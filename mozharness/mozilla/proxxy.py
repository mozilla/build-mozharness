import urlparse
import socket
from mozharness.base.log import ERROR


class ProxxyMixin:
    """
    Support downloading files from HTTP caching proxies

    Current supports 'proxxy' instances, in which the caching proxy at
    proxxy.domain.com will cache requests for ftp.mozilla.org when passed requests to
    http://ftp.mozilla.org.proxxy.domain.com/...

    self.config['proxxy']['urls'] defines the list of backend hosts we are currently caching, and
    the hostname prefix to use for proxxy

    self.config['proxxy']['instances'] lists current hostnames for proxxy instances. wildcard DNS
    is set up so that *.proxxy.domain.com is a CNAME to the proxxy instance
    """

    # Default configuration. Can be overridden via self.config
    PROXXY_CONFIG = {
        "urls": [
            ('http://ftp.mozilla.org', 'ftp.mozilla.org'),
            ('https://ftp.mozilla.org', 'ftp.mozilla.org'),
            ('https://ftp-ssl.mozilla.org', 'ftp.mozilla.org'),
        ],
        "instances": [
            'proxxy.srv.releng.use1.mozilla.com',
            'proxxy.srv.releng.usw2.mozilla.com',
        ],
        "regions": [".use1.", ".usw2."],
    }

    def query_proxxy_config(self):
        cfg = self.config.get('proxxy', self.PROXXY_CONFIG)
        self.debug("proxxy config: %s" % cfg)
        return cfg

    def query_proxy_urls(self, url):
        """Return a list of proxy URLs to try, in sorted order. The original
        url is included in this list."""
        urls = [url]

        cfg = self.query_proxxy_config()
        self.info("proxxy config: %s" % cfg)

        proxxy_urls = cfg.get('urls', [])
        proxxy_instances = cfg.get('instances', [])

        url_parts = urlparse.urlsplit(url)
        url_path = url_parts.path
        if url_parts.query:
            url_path += "?" + url_parts.query
        if url_parts.fragment:
            url_path += "#" + url_parts.fragment

        for prefix, target in proxxy_urls:
            if url.startswith(prefix):
                self.info("%s matches %s" % (url, prefix))
                for instance in proxxy_instances:
                    if not self.query_is_proxxy_local(instance):
                        continue
                    new_url = "http://%s.%s%s" % (target, instance, url_path)
                    urls.insert(0, new_url)

        for u in urls:
            self.info("URL Candidate: %s" % u)
        return urls

    def query_is_proxxy_local(self, url):
        """Returns a list of base proxxy urls local to the machine"""
        fqdn = socket.getfqdn()
        regions = self.query_proxxy_config().get('regions', [])

        return any(r in fqdn and r in url for r in regions)

    def download_proxied_file(self, url, file_name=None, parent_dir=None,
                              create_parent_dir=True, error_level=ERROR,
                              exit_code=3):
        """
        Wrapper around BaseScript.download_file that understands proxies
        """
        urls = self.query_proxy_urls(url)

        for u in urls:
            self.info("trying %s" % u)
            retval = self.download_file(
                u, file_name=file_name, parent_dir=parent_dir,
                create_parent_dir=create_parent_dir, error_level=ERROR,
                exit_code=exit_code)
            if retval:
                return retval

        self.log("Failed to download from all available URLs, aborting", level=error_level, exit_code=exit_code)
        return retval
