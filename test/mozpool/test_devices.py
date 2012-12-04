import unittest

from mozpoolmisc import TEST_DEVICE1, BaseMozpoolTest

class TestBlackMobileMagic(BaseMozpoolTest):
    def test_device_ping(self):
        self.setup()

        device = TEST_DEVICE1

        response = self.mph.device_ping(device)
        self.assertIn(response['success'], [True, False])

    def test_device_power_off(self):
        self.setup()

        device = TEST_DEVICE1

        self.mph.device_power_off(device)

    def test_query_device_log(self):
        self.setup()

        device = TEST_DEVICE1

        response = self.mph.query_device_log(device)
        self.assertIsNotNone(response)
        self.assertIsInstance(response['log'], list)

    def test_query_device_bootconfig(self):
        self.setup()

        device = TEST_DEVICE1

        response = self.mph.query_device_bootconfig(device)
        self.assertIsNotNone(response)

    def _test_bmm_pxe_config_details(self, pxe_config):
        self.setup()

        response = self.mph.bmm_pxe_config_details(pxe_config)
        #{"details": {"active": true, "name": "image1", "contents": "some config", "description": "test img"}}
        self.assertIsInstance(response['details'], dict)
        for k in response['details'].keys():
             self.assertIn(k, ['active','name','contents','description'])

    def test_bmm_pxe_config_list(self):
        self.setup()

        response = self.mph.bmm_pxe_config_list(include_active_only=True)
        self.assertIsNotNone(response)
        response = self.mph.bmm_pxe_config_list(include_active_only=False)
        self.assertIsNotNone(response)
        pxe_configs = response['pxe_configs']
        self.assertIsInstance(pxe_configs, list)
        for pxe_config in pxe_configs:
            self._test_bmm_pxe_config_details(pxe_config)

    def test_bmm_device_clear_pxe(self):
        self.setup()

        device = TEST_DEVICE1

        self.mph.bmm_device_clear_pxe(device)


if __name__ == '__main__':
    unittest.main()
