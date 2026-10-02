"""build.py 的构建链路。python3 site/tools/test_build.py"""
import importlib.util, pathlib, tempfile, unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit
from collections import Counter

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

    def test_stale_wallpapers_are_removed(self):
        # 换掉的精选留在目录里的话，deploy.sh 整目录同步会把它一起推上线（2026-10-02 真发生过）
        with tempfile.TemporaryDirectory() as tmp:
            stale = pathlib.Path(tmp) / "winter-glass"
            stale.mkdir()
            build.copy_wallpapers(pathlib.Path(tmp))
            self.assertFalse(stale.exists())

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


class ParsedPage(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.ids = []
        self.links = []
        self.resources = []
        self.wallpapers = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag in ("img", "script") and "src" in attrs:
            self.resources.append(attrs["src"])
        if tag == "link" and attrs.get("rel") in ("stylesheet", "icon"):
            self.resources.append(attrs["href"])
        for attr in ("data-live", "data-slug"):
            if attr in attrs:
                self.wallpapers.append(attrs[attr])


class RenderIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        template = (ROOT / "template.html").read_text()
        locales = build.load_locales()
        cls.pages = {}
        cls.base = urlsplit(build.SITE_URL).path.rstrip("/")
        for code, entries in locales.items():
            for page in build.PAGES:
                html = build.head(code, entries, page) + build.render(template, entries, code, page)
                path = urlsplit(build.page_href(cls.base, build.LOCALES[code][0], page)).path
                cls.pages[path] = (html, ParsedPage(html))

    def test_every_language_has_resolved_copy_and_unique_ids(self):
        for path, (html, parsed) in self.pages.items():
            with self.subTest(path=path):
                self.assertNotIn("{{", html)
                self.assertNotIn("%%", html)
                self.assertNotIn("localhost", html)
                duplicates = [k for k, v in Counter(parsed.ids).items() if v > 1]
                self.assertEqual(duplicates, [])

    def test_internal_navigation_targets_exist_across_pages_and_languages(self):
        for path, (_, parsed) in self.pages.items():
            for href in parsed.links:
                url = urlsplit(href)
                if url.netloc or not url.fragment:
                    continue
                target = url.path or path
                with self.subTest(source=path, href=href):
                    self.assertIn(target, self.pages)
                    self.assertIn(url.fragment, self.pages[target][1].ids)

    def test_all_local_media_and_live_wallpapers_exist(self):
        included = {build.HERO, build.WEB_TILE, *build.FEATURED}
        for path, (_, parsed) in self.pages.items():
            for resource in parsed.resources:
                url = urlsplit(resource)
                if not url.path.startswith(self.base + "/"):
                    continue
                relative = url.path[len(self.base) + 1:]
                with self.subTest(page=path, resource=resource):
                    self.assertTrue((ROOT / relative).is_file())
            for slug in parsed.wallpapers:
                with self.subTest(page=path, slug=slug):
                    self.assertIn(slug, included)
                    self.assertTrue((build.BUNDLED / slug / "content" / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
