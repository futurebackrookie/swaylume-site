#!/usr/bin/env python3
"""从 template.html + locales/*.json 生成各语言的站点。

输出：
    content.html        中文片段（不带 <!doctype>，供预览页使用）
    index.html          中文完整文档
    en/index.html       英文
    fr/ ja/ de/         法语 / 日语 / 德语

为什么是编译期生成而不是 JS 运行时切换：做多语言的目的是让非中文用户
**搜得到**。JS 切换的话每种语言没有自己的网址，搜索引擎只会收录默认那一版，
等于白做。编译期出静态页，每种语言都是真实 URL，配 hreflang 互相声明。

用法：./build.py [--check]
      --check  只校验词条完整性，不写文件
"""
import json, re, os, sys, pathlib

SITE_URL = os.environ.get("SWAYLUME_SITE_URL",
                          "https://futurebackrookie.github.io/swaylume-site").rstrip("/")

# 语言代码 -> (输出子目录, <html lang>, og:locale, 语言切换器上的名字)
LOCALES = {
    "zh-Hans": ("",   "zh-Hans", "zh_CN", "简体中文"),
    "en":      ("en", "en",      "en_US", "English"),
    "ja":      ("ja", "ja",      "ja_JP", "日本語"),
    "de":      ("de", "de",      "de_DE", "Deutsch"),
    "fr":      ("fr", "fr",      "fr_FR", "Français"),
}
DEFAULT = "zh-Hans"

# 站点现在有两页。首页只留六幕主线，密集的参考材料（音频、素材来源与授权、
# 隐私兼容、常见问题、三条上手路径）挪到 /details ——
# 一条都没删：它们是可信度的证据，只是不该跟首屏抢注意力。
#
# 页面 id -> (子路径, 标题词条, 描述词条)
PAGES = {
    "home":    ("",         "x.title1",      "meta.description"),
    "details":  ("details", "details.title", "details.description"),
}


def page_href(base, subdir, page):
    """某语言某页面的绝对路径。语言子目录在前，页面子目录在后。"""
    parts = [base.rstrip("/")]
    if subdir:
        parts.append(subdir)
    if PAGES[page][0]:
        parts.append(PAGES[page][0])
    return "/".join(parts) + "/"


# 只出现在某一页的区块。没标记的（head、导航、页脚）两页都有。
PAGE_BLOCK = re.compile(r"[ \t]*<!--ONLY:(\w+)-->\n?(.*?)[ \t]*<!--/ONLY-->\n?", re.S)


def select_page(html, page):
    return PAGE_BLOCK.sub(lambda m: m.group(2) if m.group(1) == page else "", html)

# Google Search Console 的所有权验证串。
#
# 这是第二种验证方式 —— 第一种是根目录那个 google*.html 文件。
# 多留一种是因为文件万一被误删就会掉验证状态，而掉了之后 sitemap 的
# 提交记录和「效果」报告都会一并失效。
# 这个串是公开信息，本来就写在页面 <head> 里给 Google 读。
GOOGLE_SITE_VERIFICATION = "93BTzCfdrxJ65LatgdtsEzQOmfIMGR1uFCZ4_jt4318"

# 网页访问统计。留空 = 页面上一个追踪脚本都没有。
#
# 只支持无 cookie 的方案。页面自己有一整节在讲隐私，挂 Google Analytics
# 那种广告产品是自相矛盾 —— 而且欧盟访客还得弹 Cookie 同意条。
#
#   ANALYTICS = ("cloudflare", "你的 token")   # dash.cloudflare.com → Web Analytics
#   ANALYTICS = ("goatcounter", "你的子域名")   # 形如 swaylume（不含 .goatcounter.com）
#
# 这个 token 不是密钥：它会原样出现在每个访客的页面源码里，Cloudflare 就是这么
# 设计的（它标识「统计哪个站点」，不能用来读数据，读数据要登录后台）。
# 所以进版本库没有问题，不用当敏感信息处理。
# 主机名注册的是 futurebackrookie.github.io —— 账号级域名，名下其它
# GitHub Pages 项目的流量会一起算进来，后台按 /swaylume-site/* 路径筛才是本站数字。
ANALYTICS = ("cloudflare", "aca979be3ab8462e811dcefcae9aa19b")

ROOT = pathlib.Path(__file__).parent
PLACEHOLDER = re.compile(r"\{\{([\w.\-]+)\}\}")


def load_locales():
    out = {}
    for code in LOCALES:
        path = ROOT / "locales" / f"{code}.json"
        if not path.exists():
            print(f"❌ 缺少 locales/{code}.json")
            sys.exit(1)
        out[code] = json.loads(path.read_text())
    return out


def check_keys(locales, template):
    """每种语言的词条集合必须完全一致，且覆盖模板里的每个占位符。

    漏一条的后果不是报错而是页面上突兀地冒出一句中文，肉眼很难在
    五个语言 × 十个分节里发现 —— 所以必须机器查。
    """
    used = set(PLACEHOLDER.findall(template))
    base = set(locales[DEFAULT])
    errors = []

    # js.* 不以 {{}} 形式出现在模板里 —— 它们注入到 window.__I18N 供页面脚本读取，
    # 所以「模板里没用到」对它们不是错误。
    # 这几条由 build.py 自己消费，模板里不会出现对应的 {{}}：
    # 前两条进 <head>，trust.analytics 只在开了统计时才输出。
    # 页面标题/描述由 head() 经 PAGES 消费，从那里派生而不是再抄一遍 ——
    # 抄一遍的话，加一个页面就多一处会忘记同步的地方。
    PAGE_KEYS = {k for _, t, d in PAGES.values() for k in (t, d)}
    CODE_KEYS = PAGE_KEYS | {"trust.analytics"}
    # 豁免名单最容易变成孤儿词条的藏身处 —— 写进来却没人用，检查照样放行。
    # 所以反过来验一遍：豁免的 key 必须真的被本文件用到。
    #
    # 注意这里必须数**出现次数**，不能只判断「在不在源码里」：
    # CODE_KEYS 这行本身就写着这些 key，源码里永远找得到，那样写出来的
    # 检查永远不会失败。第一版就是这么写的，拿一个纯属虚构的 key 去测才发现。
    # 声明处贡献 1 次，所以真正被用到的至少出现 2 次。
    _self = pathlib.Path(__file__).read_text()
    # 只对**手写**进名单的 key 做这个计数。PAGE_KEYS 是从 PAGES 结构里推出来的，
    # 「确实被用到」由结构本身保证；而它们的字面量在 PAGES 里只出现一次，
    # 套用「至少两次」的规则会把它们误判成孤儿词条。
    _dead = {k for k in CODE_KEYS - PAGE_KEYS if _self.count(f'"{k}"') < 2}
    if _dead:
        errors.append(f"豁免名单里有 build.py 根本没用到的 key：{sorted(_dead)}")
    missing_in_template = {k for k in base - used
                           if not k.startswith("js.") and k not in CODE_KEYS}
    if missing_in_template:
        errors.append(f"{DEFAULT} 有 {len(missing_in_template)} 条词条模板里用不到："
                      f"{sorted(missing_in_template)[:5]}")

    # 但 js.* 必须真的被脚本用到，否则就是改代码时留下的孤儿词条
    import re as _re
    referenced = set(_re.findall(r'T\("([\w.]+)"\)', template))
    referenced |= {f"js.preview{n}.{f}" for n in "1234" for f in ("kind", "title", "meta")}
    referenced |= {f"js.gov{n}.{f}" for n in "1234567" for f in ("p", "m")}
    orphan = {k for k in base if k.startswith("js.")} - referenced
    if orphan:
        errors.append(f"js.* 有 {len(orphan)} 条没有任何脚本引用：{sorted(orphan)}")
    unknown = used - base
    if unknown:
        errors.append(f"模板里有 {len(unknown)} 个占位符没有对应词条："
                      f"{sorted(unknown)[:5]}")

    for code, entries in locales.items():
        if code == DEFAULT:
            continue
        miss = base - set(entries)
        extra = set(entries) - base
        if miss:
            errors.append(f"{code} 缺 {len(miss)} 条：{sorted(miss)[:6]}")
        if extra:
            errors.append(f"{code} 多出 {len(extra)} 条：{sorted(extra)[:6]}")
        empty = [k for k, v in entries.items() if not str(v).strip()]
        if empty:
            errors.append(f"{code} 有 {len(empty)} 条是空的：{empty[:6]}")

    return errors


def analytics_tag():
    """无 cookie 的访问统计。没配置就什么都不输出。

    defer 是必须的：统计脚本绝不该挡住首屏那个着色器的渲染。
    """
    if not ANALYTICS:
        return []
    kind, key = ANALYTICS
    if kind == "cloudflare":
        return ['<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
                f"""data-cf-beacon='{{"token": "{key}"}}'></script>"""]
    if kind == "goatcounter":
        return [f'<script defer data-goatcounter="https://{key}.goatcounter.com/count" '
                'src="//gc.zgo.at/count.js"></script>']
    raise ValueError(f"不认识的统计方案：{kind}")


def analytics_note(entries):
    """开了统计才输出这句话。"""
    if not ANALYTICS:
        return ""
    return f'<p class="trust-note rise">{entries["trust.analytics"]}</p>'


def head(code, entries, page="home"):
    subdir, lang, og_locale, _ = LOCALES[code]
    title_key, desc_key = PAGES[page][1], PAGES[page][2]
    canonical = page_href(SITE_URL, subdir, page)
    lines = [
        "<!doctype html>",
        f'<html lang="{lang}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f'<title>{entries[title_key]}</title>',
        f'<meta name="description" content="{entries[desc_key]}">',
        f'<meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">',
        f'<link rel="canonical" href="{canonical}">',
    ]
    # hreflang：告诉搜索引擎这几个页面是同一内容的不同语言版本。
    # 少了它，各语言版本会被当成互相抄袭的重复内容。
    # hreflang 必须指向**同一页**的其它语言版本。指回首页的话，
    # 各语言的 /details 会被判成没有对应译文。
    for other, (osub, olang, _, _) in LOCALES.items():
        lines.append(f'<link rel="alternate" hreflang="{olang}" '
                     f'href="{page_href(SITE_URL, osub, page)}">')
    lines.append(f'<link rel="alternate" hreflang="x-default" '
                 f'href="{page_href(SITE_URL, "", page)}">')
    lines += [
        '<meta name="theme-color" content="#0A0A0B" media="(prefers-color-scheme: dark)">',
        '<meta name="theme-color" content="#EBE4D3" media="(prefers-color-scheme: light)">',
        f'<meta property="og:title" content="{entries[title_key]}">',
        f'<meta property="og:description" content="{entries[desc_key]}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:locale" content="{og_locale}">',
        f'<meta property="og:url" content="{canonical}">',
        f'<meta property="og:image" content="{SITE_URL}/og-cover.png">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">',
        # downloadUrl 必须指向公开仓库；源码仓库是私有的，写进去等于喂死链
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"SoftwareApplication","name":"Swaylume",'
        '"applicationCategory":"UtilitiesApplication","operatingSystem":"macOS 14 or later",'
        '"softwareVersion":"Beta",'
        '"downloadUrl":"https://github.com/futurebackrookie/swaylume-site/releases",'
        '"offers":{"@type":"Offer","price":"0","priceCurrency":"USD"}}</script>',
        f'<link rel="icon" type="image/png" href="{SITE_URL}/icon.png">',
        f'<link rel="apple-touch-icon" href="{SITE_URL}/icon.png">',
    ]
    lines += analytics_tag()
    lines += [
        "</head>",
        # 页面 id 挂在 body 上：首页每一幕是满屏画面，二级页退回安静的纸面。
        # 两页共用一份样式，靠这个属性分流，不再各写一套。
        f'<body data-page="{page}">',
    ]
    return "\n".join(lines)


def lang_switcher(code, page="home"):
    """语言切换器：收起成一个按钮，点开才列出语言。

    **链接依然是构建时写死的真实 `<a hreflang>`，只是默认不可见。**
    爬虫读的是 DOM 不是可见状态，所以头部那些 hreflang 照样有依据 ——
    以前这里写着「不用 JS 下拉」，防的是**用 JS 现生成链接**那种做法，
    不是这种。

    用 `<details>` 而不是按钮加脚本：没有 JS 也能展开，键盘和读屏天然可用。
    脚本只负责「点外面关掉」和 Esc，坏了也只是关不掉，不会打不开。

    顺带解决一个旧问题：五种语言并排在窄屏放不下，原来靠横向滚动加
    `order: -1` 把当前语言顶到最前。收起来之后这个补丁整个不需要了。
    """
    base = "/" + SITE_URL.rstrip("/").split("/")[-1] if "github.io" in SITE_URL else ""
    items = []
    for other, (subdir, lang, _, name) in LOCALES.items():
        # 切语言要停在**同一页**：在 /details 上切成英文该去 /en/details/，
        # 不是把人踢回首页。
        href = page_href(base, subdir, page)
        current = ' aria-current="true"' if other == code else ""
        tick = '<span class="lang-tick" aria-hidden="true">✓</span>' if other == code else '<span class="lang-tick"></span>'
        items.append(
            f'<li><a href="{href}" hreflang="{lang}" lang="{lang}"{current}>'
            f'{tick}<span class="lang-name">{name}</span>'
            f'<span class="lang-code">{lang}</span></a></li>')
    here = LOCALES[code][3]
    return (
        '<details class="langs" data-langs>'
        f'<summary aria-label="Language"><svg class="lang-globe" viewBox="0 0 14 14" aria-hidden="true">'
        '<circle cx="7" cy="7" r="5.4" fill="none" stroke="currentColor" stroke-width="1.2"/>'
        '<path d="M1.6 7h10.8M7 1.6c1.5 1.6 2.2 3.4 2.2 5.4S8.5 10.8 7 12.4c-1.5-1.6-2.2-3.4-2.2-5.4S5.5 3.2 7 1.6Z"'
        ' fill="none" stroke="currentColor" stroke-width="1.2"/></svg>'
        f'<span class="lang-here">{here}</span>'
        '<svg class="lang-caret" viewBox="0 0 10 10" aria-hidden="true">'
        '<path d="M2.5 4l2.5 2.5L7.5 4" fill="none" stroke="currentColor" stroke-width="1.4"'
        ' stroke-linecap="round" stroke-linejoin="round"/></svg></summary>'
        '<ul class="lang-menu">' + "".join(items) + '</ul>'
        '</details>')


def render(template, entries, code, page="home"):
    template = select_page(template, page)

    def rep(m):
        key = m.group(1)
        if key not in entries:
            raise KeyError(f"{code}: 缺词条 {key}")
        return str(entries[key])
    out = PLACEHOLDER.sub(rep, template)
    # 正文里的资源引用必须换成绝对地址。语言页在 /en/ /ja/ 等子目录下，
    # 相对路径会解析到子目录里去 —— 根页面正常、四个语言页全裂图，
    # 只测根页面永远发现不了。
    out = out.replace("%%SITE%%", SITE_URL)
    out = out.replace("<!--LANG-SWITCHER-->", lang_switcher(code, page))
    # 跨页链接。导航里指向已经挪到 /details 的小节，必须写成完整路径 ——
    # 写 "#faq" 的话在首页上点了毫无反应（那个锚点已经不在这一页了）。
    base = "/" + SITE_URL.rstrip("/").split("/")[-1] if "github.io" in SITE_URL else ""
    subdir = LOCALES[code][0]
    out = out.replace("%%HOME%%", page_href(base, subdir, "home"))
    out = out.replace("%%DETAILS%%", page_href(base, subdir, "details"))
    # 站点自己的访问统计声明。关掉统计时输出空串 —— 页面上有一整节在讲隐私，
    # 挂了计数器却只字不提，被人打开开发者工具看见就是自打嘴巴；
    # 反过来，没挂统计还写着「本站使用统计」同样是假话。所以跟着开关走。
    out = out.replace("<!--SITE-ANALYTICS-NOTE-->", analytics_note(entries))
    # 页面脚本要用的文案单独注入。JS 里写死中文的话，切到别的语言后
    # 交互部分（层级读数、调速器日志、精选卡片）会突然变回中文。
    js_strings = {k: v for k, v in entries.items() if k.startswith("js.")}
    blob = json.dumps(js_strings, ensure_ascii=False, separators=(",", ":"))
    out = out.replace("<!--I18N-DATA-->",
                      f"<script>window.__I18N={blob};</script>")
    return out


def content_mtime():
    """内容最后改动时间。

    用构建时间当 lastmod 会在每次重新生成时都变一遍，等于反复告诉搜索引擎
    「内容更新了」，久了就不被当真。取模板和词条文件的最新修改时间才是实话。
    """
    import datetime
    files = [ROOT / "template.html"] + sorted((ROOT / "locales").glob("*.json"))
    newest = max(f.stat().st_mtime for f in files if f.exists())
    return datetime.date.fromtimestamp(newest).isoformat()


def write_sitemap():
    """多语言 sitemap：每条 URL 都要列出全部语言版本（含它自己）。

    只列 5 个 <loc> 而不带 xhtml:link 的话，搜索引擎不知道它们是同一内容的
    不同语言，可能当成互相重复的页面。
    """
    lastmod = content_mtime()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
             '        xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    # 两页 × 五语言。每条 URL 的 alternate 只列**同一页**的其它语言 ——
    # 混在一起的话，/details 会声称自己的英文版是英文首页。
    for page in PAGES:
        for code, (subdir, lang, _, _) in LOCALES.items():
            lines.append("  <url>")
            lines.append(f"    <loc>{page_href(SITE_URL, subdir, page)}</loc>")
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
            for other, (osub, olang, _, _) in LOCALES.items():
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{olang}" '
                             f'href="{page_href(SITE_URL, osub, page)}"/>')
            lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" '
                         f'href="{page_href(SITE_URL, "", page)}"/>')
            lines.append("  </url>")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n")
    return lastmod


def write_robots():
    """robots.txt。

    ⚠️ 部署在 github.io 的子路径下时，爬虫**只认域名根部**的 robots.txt，
    /swaylume-site/robots.txt 会被忽略。生成它是为了将来绑自定义域名时
    自动生效；在那之前，让 sitemap 被发现的办法是去 Search Console 提交。
    """
    (ROOT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n")


def main():
    template = (ROOT / "template.html").read_text()
    locales = load_locales()

    errors = check_keys(locales, template)
    if errors:
        print("❌ 词条校验不通过：")
        for e in errors:
            print("  " + e)
        return 1

    if "--check" in sys.argv:
        print(f"✅ 词条校验通过（{len(LOCALES)} 种语言 × {len(locales[DEFAULT])} 条）")
        return 0

    for code, (subdir, _, _, _) in LOCALES.items():
        for page, (pagedir, _, _) in PAGES.items():
            body = render(template, locales[code], code, page)
            doc = head(code, locales[code], page) + "\n" + body + "\n</body>\n</html>\n"
            parts = [pp for pp in (subdir, pagedir) if pp]
            target = ROOT.joinpath(*parts, "index.html") if parts else ROOT / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(doc)
            rel = "/".join(parts + ["index.html"]) if parts else "index.html"
            print(f"  {rel:24} {len(doc):>7,} 字节  {code}")
        body = render(template, locales[code], code, "home")
        if code == DEFAULT:
            # 预览片段自带 title/description；完整文档里这两项由 head() 负责，
            # 两边都放会产生两个 <title>。
            e = locales[code]
            (ROOT / "content.html").write_text(
                f'<title>{e["x.title1"]}</title>\n'
                f'<meta name="description" content="{e["meta.description"]}">\n\n'
                + body)

    lastmod = write_sitemap()
    write_robots()
    print(f"  sitemap.xml         {len(LOCALES) * len(PAGES)} 条 URL  lastmod {lastmod}")
    print(f"  robots.txt          （子路径部署下爬虫不读，绑域名后自动生效）")
    print(f"✅ {len(LOCALES)} 种语言生成完毕")
    return 0


if __name__ == "__main__":
    sys.exit(main())
