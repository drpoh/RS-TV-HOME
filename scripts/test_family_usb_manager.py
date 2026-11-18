"""USB mount selector unit tests; never mounts, unmounts or writes system files."""
import subprocess
import unittest
from unittest import mock
from family_usb_manager import discover, mount_options, reconcile

USB = lambda **kw: {'path': '/dev/sdz1', 'fstype': 'vfat', 'uuid': 'sample',
                   'mounted_elsewhere': False, **kw}


class MountTests(unittest.TestCase):
    def test_mount_is_explicitly_readonly(self):
        for fs in ('vfat','exfat','ntfs','ntfs3','ext4'):
            self.assertIn('ro', mount_options(fs).split(','))
            self.assertIn('nosuid', mount_options(fs).split(','))
            self.assertIn('nodev', mount_options(fs).split(','))
            self.assertIn('noexec', mount_options(fs).split(','))
        actions=[]
        def fake(cmd, timeout=12):
            actions.append(cmd)
            return subprocess.CompletedProcess(cmd,0,'','')
        result=reconcile([USB()],None,call=fake)
        self.assertEqual(result,'mounted-readonly')
        self.assertEqual(len(actions),1)
        self.assertEqual(actions[0][-2:],['/dev/sdz1','/mnt/family-usb'])

    def test_existing_readonly_remains_untouched(self):
        mount={'path':'/dev/sdz1','fstype':'vfat','readonly':True}
        with mock.patch('family_usb_manager.run',side_effect=AssertionError('mutation')):
            self.assertEqual(reconcile([USB()],mount),'existing-mount-preserved')

    def test_missing_and_multiple_devices_safe(self):
        self.assertEqual(reconcile([],None),'no-usb')
        self.assertEqual(reconcile([USB(),USB()],None),'multiple-usb-select-manually')
        self.assertEqual(reconcile([USB(mounted_elsewhere=True)],None),'no-usb')

    def test_foreign_mounted_device_is_not_unmounted(self):
        mount={'path':'/dev/nvme0n1p1','fstype':'ext4','readonly':True}
        self.assertEqual(reconcile([USB()],mount),'foreign-mount-left-alone')

    def test_same_device_path_new_uuid_requests_remount(self):
        mount={'path':'/dev/sdz1','fstype':'vfat','readonly':True}
        actions=[]
        def fake(cmd,timeout=12):
            actions.append(cmd)
            return subprocess.CompletedProcess(cmd,0,'','')
        self.assertEqual(
            reconcile([USB()],mount,call=fake,observed_uuid='old-drive'),
            'mounted-readonly'
        )
        self.assertEqual(actions[0][1],'-l')

    def test_stale_usb_detached_before_mount(self):
        actions=[]
        def fake(cmd,timeout=12):
            actions.append(cmd)
            return subprocess.CompletedProcess(cmd,0,'','')
        mount={'path':'/dev/sdy1','fstype':'vfat','readonly':True}
        status=reconcile([USB()],mount,call=fake)
        self.assertEqual(status,'mounted-readonly')
        self.assertEqual(actions[0],['/usr/bin/umount','-l','/mnt/family-usb'])
        self.assertEqual(actions[1][0:2],['/usr/bin/mount','-t'])

    def test_scan_selects_only_usb(self):
        result={'blockdevices':[
            {'name':'mmcblk0','tran':'mmc','type':'disk','children':[
                {'path':'/dev/mmcblk0p2','fstype':'ext4','type':'part'}]},
            {'name':'sda','tran':'usb','type':'disk','children':[
                {'path':'/dev/sda1','fstype':'vfat','type':'part',
                 'uuid':'example','mountpoints':[]}]}]}
        import json
        with mock.patch('family_usb_manager.run',
                        return_value=subprocess.CompletedProcess([],0,json.dumps(result),'')):
            items=discover()
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['path'],'/dev/sda1')


if __name__ == '__main__':
    unittest.main()
