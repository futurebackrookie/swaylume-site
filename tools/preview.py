#!/usr/bin/env python3
"""Generate an isolated local preview, leaving the publishable site/ files intact.
Serve the repository root: python3 -m http.server 8765 --bind 127.0.0.1
"""
import argparse
import importlib.util
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--port', type=int, default=8765)
    options = args.parse_args()
    output = ROOT.parent / 'build' / 'site-preview'
    spec = importlib.util.spec_from_file_location('site_build', ROOT / 'build.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    build.PREVIEW = True
    build.SITE_URL = f'http://localhost:{options.port}/build/site-preview'
    locales = build.load_locales()
    template = (ROOT / 'template.html').read_text()
    errors = build.check_keys(locales, template)
    if errors:
        raise SystemExit('\n'.join(errors))
    build.LANG_HINTS.update(build.lang_hints(locales))
    output.mkdir(parents=True, exist_ok=True)
    for name in ('assets', 'posters'):
        shutil.copytree(ROOT / name, output / name, dirs_exist_ok=True)
    for name in ('icon.png', 'og-cover.png', 'screenshot-library.png', 'pet-idle.png', 'pet-walk.png', 'pet-petted.png'):
        shutil.copy2(ROOT / name, output / name)
    build.copy_wallpapers(output / 'wallpapers')
    for code, (langdir, _, _, _) in build.LOCALES.items():
        for page, (pagedir, _, _) in build.PAGES.items():
            target = output / langdir / pagedir / 'index.html'
            target.parent.mkdir(parents=True, exist_ok=True)
            body = build.render(template, locales[code], code, page)
            target.write_text(build.head(code, locales[code], page) + '\n' + body + '\n</body>\n</html>\n')
    print(f'Preview: {build.SITE_URL}/')
    print('5 languages, 15 pages. Production output was not changed.')

if __name__ == '__main__':
    main()
