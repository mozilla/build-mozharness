#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
'''Interact with mozpool/lifeguard/bmm.
'''

import sys
import time

try:
    import simplejson as json
except ImportError:
    import json

from mozharness.base.log import LogMixin, DEBUG, ERROR, WARNING, FATAL
from mozharness.base.script import ShellMixin, OSMixin

JsonHeader = {'content-type': 'application/json'}

# TODO do something with r.status_code?
# 200 OK
# 201 Created
# 202 Accepted
# 300 Multiple Choices
# 301 Moved Permanently
# 302 Found
# 304 Not Modified
# 400 Bad Request
# 401 Unauthorized
# 403 Forbidden
# 404 Not Found
# 405 Method Not Allowed
# 409 Conflict
# 500 Server Error
# 501 Not Implemented
# 503 Service Unavailable

# Usage:
# Clients should only need to use the following Mozpool methods:
#  close_request
#  query_all_device_details
#  query_all_device_list
#  query_all_requests
#  query_device_status
#  query_request_details
#  query_request_status
#  renew_request
#  request_device

class MozpoolException(Exception):
    pass

class MozpoolConflictException(MozpoolException):
    pass

def mozpool_status_ok(status):
    if status in range(200,400):
        return True
    else:
        return False

def check_mozpool_status(status):
    if not mozpool_status_ok(status):
        if status == 409:
            raise MozpoolConflictException()
        import pprint
        raise MozpoolException('mozpool status not ok, code %s' % pprint.pformat(status))

# MozpoolHandler {{{1
class MozpoolHandler(ShellMixin, OSMixin, LogMixin):
    """ Depends on /requests/; if you don't have this installed you need to
        instantiate this after installing /requests/ via VirtualenvMixin.
    """
    def __init__(self, mozpool_api_url, mozpool_config=None, config=None,
                 log_obj=None, script_obj=None):
        self.config = config
        self.log_obj = log_obj
        super(MozpoolHandler, self).__init__()
        self.mozpool_api_url = mozpool_api_url
        self.mozpool_config = mozpool_config or {}
        self.script_obj = script_obj
        self.mozpool_auth = self.mozpool_config.get("mozpool_auth")
        self.mozpool_timeout = self.mozpool_config.get("mozpool_timeout", 60)
        try:
            site_packages_path = self.script_obj.query_python_site_packages_path()
            sys.path.append(site_packages_path)
            global requests
            requests = __import__('requests', globals(), locals(), [], -1)
        except ImportError:
            self.fatal("Can't instantiate MozpoolHandler until requests python package is installed! (VirtualenvMixin?)")

    # Helper methods {{{2
    def url_get(self, url, auth=None, params=None, num_retries=None,
                decode_json=True, error_level=FATAL, verbose_level=DEBUG,
                **kwargs):
        """Generic get output from a url method.

        This could be moved to a generic url handler object.
        """
        self.info("Request GET %s..." % url)
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.mozpool_timeout
        if kwargs.get("auth") is None and self.mozpool_auth:
            kwargs["auth"] = self.mozpool_auth
        if num_retries is None:
            num_retries = self.config.get("global_retries", 10)
        try_num = 0
        while try_num <= num_retries:
            try_num += 1
            log_level = WARNING
            if try_num == num_retries:
                log_level = error_level
            try:
                r = requests.get(url, **kwargs)
                self.info("Status code: %s" % str(r.status_code))
                if verbose_level:
                    self.log(r.text, level=verbose_level)
                if decode_json:
                    j = self.decode_json(r.text)
                    if j is not None:
                        return (j, r.status_code)
                    else:
                        self.log("Try %d: Can't decode json from %s!" % (try_num, url), level=log_level)
                else:
                    return (r.text, r.status_code)
            except requests.exceptions.RequestException, e:
                self.log("Try %d: Can't get %s: %s!" % (try_num, url, str(e)),
                         level=log_level)
            if try_num <= num_retries:
                sleep_time = 2 * try_num
                self.info("Sleeping %d..." % sleep_time)
                time.sleep(sleep_time)

    def partial_url_get(self, partial_url, **kwargs):
        return self.url_get(self.mozpool_api_url + partial_url, **kwargs)

    def decode_json(self, contents, error_level=WARNING):
        try:
            return json.loads(contents, encoding="ascii")
        except ValueError, e:
            self.log("Can't decode json: %s!" % str(e), level=error_level)
        except TypeError, e:
            self.log("Can't decode json: %s!" % str(e), level=error_level)
        else:
            self.log("Can't decode json: Unknown error!" % str(e), level=error_level)

    def url_post(self, url, data, auth=None, params=None, num_retries=None,
                 good_statuses=None, decode_json=True, error_level=ERROR,
                 verbose_level=DEBUG, **kwargs):
        """Generic post to a url method.

        This could be moved to a generic url handler object.
        """
        self.info("Request POST %s..." % url)
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = self.mozpool_timeout
        if kwargs.get("auth") is None and self.mozpool_auth:
            kwargs["auth"] = self.mozpool_auth
        if num_retries is None:
            num_retries = self.config.get("global_retries", 10)
        if good_statuses is None:
            good_statuses = [200, 201, 202, 204, 302]
        try_num = 0
        while try_num <= num_retries:
            try_num += 1
            log_level = WARNING
            if try_num == num_retries:
                log_level = error_level
            try:
                r = requests.post(url, data=data, **kwargs)
                if r.status_code in good_statuses:
                    self.info("Status code: %s" % str(r.status_code))

                    if verbose_level:
                        self.log(r.text, level=verbose_level)
                    if decode_json:
                        j = self.decode_json(r.text)
                        if j is not None:
                            return (j, r.status_code)
                        else:
                            self.log("Try %d: Can't decode json from %s!" % (try_num, url), level=log_level)
                    else:
                        return (r.text, r.status_code)
                else:
                    self.log("Bad return status from %s: %d!" % (url, r.status_code), level=error_level)
                    return (None, r.status_code)
            except requests.exceptions.RequestException, e:
                self.log("Try %d: Can't get %s: %s!" % (try_num, url, str(e)),
                         level=log_level)
            if try_num <= num_retries:
                sleep_time = 2 * try_num
                self.info("Sleeping %d..." % sleep_time)
                time.sleep(sleep_time)

    def partial_url_post(self, partial_url, **kwargs):
        return self.url_post(self.mozpool_api_url + partial_url, **kwargs)

    # TODO we could do some caching and more error checking
    # Device queries {{{2
    def query_all_device_list(self, **kwargs):
	""" returns a JSON response body whose "devices" key contains an array
            of the names of devices known to the system.  Device names can be passed
            as the id in the following device APIs.
        """
        response, status = self.partial_url_get("/api/device/list/", **kwargs)
        check_mozpool_status(status)
        return response.get("devices")

    def query_all_device_details(self, **kwargs):
        """ returns a JSON response body whose "devices" key
            contains an array of objects, each representing a single device.
            The objects have keys id, name, fqdn, invenetory_id, mac_address,
            imaging_server, and relay_info.
        """
        response, status = self.partial_url_get("/api/device/list?details=1", **kwargs)
        check_mozpool_status(status)
        return response.get("devices")

    def query_device_status(self, device, error_level=WARNING, **kwargs):
        """ returns a JSON response body whose "status" key contains
            a short string describing the last-known status of the device,
            and whose "log" key contains an array of recent log entries
            for the device.
        """
        response, status = self.partial_url_get("/api/device/%s/status/" % device,
                                    error_level=error_level, **kwargs)
        check_mozpool_status(status)
        return response

    def query_device_details(self, device_id, error_level=WARNING, **kwargs):
        devices = self.query_all_device_details(**kwargs)
        if isinstance(devices, list):
            matches = filter(lambda dd: dd['name'] == device_id, devices)
            if len(matches) != 1:
                self.log("Couldn't find %s in device list!" % device_id,
                         level=error_level)
                return
            else:
                return matches[0]
        else:
            # We shouldn't get here if query_all_device_details() FATALs...
            self.log("Invalid response from query_all_device_details()!",
                     level=error_level)

    def request_device(self, device_id, assignee, image, duration, pxe_config=None,
                       b2gbase=None, environment='any', error_level=WARNING, **kwargs):
        """ requests the given device. {id} may be "any" to let MozPool choose an
            unassigned device. The body must be a JSON object with at least the keys
            "requester", "duration", and "image". The value for "requester" takes an
            email address, for human users, or a hostname, for machine users. "duration"
            must be a value, in seconds, of the duration of the request (which can be
            renewed; see below).

            "image" specifies low-level configuration that should be done on the device
            by mozpool. Some image types will require additional parameters. Currently
            the only supported value is "b2g", for which a "b2gbase" key must also be
            present. The value of "b2gbase" must be a URL to a b2g build directory
            containing boot, system, and userdata tarballs.

            If successful, returns 200 OK with a JSON object with the key "request".
            The value of "request" is an object detailing the request, with the keys
            "assigned_device" (which is blank if mozpool is still attempting to find
            a device, "assignee", "expires", "id", "requested_device",
            and "url". The "url" attribute contains a partial URL
            for the request object and should be used in request calls, as detailed
            below. If 'any' device was requested, always returns 200 OK, since it will
            retry a few times if no devices are free. If a specific device is requested
            but is already assigned, returns 409 Conflict; otherwise, returns 200 OK.

            If a 200 OK code is returned, the client should then poll for the request's
            state (using the value of request["url"] returned in the JSON object with
            "status/" appended. A normal request will move through the states "new",
            "find_device", "contact_lifeguard", "pending", and "ready", in that order.
            When, and *only* when, the device is in the "ready" state, it is safe to be
            used by the client. Other possible states are "expired", "closed",
            "device_not_found", and "device_busy"; the assigned device (if any) is
            returned to the pool when any of these states are entered.
        """
        if image == 'b2g':
            assert b2gbase is not None, "b2gbase must be supplied when image=='b2gbase'"
        assert duration == int(duration)

        data = {'assignee': assignee, 'duration': duration, 'image': image, 'environment': environment}
        if pxe_config is not None:
            data['pxe_config'] = pxe_config
        if b2gbase is not None:
            data['b2gbase'] = b2gbase
        response, status = self.partial_url_post("/api/device/%s/request/" % device_id,
                                                    data=json.dumps(data),
                                                    headers=JsonHeader)
        check_mozpool_status(status)
        return response

    def renew_request(self, request_url, new_duration, error_level=WARNING, **kwargs):
        """ requests that the request's lifetime be updated. The request body
            should be a JSON object with the key "duration", the value of which is the
            *new* remaining time, in seconds, of the request. Returns 204 No Content.
        """
        request_url = request_url + 'renew/'
        data = {'duration': new_duration}
        response, status = self.url_post(request_url, data=json.dumps(data), headers=JsonHeader, decode_json=False)
        check_mozpool_status(status)
        return response

    def close_request(self, request_url, error_level=WARNING, **kwargs):
        """ returns the device to the pool and deletes the request. Returns
            204 No Content.
        """
        request_url = request_url + 'return/'
        data = {}
        response, status = self.url_post(request_url, data=json.dumps(data), headers=JsonHeader, decode_json=False)
        check_mozpool_status(status)
        return response

    def device_state_change(self, device, assignee, duration, old_state, new_state, pxe_config=None):
	""" conditionally set the lifeguard state of a device from old_state to
            new_state. If the current state is not old_state, the request will fail.
            The POST body is as described for `/api/device/{id}/power-cycle/`.
        """

        data = {'assignee': assignee, 'duration': duration, 'pxe_config': pxe_config}
        response, status = self.partial_url_post("/api/device/%s/state-change/%s/to/%s/" %
                                       (device, old_state, new_state), data=json.dumps(data), headers=JsonHeader)
        check_mozpool_status(status)
        return response

    def device_power_cycle(self, device, assignee, duration, pxe_config=None):
        """ initiate a power-cycle of this device. The POST body is a JSON object,
            with optional keys `pxe_config` and `boot_config`. If `pxe_config` is
            specified, then the device is configured to boot with that PXE config;
            otherwise, the device boots from its internal storage. If `boot_config` is
            supplied (as a string), it is stored for later use by the device via
            `/api/device/{id}/config/`.
        """
        data = {'assignee': assignee, 'duration': duration}
        if pxe_config is not None:
            data['pxe_config'] = pxe_config
        response, status = self.partial_url_post("/api/device/%s/power-cycle/" %
                                       (device), data=json.dumps(data), headers=JsonHeader)
        check_mozpool_status(status)
        return response

    def device_ping(self, device, error_level=WARNING, **kwargs):
        """ ping this device. Returns a JSON object with a `success` key, and
            value true or false. The ping happens synchronously, and takes around a
            half-second.
        """
        response, status = self.partial_url_get("/api/device/%s/ping/" % device,
                                    error_level=error_level, **kwargs)
        check_mozpool_status(status)
        return response

    def device_power_off(self, device, error_level=ERROR, **kwargs):
        """ initiate a power-off of this device. Use the power-cycle API to
            turn power back on.
        """
        response, status = self.partial_url_get("/api/device/%s/power-off/" % device,
                                    error_level=error_level, decode_json=False, **kwargs)
        check_mozpool_status(status)
        return response

    def query_device_log(self, device, error_level=ERROR, **kwargs):
        """ get a list of recent log lines for this device. The return value has
            a 'log' key containing a list of objects representing log lines.
        """
        response, status = self.partial_url_get("/api/device/%s/log/" % device,
                                    error_level=error_level, **kwargs)
        check_mozpool_status(status)

        return response

    def query_device_bootconfig(self, device, error_level=WARNING, **kwargs):
        """ get the boot configuration string set for this device.
        """
        response, status = self.partial_url_get("/api/device/%s/bootconfig/" % device,
                                    error_level=error_level, decode_json=False, **kwargs)
        check_mozpool_status(status)

        return response

    def query_all_requests(self, include_closed_requests=False, error_level=ERROR, **kwargs):
        """ returns a JSON response body whose "requests" key contains an array of
            objects representing all current requests. The objects have the keys id,
            assignee, assigned_device, boot_config, device_status, expires,
            imaging_server, requested_device, and state. "assigned_device" and
            "device_status" will be blank if no suitable free device has been found.
            "expires" is given in UTC. By default, closed requests are omitted. They
            can be included by giving the "include_closed" argument (with any value).

            Once a request is fulfilled using the "request" API above, all further
            actions related to the requested device should be done using that URL, which
            includes up to "/api/request/{id}/". This ensures that only one server
            handles any given request. Attempts to access that request ID on a different
            server will result in a 302 Found redirection to the correct server.

            The full paths of request APIs are presented below for clarity.

            Note that a request will be automatically terminated once it expires. The
            "renew" call should be used to extend the request lifetime.
        """
        incl_closed = ""
        if include_closed_requests:
            incl_closed = "?include_closed=1"
        response, status = self.partial_url_get("/api/request/list/%s" % incl_closed,
                                    error_level=error_level, **kwargs)
        check_mozpool_status(status)
        return response

    def query_request_status(self, request_url, error_level=WARNING, **kwargs):
        """ returns a JSON response body with keys "log" and "state". Log objects
            contain "message", "source", and "timestamp" keys. "state" is the name of
            the current state, "ready" being the state in which it is safe to use the
            device.
        """
        request_url = request_url + 'status/'
        response, status = self.url_get(request_url, error_level=error_level, **kwargs)
        check_mozpool_status(status)
        return response

    def query_request_details(self, request_url, error_level=ERROR, **kwargs):
        """ returns a JSON response body whose "request" key contains an object
            representing the given request with the keys id, device_id, assignee,
            expires, and status. The expires field is given as an ISO-formatted time.
        """
        request_url = request_url + 'details/'
        response, status = self.url_get(request_url, error_level=error_level, **kwargs)
        check_mozpool_status(status)
        return response

    def bmm_device_clear_pxe(self, device_id, error_level=ERROR, **kwargs):
	""" clear the PXE configuration for the device. Call this after a
            `power_cycle` operation with a `pxe_config` argument has been successful, so
            that any subsequent device-initiated reboots will not PXE boot.
        """
        data = {}
        response, status = self.partial_url_post("/api/device/%s/clear-pxe/" %
                                       (device_id), data=json.dumps(data), headers=JsonHeader)
        check_mozpool_status(status)
        return response

    def bmm_pxe_config_list(self, include_active_only=False, error_level=ERROR, **kwargs):
        """ returns a JSON response body whose "pxe_configs" key
            contains an array of the names of boot images known to the system.
            Bootimage names can be passed as the id in the following bootimage APIs.
            With `?active_only=1` appended, this will return only active PXE configs.
        """
        active_only = ""
        if include_active_only:
            active_only = "?active_only=1"
        response, status = self.partial_url_get("/api/bmm/pxe_config/list/%s" % active_only,
                                    error_level=error_level, **kwargs)
        check_mozpool_status(status)
        return response

    def bmm_pxe_config_details(self, device_id, error_level=ERROR, **kwargs):
        """ returns a JSON response body whose "details" key contains
            an object that provides information about this PXE config.
            The keys of this object are: "name", "version", "description" and
            "content".
        """
        response, status = self.partial_url_get("/api/bmm/pxe_config/%s/details" % device_id,
                                    error_level=error_level, **kwargs)
        check_mozpool_status(status)
        return response


# MozpoolMixin {{{1
class MozpoolMixin(object):
    mozpool_handler = None

    def query_mozpool_handler(self):
        if not self.mozpool_handler:
            if 'mozpool_api_url' not in self.config:
                self.fatal("Can't create mozpool handler without mozpool_api_url set!")
            mozpool_config = {}
            for var in ("mozpool_auth", "mozpool_timeout"):
                if self.config.get(var):
                    mozpool_config[var] = self.config[var]
            self.mozpool_handler = MozpoolHandler(
                self.config["mozpool_api_url"],
                config=self.config,
                log_obj=self.log_obj,
                script_obj=self,
            )
        return self.mozpool_handler
