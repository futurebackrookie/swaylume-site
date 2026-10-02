"""build.py 的构建链路。python3 site/tools/test_build.py"""
import importlib.util, pathlib, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class CopyWallpapersTests(unittest.TestCase):
    def test_copies_every_wallpaper_the_page_uses(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = build.copy_wallpapers(pathlib.Path(tmp))
            expected = {build.HERO, build.WEB_TILE, *build.FEATURED}
            self.assertEqual(set(copied), expected)
            for slug in expected:
                self.assertTrue((pathlib.Path(tmp) / slug / "index.html").is_file(), slug)

    def test_unknown_slug_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                build.copy_wallpapers(pathlib.Path(tmp), slugs=["no-such-wallpaper"])


class AssetUrlTests(unittest.TestCase):
    def test_url_carries_content_hash(self):
        url = build.asset_url("site.css")
        self.assertTrue(url.startswith(build.SITE_URL + "/assets/site.css?v="))
        self.assertEqual(len(url.split("?v=")[1]), 8)

    def test_hash_changes_with_content(self):
        a = build.content_hash(b"one")
        self.assertNotEqual(a, build.content_hash(b"two"))
        self.assertEqual(a, build.content_hash(b"one"))


class OnlyFlagTests(unittest.TestCase):
    def test_only_limits_locales(self):
        self.assertEqual(build.selected_locales(["--only", "zh-Hans"]), ["zh-Hans"])
        self.assertEqual(build.selected_locales([]), list(build.LOCALES))

    def test_only_rejects_unknown_locale(self):
        with self.assertRaises(SystemExit):
            build.selected_locales(["--only", "xx"])


if __name__ == "__main__":
    unittest.main()
