"""Ownership and human-intervention transitions use the same locked CLI path."""
import argparse
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('checklist_task', Path(__file__).parents[2] / 'scripts/checklist_task.py')
c = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = c
spec.loader.exec_module(c)


class BlockTest(unittest.TestCase):
    def test_block_preserves_evidence_and_excludes_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checklist.md'
            path.write_text('### TEST-01 — One\n\n**Priority:** P0\n\n'
                            '**Started:** 2026-09-08T08:00:00-04:00\n**Model:** Owner\n\n'
                            '- [ ] Independent evidence\n\n### TEST-02 — Two\n\n**Priority:** P1\n\n- [ ] Fix\n')
            args = argparse.Namespace(checklist=path, lock_timeout=1, model='Owner',
                task_id='TEST-01', reason='Provide independent reference', builder=path,
                repo_root=Path(directory), no_build=True, order='high')
            with self.assertRaises(c.ChecklistError):
                c.claim(args)
            args.model = 'Other'
            with self.assertRaises(c.ChecklistError):
                c.block(args)
            args.model = 'Owner'
            c.block(args)
            tasks = c.parse_tasks(path.read_text())
            self.assertTrue(tasks[0].blocked)
            self.assertFalse(tasks[0].finished)
            self.assertEqual(tasks[0].checkbox_states, [' '])
            self.assertEqual(tasks[0].model, 'Owner')
            self.assertEqual(c.choose_claimable(tasks, 'high').task_id, 'TEST-02')
            # Even if a stale Started field is removed, human-blocked work stays excluded.
            stripped = c.parse_tasks(c.remove_claim_metadata(tasks[0].body))[0]
            with self.assertRaises(c.ChecklistError):
                c.choose_claimable([stripped], 'high')


if __name__ == '__main__':
    unittest.main()
