import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def front_matter(path):
    content = read(path)
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise AssertionError(f"{path} has no YAML front matter")
    return parts[1]


def metadata(path, key):
    match = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)", front_matter(path), re.MULTILINE)
    return match.group(1).strip() if match else None


def structural_classes(path):
    return re.findall(r"<(?:div|section|article|aside|figure|details)\b[^>]*class=\"([^\"]+)\"", read(path))


class BilingualPagesTests(unittest.TestCase):
    def test_english_and_chinese_pages_keep_matching_routes(self):
        pairs = [
            ("_pages/about.md", "_pages/zh-about.md", "/", "/zh/"),
            ("_pages/bio.md", "_pages/zh-bio.md", "/bio/", "/zh/bio/"),
            ("_pages/research.md", "_pages/zh-research.md", "/research/", "/zh/research/"),
        ]
        for english, chinese, english_url, chinese_url in pairs:
            with self.subTest(english=english):
                self.assertEqual(metadata(english, "permalink"), english_url)
                self.assertEqual(metadata(english, "lang"), "en")
                self.assertEqual(metadata(english, "translation_url"), chinese_url)
                self.assertEqual(metadata(chinese, "permalink"), chinese_url)
                self.assertEqual(metadata(chinese, "lang"), "zh-CN")
                self.assertEqual(metadata(chinese, "translation_url"), english_url)

    def test_chinese_pages_reuse_the_english_page_structure(self):
        for english, chinese in [
            ("_pages/about.md", "_pages/zh-about.md"),
            ("_pages/bio.md", "_pages/zh-bio.md"),
            ("_pages/research.md", "_pages/zh-research.md"),
        ]:
            with self.subTest(english=english):
                self.assertEqual(structural_classes(english), structural_classes(chinese))

    def test_navigation_exposes_both_languages_and_uses_page_translation(self):
        navigation = read("_data/navigation.yml")
        masthead = read("_includes/masthead.html")
        self.assertIn("title_zh:", navigation)
        self.assertIn("url_zh:", navigation)
        self.assertIn("page.translation_url", masthead)
        self.assertIn("link.url_zh", masthead)
        self.assertIn("site_home_url", masthead)
        self.assertIn("English", masthead)
        self.assertIn("中文", masthead)

    def test_document_language_comes_from_the_page(self):
        layout = read("_layouts/default.html")
        self.assertRegex(layout, r'<html lang="\{\{\s*page\.lang')

    def test_open_graph_locale_keeps_the_english_region(self):
        seo = read("_includes/seo.html")
        self.assertIn("assign og_locale = page.lang", seo)
        self.assertIn("if page.lang == 'en'", seo)
        self.assertIn("assign og_locale = site.locale", seo)
        self.assertIn("replace: \"-\", \"_\"", seo)

    def test_narrow_mobile_brand_does_not_overlap_the_menu(self):
        masthead_styles = read("_sass/_masthead.scss")
        self.assertIn("text-overflow: ellipsis", masthead_styles)
        self.assertIn("overflow: hidden", masthead_styles)


if __name__ == "__main__":
    unittest.main()
