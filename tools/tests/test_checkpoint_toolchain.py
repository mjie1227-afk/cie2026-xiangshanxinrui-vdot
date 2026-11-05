"""Regression: a GCC-12-only installation must work without a system gcc alias."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checkpoint_toolchain import prepare


class ToolchainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / 'system-bin'
        self.bin.mkdir()
        for name in ['gcc-12', 'ld', 'objcopy', 'objdump']:
            path = self.bin / ('riscv64-linux-gnu-' + name)
            path.write_text('#!/bin/sh\nexit 0\n')
            path.chmod(0o755)
        self.env = patch.dict(os.environ, {'PATH': str(self.bin)}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_versioned_only_and_idempotent(self):
        prefix, selected = prepare(self.root)
        self.assertTrue(selected['gcc'].endswith('gcc-12'))
        self.assertFalse((self.bin / 'riscv64-linux-gnu-gcc').exists())
        self.assertEqual(prepare(self.root), (prefix, selected))
        for tool, target in selected.items():
            self.assertEqual(Path(prefix + tool).resolve(), Path(target))

    def test_explicit_prefix_with_only_gcc12(self):
        os.environ['CPT_CROSS_COMPILE'] = 'riscv64-linux-gnu-'
        self.assertTrue(prepare(self.root)[1]['gcc'].endswith('gcc-12'))

    def test_invalid_explicit_prefix_does_not_silently_fallback(self):
        os.environ['CPT_CROSS_COMPILE'] = 'nonexistent-prefix-'
        with self.assertRaises(FileNotFoundError): prepare(self.root)

    def test_missing_binutils_stops_before_alias_creation(self):
        (self.bin / 'riscv64-linux-gnu-ld').unlink()
        with self.assertRaises(FileNotFoundError): prepare(self.root)
        self.assertFalse((self.root / 'work').exists())

    def test_existing_unrelated_file_is_preserved(self):
        prefix, _ = prepare(self.root)
        path = Path(prefix + 'gcc')
        path.unlink()
        path.write_text('user file')
        with self.assertRaises(ValueError): prepare(self.root)
        self.assertEqual(path.read_text(), 'user file')


if __name__ == '__main__': unittest.main()
