"""Regression tests for the OHS Labs static site builder."""

import contextlib
import io
import json
import pathlib
import re
import sys
import tempfile
import unittest
from unittest import mock

WEBSITE_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(WEBSITE_ROOT) not in sys.path:
    sys.path.insert(0, str(WEBSITE_ROOT))

import build  # noqa: E402


EXPECTED_SLUGS_IN_ORDER = [
    "fhir-tax",
    "slm-on-device",
    "nl-data-pipes",
    "deploy-data-pipes",
    "kotlin-fhir-skills",
]


def _write_experiment(directory: pathlib.Path, filename: str, content: str) -> pathlib.Path:
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


class BuildSiteTests(unittest.TestCase):
    """Happy-path build and validation checks against the repository content."""

    def test_check_real_experiments_succeeds(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = build.main(["--check"])

        self.assertEqual(rc, 0)
        self.assertIn("5 experiments OK", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_full_build_renders_index_assets_and_share_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dist = pathlib.Path(tmpdir) / "dist"
            stdout = io.StringIO()
            with (
                mock.patch.object(build, "DIST", tmp_dist),
                contextlib.redirect_stdout(stdout),
            ):
                rc = build.main([])

            self.assertEqual(rc, 0)
            self.assertIn("5 experiments OK", stdout.getvalue())

            index_path = tmp_dist / "index.html"
            self.assertTrue(index_path.is_file())
            index_html = index_path.read_text(encoding="utf-8")

            # No unreplaced template or body shortcodes should survive.
            self.assertIsNone(re.search(r"\{\{[^}]+\}\}", index_html))

            # Static assets copied cleanly.
            for asset in ("site.css", "site.js", "favicon.svg"):
                self.assertTrue((tmp_dist / "assets" / asset).is_file(), f"missing asset {asset}")

            # Template file excluded and real experiments built in expected sort order.
            self.assertFalse((tmp_dist / "e" / "_template").exists())
            for slug in EXPECTED_SLUGS_IN_ORDER:
                share_page = tmp_dist / "e" / slug / "index.html"
                self.assertTrue(share_page.is_file(), f"missing share page for {slug}")
                self.assertIn(f"../../#/{slug}", share_page.read_text(encoding="utf-8"))

            data_match = re.search(
                r'<script id="labs-data" type="application/json">(.*?)</script>',
                index_html,
                re.S,
            )
            self.assertIsNotNone(data_match)
            payload = json.loads(data_match.group(1))
            self.assertEqual(
                [exp["slug"] for exp in payload["experiments"]],
                EXPECTED_SLUGS_IN_ORDER,
            )


class ValidationAndBoundaryTests(unittest.TestCase):
    """Boundary conditions, malformed inputs, and validation failures."""

    def test_load_raises_without_front_matter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = _write_experiment(
                pathlib.Path(tmpdir),
                "no-front-matter.md",
                "# Missing front matter\n\nJust markdown.\n",
            )
            with self.assertRaises(ValueError):
                build.load(bad_file)

    def test_validate_reports_required_fields_and_invalid_values(self) -> None:
        exp = {
            "slug": "Bad_Slug!",
            "cover": {"pattern": "stripes", "image": "assets/does-not-exist.png"},
            "links": [{"label": "Missing URL"}],
            "charts": [
                {"id": "bad-type", "type": "pie"},
                {"id": "bad-race", "type": "race", "from": "missing-src", "group": "g1"},
            ],
            "body": "Look at {{chart:undefined-chart}}.\n",
        }
        errs = build.validate(exp, pathlib.Path("sample.md"))
        joined = "\n".join(errs)

        for expected in (
            "'title' is required",
            "'stage' is required",
            "'summary' is required",
            "slug (file name) may use only a-z, 0-9 and -",
            "cover.pattern must be one of:",
            "cover.image assets/does-not-exist.png not found",
            "every link needs a label and a url",
            "chart bad-type: type must be one of",
            "chart bad-race: from: must name a grouped-bars chart",
            "body uses {{chart:undefined-chart}} but no chart has id 'undefined-chart'",
        ):
            self.assertIn(expected, joined)

    def test_validate_rejects_unknown_stage_and_race_group(self) -> None:
        exp = {
            "title": "Test",
            "stage": "archived",
            "summary": "Summary",
            "slug": "test-exp",
            "charts": [
                {"id": "main", "type": "grouped-bars", "groups": ["A"]},
                {"id": "replay", "type": "race", "from": "main", "group": "B"},
            ],
            "body": "{{chart:main}}\n{{chart:replay}}\n",
        }
        errs = build.validate(exp, pathlib.Path("test-exp.md"))
        joined = "\n".join(errs)
        self.assertIn("stage 'archived' must be one of:", joined)
        self.assertIn("chart replay: group B is not in main", joined)

    def test_main_fails_on_duplicate_slugs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_dir = pathlib.Path(tmpdir)
            for name in ("first.md", "second.md"):
                _write_experiment(
                    exp_dir,
                    name,
                    (
                        "---\n"
                        "title: Duplicate Test\n"
                        "stage: proposal\n"
                        "slug: shared-slug\n"
                        "summary: Tests duplicate slug detection.\n"
                        "---\n\n"
                        "Body text.\n"
                    ),
                )

            stderr = io.StringIO()
            with (
                mock.patch.object(build, "EXPERIMENTS", exp_dir),
                contextlib.redirect_stderr(stderr),
            ):
                rc = build.main(["--check"])

            self.assertEqual(rc, 1)
            self.assertIn("slug 'shared-slug' is used twice", stderr.getvalue())


class EscapingTests(unittest.TestCase):
    """HTML and embedded JSON escaping invariants."""

    def test_esc_escapes_html_special_characters(self) -> None:
        raw = '<script>"a & b"</script>'
        self.assertEqual(
            build.esc(raw),
            "&lt;script&gt;&quot;a &amp; b&quot;&lt;/script&gt;",
        )

    def test_embedded_json_escapes_closing_script_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            exp_dir = tmp_path / "experiments"
            dist_dir = tmp_path / "dist"
            exp_dir.mkdir()

            payload_text = "Breaks if raw </script><script>alert(1)</script> appears."
            _write_experiment(
                exp_dir,
                "escape-check.md",
                (
                    "---\n"
                    "title: Escape Check\n"
                    "stage: published\n"
                    f'summary: "{payload_text}"\n'
                    "---\n\n"
                    "## Check | Verifies escaping\n\n"
                    "Plain paragraph.\n"
                ),
            )

            stdout = io.StringIO()
            with (
                mock.patch.object(build, "EXPERIMENTS", exp_dir),
                mock.patch.object(build, "DIST", dist_dir),
                contextlib.redirect_stdout(stdout),
            ):
                rc = build.main([])

            self.assertEqual(rc, 0)
            index_html = (dist_dir / "index.html").read_text(encoding="utf-8")
            data_match = re.search(
                r'<script id="labs-data" type="application/json">(.*?)</script>',
                index_html,
                re.S,
            )
            self.assertIsNotNone(data_match)
            raw_json = data_match.group(1)
            self.assertNotIn("</script>", raw_json)
            self.assertIn("<\\/script>", raw_json)
            parsed = json.loads(raw_json)
            self.assertEqual(parsed["experiments"][0]["summary"], payload_text)


if __name__ == "__main__":
    unittest.main()
