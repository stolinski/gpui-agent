"""Pure fixture tests for tree-driver helpers. No GPUI launch, real key or network."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'python'))
from gpui_agent.runner import ScriptPolicy
from gpui_agent.jev import PolicyError


def snapshot(nodes=()):
    return {'surface': {'controls': list(nodes)}}


def node(id='ax-123'):
    return {'id': id, 'label': 'Increment', 'enabled': True, 'actions': ['click']}


class ScriptDiscoveryTests(unittest.TestCase):
    def test_missing_wait_target_does_not_consume_step(self):
        policy = ScriptPolicy([{'operation': 'click', 'label': 'Increment', 'waitFor': True}])
        self.assertEqual(policy.choose(snapshot(), '', [], []), {'operation': 'wait'})
        self.assertEqual(policy.choose(snapshot([node('ax-987')]), '', [], []),
                         {'operation': 'click', 'target': 'ax-987'})
        self.assertEqual(policy.choose(snapshot(), '', [], []), {'operation': 'done'})

    def test_ambiguous_wait_target_still_refuses(self):
        policy = ScriptPolicy([{'operation': 'click', 'label': 'Increment', 'waitFor': True}])
        with self.assertRaises(PolicyError):
            policy.choose(snapshot([node(), node('ax-456')]), '', [], [])

    def test_missing_target_without_explicit_wait_refuses(self):
        policy = ScriptPolicy([{'operation': 'click', 'label': 'Increment'}])
        with self.assertRaises(PolicyError):
            policy.choose(snapshot(), '', [], [])


class PreparationTests(unittest.TestCase):
    @staticmethod
    def module():
        spec = importlib.util.spec_from_file_location('prepare_tree_test', ROOT / 'prepare-native-tree.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_patch_anchor_mismatch_preserves_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.rs'
            path.write_text('duplicated duplicated')
            with self.assertRaises(ValueError):
                self.module().replace(path, 'duplicated', 'changed')
            self.assertEqual(path.read_text(), 'duplicated duplicated')

    def test_wrong_archive_refuses_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upstream = root / 'registry/src/index/gpui-pre-0.3.7'
            upstream.mkdir(parents=True)
            archive = root / 'registry/cache/index/gpui-pre-0.3.7.crate'
            archive.parent.mkdir(parents=True)
            archive.write_bytes(b'fixture-only bad archive')
            (root / 'patches').mkdir()
            (root / 'patches/upstream.json').write_text(json.dumps({'checksum': '0' * 64}))
            module = self.module()
            with patch.object(module, 'HERE', root):
                with self.assertRaises(ValueError):
                    module.prepare(root / 'output', upstream)
            self.assertFalse((root / 'output').exists())
            self.assertEqual(archive.read_bytes(), b'fixture-only bad archive')


if __name__ == '__main__':
    unittest.main()
