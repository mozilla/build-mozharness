import unittest

from mozharness.mozilla.testing.mozpool import MozpoolConflictException
from mozpoolmisc import TEST_ASSIGNEE, TEST_B2GBASE, BaseMozpoolTest

class RequestDevice(BaseMozpoolTest):
    def _force_state(self, device, assignee, pxe_config, duration, desired_state):
        dd = self.mph.query_device_details(device)
        old_state = dd['state']
        self.mph.device_state_change(device, assignee, pxe_config, duration, old_state, desired_state)
        dd = self.mph.query_device_details(device)
        new_state = dd['state']
        self.assertEquals(desired_state, new_state)

    def _test_query_all_requests(self):
        """ Get a list of request. Expects at least one request to be active.
        """
        # query all requests
        response = self.mph.query_all_requests()
        self.assertIsNotNone(response)
        self.assertGreaterEqual(1, len(response))
        for request in response['requests']:
            for request_key in request.keys():
                self.assertIn(request_key, ['assigned_device', 'assignee', 'boot_config', 'device_state',
                    'expires', 'id', 'imaging_server', 'requested_device', 'state', 'environment'])
            self.assertNotIn(request['state'], ['closed'])

        response = self.mph.query_all_requests(include_closed_requests=True)
        self.assertIsNotNone(response)
        self.assertGreaterEqual(2, len(response))
        for request in response['requests']:
            for request_key in request.keys():
                self.assertIn(request_key, ['assigned_device', 'assignee', 'boot_config', 'device_state',
                    'expires', 'id', 'imaging_server', 'requested_device', 'state', 'environment'])

    def _test_renew_request(self, request_url, old_expires):
        """ Reset the lifetime of a request.
        """
        self.mph.renew_request(request_url, 12)
        response = self.mph.query_request_details(request_url)
        expires = response['expires']
        self.assertIsNotNone(expires)
        self.assertNotEquals(expires, old_expires)

    def _test_query_request_details(self, request_url):
        """ Get request details. Expects at least one request to be active.
        """
        response = self.mph.query_request_details(request_url)
        self.assertIsNotNone(response)
        for k in response.keys():
            self.assertIn(k, ['assigned_device','assignee','boot_config','expires','id','requested_device','url'])
        old_expires = response['expires']

        self._test_renew_request(request_url, old_expires)

    def _test_close_request(self, request_url):
        """ Returns the device to the pool and deletes the request.
        """
        self.mph.close_request(request_url)

        response = self.mph.query_request_status(request_url)
        self.assertEqual(response['state'], 'closed')

    def test_request_any_device(self):
        """If 'any' device was requested, always returns 200 OK, since it will
        retry a few times if no devices are free. If a specific device is requested
        but is already assigned, returns 409 Conflict; otherwise, returns 200 OK.
        """
        self.setup()

        device = 'any'
        duration = 15
        image = 'b2g'
        pxe_config = None

        device_blob = self.mph.request_device(device, TEST_ASSIGNEE, image, duration, b2gbase=TEST_B2GBASE, pxe_config=pxe_config)
        self.assertIsNotNone(device_blob)
        request_url = device_blob['request']['url']
        self.assertIsNotNone(request_url)
        self.assertIn('http', request_url)

        self._test_query_all_requests()
        self._test_query_request_details(request_url)
        self._test_close_request(request_url)

    def test_request_conflicting_device(self):
        self.setup()

        device = 'any'
        duration = 10
        image = 'b2g'
        pxe_config = None

        device_blob = self.mph.request_device(device, TEST_ASSIGNEE, image, duration, b2gbase=TEST_B2GBASE, pxe_config=pxe_config)
        self.assertIsNotNone(device_blob)
        assigned_device = device_blob['request']['assigned_device']
        device_blob['request']['url']
        # try and request the same device
        with self.assertRaises(MozpoolConflictException):
            self.mph.request_device(assigned_device, TEST_ASSIGNEE, image, duration, b2gbase=TEST_B2GBASE, pxe_config=pxe_config)

    def test_query_request_status(self):
        self.setup()

        device = 'any'
        duration = 10
        image = 'b2g'
        pxe_config = None

        device_blob = self.mph.request_device(device, TEST_ASSIGNEE, image, duration, b2gbase=TEST_B2GBASE, pxe_config=pxe_config)
        request_url = device_blob['request']['url']

        response = self.mph.query_request_status(request_url)
        self.assertIsNotNone(response)

if __name__ == '__main__':
    unittest.main()
