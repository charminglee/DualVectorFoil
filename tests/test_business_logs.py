# -*- coding: utf-8 -*-
"""业务日志的限频、跨端隔离与真实错误分支回归；仅供离线测试。"""
import os
import sys
import unittest
from StringIO import StringIO

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'bp'))
from dualvectorfoil_scripts.common import diagnostics


class LogTests(unittest.TestCase):
    def setUp(self):
        self.output = StringIO()
        self.old_stdout, sys.stdout = sys.stdout, self.output
        self.old_time = diagnostics.time
        self.now = 100.0
        diagnostics.time = lambda: self.now
        self.addCleanup(setattr, sys, 'stdout', self.old_stdout)
        self.addCleanup(setattr, diagnostics, 'time', self.old_time)

    def test_1000_ticks_are_merged_and_next_report_counts_suppressed(self):
        log = diagnostics.BusinessLog('foil.server')
        for index in range(1000):
            log.sample('field_state', moved=index)
        self.assertEqual(len(self.output.getvalue().splitlines()), 1)
        self.now += 5.0
        log.sample('field_state', moved=1000)
        self.assertIn('suppressed=999', self.output.getvalue())
        self.assertIn('moved=1000', self.output.getvalue())

    def test_changed_failure_and_recovery_are_reported_immediately(self):
        log = diagnostics.BusinessLog('foil.server')
        for status in ('moving', 'palette_write_failed', 'nbt_failed', 'moving'):
            log.sample('field_state', signature=status, status=status)
        self.assertEqual(len(self.output.getvalue().splitlines()), 4)

    def test_reason_and_level_change_are_not_suppressed(self):
        log = diagnostics.BusinessLog('effect.client')
        log.sample('skip', reason='dimension')
        log.sample('skip', reason='old_stop')
        log.sample('skip', reason='old_stop', level='ERROR')
        self.assertEqual(len(self.output.getvalue().splitlines()), 3)
        self.assertIn('[effect.client][ERROR]', self.output.getvalue())

    def test_sides_and_dimensions_have_independent_streams(self):
        server = diagnostics.BusinessLog('effect.server')
        client = diagnostics.BusinessLog('effect.client')
        server.sample('sync', key='dimension:0')
        server.sample('sync', key='dimension:1')
        client.sample('sync', key='dimension:0')
        self.assertEqual(len(self.output.getvalue().splitlines()), 3)

    def test_clock_rollback_does_not_mute_logs(self):
        log = diagnostics.BusinessLog('foil.server')
        log.sample('progress')
        self.now -= 1.0
        log.sample('progress')
        self.assertEqual(len(self.output.getvalue().splitlines()), 2)

    def test_large_field_is_bounded_and_owner_logger_is_reused(self):
        owner = type('Owner', (object,), {})()
        log = diagnostics.get_log(owner, 'foil.server')
        self.assertIs(log, diagnostics.get_log(owner, 'foil.server'))
        log.event('error', level='ERROR', detail='x' * 10000)
        self.assertLess(len(self.output.getvalue()), 700)
        self.assertIn('ts=100.000', self.output.getvalue())

    def test_field_failure_includes_run_progress_and_native_mismatch(self):
        from test_palette import sandbox
        system, world, state = sandbox({(0, 1, 0): 'stone'})
        state['run_id'] = 'log_test'
        system._process_field(0, state)
        world.fail = True
        world.last_error = {'reason': 'state_mismatch', 'pos': (1, 2, 3)}
        system._process_field(0, state)
        text = self.output.getvalue()
        self.assertIn('[foil.server][ERROR] field_state', text)
        self.assertIn("run_id='log_test'", text)
        self.assertIn('state_mismatch', text)
        self.assertEqual(state['moved'], 0)



if __name__ == '__main__':
    unittest.main()
