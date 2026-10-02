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
    # 包格式单独一页。它面向的是想做壁纸的人，跟「想马上用」的人需求完全不同，
    # 挤进首页只会互相稀释；而放在私有仓库的 docs/ 里等于没公开 ——
    # 站点上写着「欢迎投稿、格式清楚」，格式却在外面看不到。
    "format":  ("format",  "fmt.title",     "fmt.description"),
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

# 本地预览：资源地址指向本机的 http.server（.claude/launch.json 里的 design-proto，
# 仓库根目录、8765 端口）。只给 --preview 用 —— 生成结果里出现 localhost 的话
# 线上整页裂图，所以 deploy.sh 永远走不带开关的正式构建。
PREVIEW = "--preview" in sys.argv
if PREVIEW:
    SITE_URL = "http://localhost:8765/site"

# 页面上实时跑的内置壁纸。它们就是产品本身，不是另做的宣传图。
BUNDLED = ROOT.parent / "Sources" / "Resources" / "BundledWallpapers"
# 开场用极光：没有哪张内置壁纸画着山脊，退而求其次取同一套青色，图标溶进去才像同一个镜头。
# 画廊六张按「互相不像」挑：流体、液态金属、霓虹、光斑、玉色流体、等高线。
HERO = "aurora"
FEATURED = ["daybreak", "copper-fold", "neon-rain", "harbor-lamp", "jade-vein", "contour-map"]
WEB_TILE = "silk-current"


def copy_wallpapers(dest, slugs=None):
    """把页面要用的壁纸从 app 的内置包里复制到 dest/<slug>/。

    复制而不是链接：线上仓库只收 site/，引用不到主仓库的 Sources。
    """
    import shutil
    wanted = slugs if slugs is not None else list(dict.fromkeys([HERO, WEB_TILE, *FEATURED]))
    # 换掉的精选不能留在目录里 —— deploy.sh 是整目录同步，留着就会跟着上线
    if dest.exists() and slugs is None:
        for old in dest.iterdir():
            if old.is_dir() and old.name not in wanted:
                shutil.rmtree(old)
    for slug in wanted:
        src = BUNDLED / slug / "content"
        if not (src / "index.html").is_file():
            print(f"❌ 内置壁纸里没有 {slug}（{src}）")
            sys.exit(1)
        target = dest / slug
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target)
    return wanted


def content_hash(data):
    import hashlib
    return hashlib.sha256(data).hexdigest()[:8]


def asset_url(name):
    """带内容哈希的资源地址。改了 css/js 浏览器一定重新取，不改就一直走缓存。"""
    data = (ROOT / "assets" / name).read_bytes()
    return f"{SITE_URL}/assets/{name}?v={content_hash(data)}"


ASSET = re.compile(r"%%ASSET:([\w.\-]+)%%")


def selected_locales(argv):
    """--only <code> 只生成一种语言（第一阶段只有中文有新词条）。"""
    if "--only" not in argv:
        return list(LOCALES)
    i = argv.index("--only") + 1
    code = argv[i] if i < len(argv) else ""
    if code not in LOCALES:
        print(f"❌ --only 后面要跟语言代码，可选：{', '.join(LOCALES)}")
        sys.exit(2)
    return [code]


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
    # langhint.* 由 build.py 收集全部语言后注入 window.__LANGHINT（见 lang_hints）
    CODE_KEYS = PAGE_KEYS | {"trust.analytics", "langhint.text", "langhint.go", "langhint.close"}
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

    # 但 js.* 必须真的被用到，否则就是改代码时留下的孤儿词条。
    # 脚本已经从模板里拆到 assets/*.js，T("…") 要去那里找；技术细节页的调速器日志
    # 是静态表格，直接以 {{js.gov…}} 写在模板里，也算用到。
    import re as _re
    scripts = template + "".join(f.read_text() for f in sorted((ROOT / "assets").glob("*.js")))
    referenced = set(_re.findall(r'T\("([\w.]+)"\)', scripts)) | used
    # 查表再 T(…) 的写法（省电那幕的四个状态）：引号里出现过的 js.* 也算用到
    referenced |= set(_re.findall(r'"(js\.[\w.]+)"', scripts))
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
    # 本机预览不统计：否则自己刷新几十次全算进访问量，控制台还一片 CORS 报错
    if not ANALYTICS or PREVIEW:
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


TAGS = re.compile(r"<[^>]+>")


def faq_schema(entries):
    """常见问题的结构化数据。

    有了它，搜索结果里可以直接把问答展开 —— 对一个主要靠
    「wallpaper engine mac 平替」这类问句式搜索进来的产品，这是白捡的位置。

    答案里带 HTML（<strong>、<a>），schema.org 要的是纯文本，所以标签得剥掉。
    问答条目从词条里现取，不另抄一份 —— 抄一份就多一处会忘记同步的地方。
    """
    items = []
    n = 1
    while f"faq.q{n}" in entries and f"faq.a{n}" in entries:
        q = TAGS.sub("", str(entries[f"faq.q{n}"])).strip()
        a = TAGS.sub("", str(entries[f"faq.a{n}"])).strip()
        items.append({"@type": "Question", "name": q,
                      "acceptedAnswer": {"@type": "Answer", "text": a}})
        n += 1
    if not items:
        return []
    blob = json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                       "mainEntity": items}, ensure_ascii=False, separators=(",", ":"))
    return [f'<script type="application/ld+json">{blob}</script>']


def head(code, entries, page="home"):
    subdir, lang, og_locale, _ = LOCALES[code]
    title_key, desc_key = PAGES[page][1], PAGES[page][2]
    canonical = page_href(SITE_URL, subdir, page)
    lines = [
        "<!doctype html>",
        # data-site：live.js 拼壁纸和海报地址用
        f'<html lang="{lang}" data-site="{SITE_URL}">',
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
        # 首屏是黑底的开场，浏览器顶栏跟着黑
        '<meta name="theme-color" content="#000000">',
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
        f'<link rel="stylesheet" href="{asset_url("site.css")}">',
        *([f'<link rel="stylesheet" href="{asset_url("home.css")}">'] if page == "home" else []),
        f'<link rel="apple-touch-icon" href="{SITE_URL}/icon.png">',
    ]
    # 常见问题只在 /details 上，结构化数据也只该出现在那一页 ——
    # 每页都放一份等于告诉搜索引擎首页也有 FAQ，实际点进去没有。
    if page == "details":
        lines += faq_schema(entries)
    lines += analytics_tag()
    lines += [
        "</head>",
        # 页面 id 挂在 body 上：首页每一幕是满屏画面，二级页退回安静的纸面。
        # 两页共用一份样式，靠这个属性分流，不再各写一套。
        f'<body data-page="{page}">',
    ]
    return "\n".join(lines)


def site_base():
    """站内链接的路径前缀：站点部署在哪个子路径下。

    github.io 项目页是 /swaylume-site，绑了域名就是空串，本机预览是 /site ——
    都从 SITE_URL 的路径部分来，不再只认 github.io（那样预览时导航全指到仓库根目录）。
    """
    from urllib.parse import urlparse
    return urlparse(SITE_URL).path.rstrip("/")


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
    base = site_base()
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


def brand_mark():
    """页头那个标记。缺文件就直接报错 —— 悄悄少一个 logo 比报错难发现得多。"""
    path = ROOT / "brand-mark.svg"
    if not path.exists():
        raise SystemExit("缺 site/brand-mark.svg，先跑一次 swift Tools/make-icon.swift")
    return path.read_text().strip()


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
    out = ASSET.sub(lambda m: asset_url(m.group(1)), out)
    # 代码块是 white-space: pre，词条开头那个换行会变成一行空白。在这里修，不靠脚本
    out = re.sub(r'(<div class="code[^"]*">)(.*?)(</div>)',
                 lambda m: m.group(1) + m.group(2).strip() + m.group(3), out, flags=re.S)
    out = out.replace("<!--LANG-SWITCHER-->", lang_switcher(code, page))
    # 品牌标记内联进来，不走 <img>：它是 30px 的小图，多一次请求不划算，
    # 而且内联之后能被 CSS 直接摸到。
    # **文件由 Tools/make-icon.swift 和应用图标一起生成**，两边共用同一份
    # 几何 —— 手画两份的话迟早会调了一边忘了另一边，而这种不一致没有任何
    # 测试查得出来。
    out = out.replace("<!--BRAND-MARK-->", brand_mark())
    # 跨页链接。导航里指向已经挪到 /details 的小节，必须写成完整路径 ——
    # 写 "#faq" 的话在首页上点了毫无反应（那个锚点已经不在这一页了）。
    base = site_base()
    subdir = LOCALES[code][0]
    out = out.replace("%%HOME%%", page_href(base, subdir, "home"))
    out = out.replace("%%DETAILS%%", page_href(base, subdir, "details"))
    out = out.replace("%%FORMAT%%", page_href(base, subdir, "format"))
    # 站点自己的访问统计声明。关掉统计时输出空串 —— 页面上有一整节在讲隐私，
    # 挂了计数器却只字不提，被人打开开发者工具看见就是自打嘴巴；
    # 反过来，没挂统计还写着「本站使用统计」同样是假话。所以跟着开关走。
    out = out.replace("<!--SITE-ANALYTICS-NOTE-->", analytics_note(entries))
    # 页面脚本要用的文案单独注入。JS 里写死中文的话，切到别的语言后
    # 交互部分（层级读数、调速器日志、精选卡片）会突然变回中文。
    js_strings = {k: v for k, v in entries.items() if k.startswith("js.")}
    blob = json.dumps(js_strings, ensure_ascii=False, separators=(",", ":"))
    hints = json.dumps(LANG_HINTS, ensure_ascii=False, separators=(",", ":"))
    out = out.replace("<!--I18N-DATA-->",
                      f"<script>window.__I18N={blob};window.__LANGHINT={hints};</script>")
    return out


# 访客浏览器语言和当前页面不一样时，site.js 用**访客那种语言**提示「本站也有你的语言」。
# 所以每一页都要带上所有语言的这三句话，不只是当前页的 —— 由 main() 加载完语言文件后填。
# 只提示、不跳转：按浏览器语言强制跳转既伤收录又惹人烦（见 README「多语言是怎么做的」）。
LANG_HINTS = {}


def lang_hints(locales):
    """{<html lang>: {text, go, close}}，键用页面上 hreflang 的写法，脚本拿它去找切换器里的链接。"""
    return {LOCALES[code][1]: {"text": e["langhint.text"], "go": e["langhint.go"], "close": e["langhint.close"]}
            for code, e in locales.items()}


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
    codes = selected_locales(sys.argv)
    locales = load_locales()
    if len(codes) == 1:
        # 只生成一种语言时，跨语言的词条对齐没有意义（其余语言还是旧词条）
        locales = {c: locales[c] for c in dict.fromkeys([DEFAULT, codes[0]])}

    errors = check_keys(locales, template)
    if errors:
        print("❌ 词条校验不通过：")
        for e in errors:
            print("  " + e)
        return 1

    if "--check" in sys.argv:
        print(f"✅ 词条校验通过（{len(LOCALES)} 种语言 × {len(locales[DEFAULT])} 条）")
        return 0

    partial = PREVIEW or len(codes) < len(LOCALES)
    copy_wallpapers(ROOT / "wallpapers")
    LANG_HINTS.update(lang_hints(locales))
    for code in codes:
        subdir = LOCALES[code][0]
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
        if code == DEFAULT and not partial:
            # 预览片段自带 title/description；完整文档里这两项由 head() 负责，
            # 两边都放会产生两个 <title>。
            e = locales[code]
            (ROOT / "content.html").write_text(
                f'<title>{e["x.title1"]}</title>\n'
                f'<meta name="description" content="{e["meta.description"]}">\n\n'
                + body)

    if partial:
        # 预览 / 只生成一种语言：sitemap、robots、content.html 是线上要用的整站产物，
        # 带着 localhost 或缺语言写进去就是一次悄悄的事故，这里一概不碰
        print(f"✅ 只生成了 {', '.join(codes)}{'（本机预览地址）' if PREVIEW else ''}，sitemap / robots 未改")
        return 0
    lastmod = write_sitemap()
    write_robots()
    print(f"  sitemap.xml         {len(LOCALES) * len(PAGES)} 条 URL  lastmod {lastmod}")
    print(f"  robots.txt          （子路径部署下爬虫不读，绑域名后自动生效）")
    print(f"✅ {len(LOCALES)} 种语言生成完毕")
    return 0


if __name__ == "__main__":
    sys.exit(main())
