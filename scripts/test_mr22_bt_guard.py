"""Synthetic guard policy tests; no Bluetooth reset or service changes."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parent))
import mr22_bt_guard as g

healthy={'hid':'connected','tv':'connected','pointer':True,'frames':100}


class GuardPolicyTests(unittest.TestCase):
    def test_kernel_error_age_and_identity(self):
        sample='\n'.join([
            '[  995.3] Bluetooth: hci0: Received unexpected HCI Event 0x00',
            '[  995.6] Bluetooth: hci0: Frame reassembly failed (-84)',
            '[  300.0] Bluetooth: hci0: Frame reassembly failed (-84)',
            '[  995.8] Bluetooth: hci1: Frame reassembly failed (-84)',
        ])
        self.assertEqual(g.recent_hci_error_count(sample,1000,110),2)
        self.assertEqual(g.recent_hci_error_count(sample,1300,110),0)

    def test_no_recovery_without_hci_burst(self):
        self.assertEqual(g.healthy_or_idle(healthy,healthy,0),'no-new-hci-error-burst')
        self.assertEqual(g.healthy_or_idle(healthy,healthy,5),'no-new-hci-error-burst')

    def test_no_recovery_when_remote_is_active(self):
        next_state=dict(healthy,frames=120)
        self.assertEqual(g.healthy_or_idle(healthy,next_state,12),'hid-frames-are-progressing')

    def test_no_recovery_when_pointer_off_or_tv_unavailable(self):
        self.assertEqual(g.healthy_or_idle(dict(healthy,pointer=False),healthy,12),
                         'pointer-mode-disabled')
        self.assertEqual(g.healthy_or_idle(dict(healthy,tv='offline'),healthy,12),
                         'remote-or-tv-not-ready')

    def test_confirmed_failure_policy(self):
        self.assertEqual(g.healthy_or_idle(healthy,healthy,12),'')

    def test_clean_kernel_skips_all_network_and_radio_operations(self):
        with mock.patch.object(g,'kernel_error_count',return_value=0),\
             mock.patch.object(g,'fetch_status',side_effect=AssertionError('Must not poll')),\
             mock.patch.object(g.subprocess,'run',side_effect=AssertionError('Must not recover')):
            self.assertEqual(g.run_guard(commit=True,delay=0),0)


if __name__=='__main__':
    unittest.main()
