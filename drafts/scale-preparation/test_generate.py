import importlib.util
import io
import itertools
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout

spec = importlib.util.spec_from_file_location('synthetic_generator', Path(__file__).with_name('generate.py'))
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class GeneratorTests(unittest.TestCase):
    def test_determinism_and_streaming(self):
        first = generator.rows(20, 3, 42)
        self.assertIs(iter(first), first)
        self.assertEqual(3, len(list(itertools.islice(generator.rows(10**9, 1, 42), 3))))
        self.assertEqual(list(first), list(generator.rows(20, 3, 42)))
        self.assertNotEqual(list(generator.rows(2, 1, 42)), list(generator.rows(2, 1, 43)))
        self.assertEqual({0, 1, 2}, {x[0] for x in generator.rows(20, 3, 42)})

    def test_scenarios_and_resume(self):
        base = list(generator.rows(20, 2, 1))
        self.assertEqual(base, list(generator.rows(20, 2, 1, 'unchanged')))
        self.assertNotEqual(base, list(generator.rows(20, 2, 1, 'incremental')))
        self.assertEqual(base, list(generator.rows(25, 2, 1, 'insert'))[:20])
        self.assertEqual('deleted', list(generator.rows(20, 2, 1, 'delete'))[0][3])
        self.assertEqual(base, list(generator.rows(20, 2, 1, 'restore')))
        self.assertEqual(5, len(next(generator.rows(1, 1, 1, 'structural'))))
        self.assertEqual(base, list(generator.rows(7, 2, 1)) + list(generator.rows(20, 2, 1, start=7)))

    def test_invalid_and_exact_csv_count(self):
        for args in [(-1, 1, 0), (1, 0, 0), (1, 1, 0, 'bad'), (1, 1, 0, 'initial', 2)]:
            with self.assertRaises(ValueError):
                list(generator.rows(*args))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, generator.main(['--rows', '4', '--sheets', '2']))
        self.assertEqual(5, len(output.getvalue().splitlines()))
        with self.assertRaises(SystemExit):
            generator.main(['--rows', '-1'])

    def test_broken_pipe_is_handled(self):
        class ClosedPipe(io.StringIO):
            def write(self, value):
                raise BrokenPipeError()
        original = sys.stdout
        try:
            sys.stdout = ClosedPipe()
            self.assertEqual(0, generator.main(['--rows', '1']))
            sys.stdout.close()
        finally:
            sys.stdout = original


if __name__ == '__main__':
    unittest.main()
