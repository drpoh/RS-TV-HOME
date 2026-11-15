import unittest
from recovery import SilenceRecovery,WorkerDeadline

class RecoveryTest(unittest.TestCase):
    def test_idle_start_does_not_restart_radio(self):
        s=SilenceRecovery(0)
        self.assertIsNone(s.action(7))
        self.assertEqual(s.action(8),"reopen")
        self.assertIsNone(s.action(1000))
    def test_stalled_stream(self):
        s=SilenceRecovery(0);s.report(1)
        self.assertEqual(s.action(9),"reopen")
        self.assertIsNone(s.action(30))
        self.assertEqual(s.action(31),"radio")
        self.assertIsNone(s.action(300))
        s.report(302)
        self.assertEqual(s.action(310),"reopen")
        self.assertEqual(s.action(332),"radio")
    def test_radio_cooldown(self):
        s=SilenceRecovery(0);s.report(1)
        s.action(9);s.action(31);s.report(40)
        s.action(48)
        self.assertIsNone(s.action(70))
        self.assertEqual(s.action(151),"radio")
    def test_deadline(self):
        now=[0.0];d=WorkerDeadline(lambda:now[0])
        d.arm("tv_send",10)
        now[0]=9;self.assertFalse(d.expired())
        now[0]=11;self.assertTrue(d.expired())
        d.arm("tv_connect",75);self.assertFalse(d.expired())

if __name__=="__main__":unittest.main()
