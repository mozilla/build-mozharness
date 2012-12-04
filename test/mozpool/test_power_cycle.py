import unittest

from mozpoolmisc import TEST_ASSIGNEE, TEST_B2GBASE, BaseMozpoolTest

class TestBlackMobileMagic(BaseMozpoolTest):
    def test_power_cycle(self):
        self.setup()

        device = 'any'
        duration = 10
        pxe_config = None
        image = 'b2g'

        device_blob = self.mph.request_device(device, TEST_ASSIGNEE, image, duration, b2gbase=TEST_B2GBASE, pxe_config=pxe_config)
        assigned_device = device_blob['request']['assigned_device']
        self.assertIsNotNone(assigned_device)

        self.mph.device_power_cycle(assigned_device, TEST_ASSIGNEE, duration, pxe_config=pxe_config)
        dd = self.mph.query_device_details(assigned_device)
        new_state = dd['state']
        self.assertEquals('pxe_power_cycling', new_state)

if __name__ == '__main__':
    unittest.main()
