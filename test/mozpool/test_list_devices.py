import unittest

from mozpoolmisc import MIN_TEST_DEVICES, MAX_DEVICES_TO_CHECK, BaseMozpoolTest

class QueryAllDeviceList(BaseMozpoolTest):
    def test_query_all_device_list(self):
        self.setup()

        dl = self.mph.query_all_device_list()
        self.assertIsNotNone(dl)
        self.assertIsInstance(dl, list)
        self.assertGreaterEqual(len(dl), MIN_TEST_DEVICES)
        # ensure each item in the list is a [unicode] string
        for d in dl[:MAX_DEVICES_TO_CHECK]:
            self.assertIsInstance(d, basestring)

class QueryAllDeviceDetails(BaseMozpoolTest):
    def test_query_all_device_details(self):
        self.setup()

        dl = self.mph.query_all_device_details()
        self.assertIsInstance(dl, list)
        self.assertGreaterEqual(len(dl), MIN_TEST_DEVICES)
        for d in dl[:MAX_DEVICES_TO_CHECK]:
            self.assertIsInstance(d, dict)
            for k, v in d.items():
                self.assertIsInstance(k, basestring)
                if k in ['fqdn', 'imaging_server', 'mac_address', 'name', 'relay_info', 'state']:
                    self.assertIsInstance(v, basestring)
                elif k in ['id', 'inventory_id']:
                    self.assertIsInstance(v, int)
                else:
                    self.fail('Unrecognized device key "%s"' % k)

class QueryDeviceStatus(BaseMozpoolTest):
    def test_query_device_status(self):
        self.setup()

        dl = self.mph.query_all_device_list()
        for d in dl[:MAX_DEVICES_TO_CHECK]:
            status = self.mph.query_device_status(d)
            self.assertIsNotNone(status)
            # {u'log': [], u'state': u'new'}
            self.assertIsInstance(status, dict)
            for k, v in status.items():
                self.assertIsInstance(k, basestring)
                if k == 'log':
                    self.assertIsInstance(v, list)
                elif k == 'state':
                    self.assertIsInstance(v, basestring)
                    self.assertIn(v, ['new','free','find_device','contact_lifeguard','pending','ready','pxe_power_cycling'])
                else:
                    self.fail('Unrecognized device status key "%s"' % k)

class QueryDeviceDetails(BaseMozpoolTest):
    def test_query_device_details(self):
        self.setup()

        dl = self.mph.query_all_device_list()
        for d in dl[:MAX_DEVICES_TO_CHECK]:
            details = self.mph.query_device_details(d)
            self.assertIsNotNone(details)
            self.assertEquals(details['name'], d)

        details = self.mph.query_device_details('thiswillnevermatch')
        self.assertIsNone(details)

if __name__ == '__main__':
    unittest.main()
