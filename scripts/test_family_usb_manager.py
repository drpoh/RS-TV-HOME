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

    def test_rw_mode_mounts_new_usb_with_owner_and_safety(self):
        actions=[]
        def fake(cmd,timeout=12):
            actions.append(cmd)
            return subprocess.CompletedProcess(cmd,0,'','')
        self.assertEqual(reconcile([USB()],None,call=fake,mode='rw'),
                         'mounted-readwrite')
        command=actions[0]
        self.assertEqual(command[-2:],['/dev/sdz1','/mnt/family-usb'])
        options=command[command.index('-o')+1].split(',')
        for wanted in ('rw','nosuid','nodev','noexec','uid=1000','gid=1000'):
            self.assertIn(wanted,options)
        self.assertNotIn('ro',options)

    def test_rw_mode_remounts_existing_readonly_usb(self):
        existing={'path':'/dev/sdz1','fstype':'vfat','readonly':True}
        calls=[]
        def fake(cmd,timeout=12):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd,0,'','')
        self.assertEqual(reconcile([USB()],existing,call=fake,mode='rw'),
                         'remounted-readwrite')
        self.assertEqual(calls[0][:2],['/usr/bin/mount','-o'])
        self.assertIn('remount,rw',calls[0][2])
        self.assertEqual(calls[0][-1],'/mnt/family-usb')

    def test_rw_mode_preserves_existing_writable_usb(self):
        existing={'path':'/dev/sdz1','fstype':'vfat','readonly':False}
        def invalid(*args,**kwargs):
            raise AssertionError('No remount should run')
        self.assertEqual(reconcile([USB()],existing,call=invalid,mode='rw'),
                         'existing-mount-preserved')

    def test_ro_mode_restored_from_rw(self):
        existing={'path':'/dev/sdz1','fstype':'vfat','readonly':False}
        calls=[]
        def fake(cmd,timeout=12):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd,0,'','')
        self.assertEqual(reconcile([USB()],existing,call=fake,mode='ro'),
                         'remounted-readonly')
        self.assertIn('remount,ro',calls[0][2])

    def test_readonly_write_protected_does_not_force(self):
        existing={'path':'/dev/sdz1','fstype':'vfat','readonly':True}
        calls=[]
        def failure(cmd,timeout=12):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd,32,'','write protected')
        self.assertEqual(reconcile([USB()],existing,call=failure,mode='rw'),
                         'remount-failed')
        self.assertEqual(len(calls),1)
        self.assertNotIn('force',calls[0][2])

    def test_invalid_mode_refused(self):
        with self.assertRaises(ValueError):
            mount_options('vfat','invalid')
        with self.assertRaises(ValueError):
            reconcile([USB()],None,mode='invalid')

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
