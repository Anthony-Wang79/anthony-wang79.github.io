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

    def test_simplified_chinese_feed_label_means_subscription(self):
        ui_text = read("_data/ui-text.yml")
        self.assertNotIn('feed_label                 : "打赏"', ui_text)
        self.assertEqual(len(re.findall(r"^zh-CN:", ui_text, re.MULTILINE)), 1)

    def test_stylesheet_url_is_cache_busted_on_site_build(self):
        head = read("_includes/head.html")
        self.assertIn("main.css?v={{ site.time | date: '%s' }}", head)

    def test_chinese_pages_use_requested_names_copy_and_publication_titles(self):
        masthead = read("_includes/masthead.html")
        config = read("_config.yml")
        home = read("_pages/zh-about.md")
        bio = read("_pages/zh-bio.md")
        research = read("_pages/zh-research.md")
        main_styles = read("assets/css/main.scss")

        self.assertIn("{% assign masthead_title = site.title %}", masthead)
        self.assertIn("{% assign masthead_title = site.author.name_zh | default: site.title %}", masthead)
        self.assertIn("{{ masthead_title }}", masthead)
        self.assertIn('bio_zh           : "复旦大学经济学院博士研究生"', config)

        self.assertIn("保险、健康与福祉", home)
        self.assertIn("王昕彤，复旦大学经济学院博士研究生（卓博计划）", home)
        self.assertIn("我的研究关注保险如何影响家庭应对健康与长寿风险的行为选择以及相应的福利水平，同时考察信息与激励在此过程中的作用。", home)
        self.assertRegex(main_styles, r"\.home-page \.research-hero \.research-lede \+ \.research-lede\s*\{\s*margin-top:\s*1\.25rem;")
        self.assertIn("The Impact of Public-Private Partnership Health Plans on Private Insurance", home)
        self.assertIn("本文以中国城市定制型医疗保险计划（惠民保）为研究背景，发现社商合作型保险保障的扩展可能挤出商业保险购买，并降低平均保障额度。", home)
        self.assertIn(">阅读论文 <span", home)
        self.assertNotIn("查看已发表论文", home)

        self.assertIn("复旦大学经济学院博士研究生", bio)
        self.assertIn("我的研究围绕保险经济学、健康经济学与家庭金融展开。研究发表于<em>Journal of Development Economics</em>、《保险研究》等中英文权威学术期刊。", bio)
        self.assertIn("复旦大学 · 卓博计划", bio)
        self.assertNotIn("以最高荣誉毕业", bio)
        awards = re.search(r'<ul class="bio-awards-grid">(.*?)</ul>', bio, re.DOTALL).group(1)
        self.assertEqual(len(re.findall(r"<li>", awards)), 3)
        self.assertIn("蒋学模经济学讲座", bio)
        self.assertEqual(bio.count("复旦大学AI大课，许闲教授"), 2)
        self.assertIn("复旦大学优秀学生培养计划（思源计划）辅导员", bio)

        for original_title in [
            "The Impact of Public-Private Partnership Health Plans on Private Insurance",
            "Exploring Health Improvement Incentives through Wellness-Linked Insurance Products",
            "Public Disclosure of Health Information and Insurance Demand",
        ]:
            with self.subTest(title=original_title):
                self.assertIn(original_title, research)
        self.assertIn("商业健康保险的赔付率悖论与获得感悖论：兼论多层次医疗保障体系的制度衔接路径", research)
        self.assertIn("本文以中国城市定制型医疗保险计划（惠民保）为研究背景，发现社商合作型保险保障的扩展可能挤出商业保险购买，并降低平均保障额度。", research)
        self.assertEqual(research.count(">阅读论文 <span"), 2)
        self.assertNotIn("查看已发表论文", research)


if __name__ == "__main__":
    unittest.main()
