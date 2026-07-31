"""Unit tests for andon_light.hooks_install.

Every test patches GLOBAL_SETTINGS_PATH / PROJECT_SETTINGS_PATH to a tempdir —
none of these tests may ever touch a real ~/.claude/settings.json.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from andon_light import hooks_install


def _make_input(*answers: str):
    it = iter(answers)

    def _input(_prompt: str) -> str:
        return next(it)

    return _input


class MergeHooksTests(unittest.TestCase):
    def test_fresh_settings(self):
        merged, overwritten = hooks_install.merge_hooks({}, {"Stop": ["x"]})
        self.assertEqual(merged, {"hooks": {"Stop": ["x"]}})
        self.assertEqual(overwritten, [])

    def test_preserves_unrelated_keys(self):
        existing = {"someOtherSetting": True, "hooks": {"Stop": ["old"]}}
        merged, _ = hooks_install.merge_hooks(existing, {"SessionStart": ["new"]})
        self.assertTrue(merged["someOtherSetting"])
        self.assertEqual(merged["hooks"]["Stop"], ["old"])
        self.assertEqual(merged["hooks"]["SessionStart"], ["new"])

    def test_reports_and_overwrites_conflicting_hook(self):
        existing = {"hooks": {"Stop": ["old"]}}
        merged, overwritten = hooks_install.merge_hooks(existing, {"Stop": ["new"]})
        self.assertEqual(overwritten, ["Stop"])
        self.assertEqual(merged["hooks"]["Stop"], ["new"])


class RunTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        tmp_root = Path(self._tmpdir.name)
        self.global_path = tmp_root / "home" / ".claude" / "settings.json"
        self.project_path = tmp_root / "project" / ".claude" / "settings.json"
        self._patches = [
            mock.patch.object(hooks_install, "GLOBAL_SETTINGS_PATH", self.global_path),
            mock.patch.object(hooks_install, "PROJECT_SETTINGS_PATH", self.project_path),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)

    def test_interactive_global_scope_confirmed(self):
        result = hooks_install.run(
            scope=None,
            assume_yes=False,
            input_func=_make_input("g", "y"),
            print_func=lambda *a, **k: None,
        )
        self.assertEqual(result, 0)
        written = json.loads(self.global_path.read_text())
        self.assertIn("hooks", written)
        self.assertFalse(self.project_path.exists())

    def test_interactive_merge_declined_writes_nothing(self):
        result = hooks_install.run(
            scope="project",
            assume_yes=False,
            input_func=_make_input("n"),
            print_func=lambda *a, **k: None,
        )
        self.assertEqual(result, 1)
        self.assertFalse(self.project_path.exists())

    def test_non_interactive_requires_scope(self):
        result = hooks_install.run(
            scope=None,
            assume_yes=True,
            input_func=_make_input(),
            print_func=lambda *a, **k: None,
        )
        self.assertEqual(result, 1)
        self.assertFalse(self.global_path.exists())
        self.assertFalse(self.project_path.exists())

    def test_non_interactive_writes_without_prompting(self):
        result = hooks_install.run(
            scope="project",
            assume_yes=True,
            input_func=_make_input(),  # never called
            print_func=lambda *a, **k: None,
        )
        self.assertEqual(result, 0)
        self.assertTrue(self.project_path.exists())

    def test_conflicting_hook_warns_and_can_be_declined(self):
        self.global_path.parent.mkdir(parents=True)
        self.global_path.write_text(json.dumps({"hooks": {"Stop": ["custom"]}}))

        result = hooks_install.run(
            scope="global",
            assume_yes=False,
            input_func=_make_input("y", "n"),  # confirm merge, decline overwrite
            print_func=lambda *a, **k: None,
        )
        self.assertEqual(result, 1)
        # untouched — still the custom mapping from before the run
        self.assertEqual(json.loads(self.global_path.read_text())["hooks"]["Stop"], ["custom"])

    def test_conflicting_hook_warns_and_can_be_accepted(self):
        self.global_path.parent.mkdir(parents=True)
        self.global_path.write_text(json.dumps({"hooks": {"Stop": ["custom"]}}))

        result = hooks_install.run(
            scope="global",
            assume_yes=False,
            input_func=_make_input("y", "y"),  # confirm merge, confirm overwrite
            print_func=lambda *a, **k: None,
        )
        self.assertEqual(result, 0)
        self.assertNotEqual(
            json.loads(self.global_path.read_text())["hooks"]["Stop"], ["custom"]
        )


class PackagedSnippetDriftGuardTests(unittest.TestCase):
    """Guards against the doc-facing and packaged copies of the hooks snippet diverging.

    See hooks/README.md — hooks/settings.snippet.json is what README.md tells people
    to open and paste by hand; host/andon_light/data/settings.snippet.json is the
    machine-facing copy `andon-light install-hooks` actually reads at runtime, bundled
    because a built/installed CLI has no access to the source repo's file layout.
    """

    def test_packaged_copy_matches_doc_facing_copy(self):
        repo_root = Path(__file__).resolve().parents[2]
        doc_facing = repo_root / "hooks" / "settings.snippet.json"
        packaged = repo_root / "host" / "andon_light" / "data" / "settings.snippet.json"
        self.assertEqual(
            doc_facing.read_text(),
            packaged.read_text(),
            "hooks/settings.snippet.json and host/andon_light/data/settings.snippet.json "
            "have drifted apart — keep them byte-identical.",
        )


if __name__ == "__main__":
    unittest.main()
