"""Exercise the actual workflow's public summary adapter without network access."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from sheets_supabase_sync import batch_cli

WORKFLOW = Path(__file__).resolve().parents[2] / '.github/workflows/scheduled-sync.yml'


def execute(summary, exit_code):
    content = WORKFLOW.read_text(encoding='utf-8')
    block = content.split('# EXECUTOR_SUMMARY_BEGIN\n')[1].split('# EXECUTOR_SUMMARY_END')[0]
    code = '\n'.join(line[10:] if line.startswith('          ') else line for line in block.splitlines())
    printed = []
    def fake_run(_args, *, emit):
        emit(json.dumps(summary))
        return exit_code
    with patch.object(batch_cli, 'run_cli', fake_run), patch('builtins.print', side_effect=printed.append), patch('logging.disable'):
        with unittest.TestCase().assertRaises(SystemExit) as result:
            exec(compile(code, 'workflow-adapter', 'exec'), {})
    return result.exception.code, json.loads(printed[-1])


class ExecutorSummaryTests(unittest.TestCase):
    def test_aggregate_partial_and_privacy(self):
        summary = dict(sources_total=1, sources_due=1, sources_executed=1, sources_failed=1,
                       sources_busy_deferred=0, sources_no_changes=0, sources_skipped=0,
                       sources=[{'source': 'synthetic-private'}])
        code, public = execute(summary, 0)
        self.assertEqual((1, 'EXECUTOR_PARTIAL_FAILURE'), (code, public['state']))
        self.assertNotIn('synthetic-private', json.dumps(public))

    def test_missing_summary_cannot_be_success(self):
        code, public = execute({}, 0)
        self.assertEqual((2, 'EXECUTOR_UNKNOWN'), (code, public['state']))

    def test_no_changes_busy_and_no_due(self):
        base = dict(sources_total=1, sources_due=1, sources_executed=1, sources_failed=0,
                    sources_busy_deferred=0, sources_no_changes=0, sources_skipped=0)
        for changes, expected in [({'sources_no_changes': 1}, 'EXECUTOR_SUCCESS'),
                                  ({'sources_busy_deferred': 1}, 'CLOCK_BUSY'),
                                  ({'sources_due': 0, 'sources_executed': 0}, 'CLOCK_SKIPPED_NO_DUE')]:
            with self.subTest(expected=expected):
                code, public = execute({**base, **changes}, 0)
                self.assertEqual((0, expected), (code, public['state']))
