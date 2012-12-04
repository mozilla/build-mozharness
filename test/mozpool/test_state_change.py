import unittest

from mozpoolmisc import TEST_DEVICE1, TEST_ASSIGNEE, BaseMozpoolTest

class TestDeviceStateChange(BaseMozpoolTest):
    def test_device_state_change(self):
        self.setup()

        device = TEST_DEVICE1
        dd = self.mph.query_device_details(device)
        old_state = dd['state']
        desired_state = 'ready'
        duration = 10
        pxe_config = None

        self.mph.device_state_change(device, TEST_ASSIGNEE, duration, old_state, desired_state, pxe_config=pxe_config)
        dd = self.mph.query_device_details(device)
        new_state = dd['state']
        self.assertEquals(desired_state, new_state)


if __name__ == '__main__':
    unittest.main()
