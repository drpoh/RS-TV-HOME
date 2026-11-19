"""Non-destructive tests: all Bluetooth and service actions are mocked."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0,os.path.dirname(__file__))
import recover_magic_remote as rm

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.paired=[(':'.join(['11','22','33','44','55','66']),'LGE MR22')]
        self.connected=[]

    @mock.patch.object(rm,'devices')
    @mock.patch.object(rm,'remote_info')
    @mock.patch.object(rm,'status_snapshot')
    def test_check_never_cycles_radio(self,status,info,devices):
        devices.side_effect=lambda kind: self.paired if kind=='Paired' else self.connected
        info.return_value={'paired':True,'trusted':True,'connected':True}
        status.return_value={'hid':'connected','tv':'connected','frames':100}
        with mock.patch.object(rm,'bluetooth_power',side_effect=AssertionError('No power change')):
            rm.recover(False)

    @mock.patch.object(rm,'devices')
    def test_other_connected_device_blocks_reset(self,devices):
        devices.side_effect=lambda kind: self.paired if kind=='Paired' else [(':'.join(['22','33','44','55','66','77']),'Speaker')]
        with self.assertRaisesRegex(RuntimeError,'Other Bluetooth'):
            rm.recover(True)

    @mock.patch.object(rm,'devices')
    def test_unpaired_or_ambiguous_remote_blocks_reset(self,devices):
        devices.side_effect=lambda kind: [] if kind=='Paired' else []
        with self.assertRaisesRegex(RuntimeError,'not uniquely paired'):
            rm.recover(True)

    @mock.patch.object(rm,'devices')
    @mock.patch.object(rm,'remote_info')
    @mock.patch.object(rm,'status_snapshot')
    def test_untrusted_device_blocks_reset(self,status,info,devices):
        devices.side_effect=lambda kind: self.paired if kind=='Paired' else []
        info.return_value={'paired':True,'trusted':False,'connected':False}
        status.return_value={}
        with self.assertRaisesRegex(RuntimeError,'bonding not ready'):
            rm.recover(True)


if __name__=='__main__':
    unittest.main()
