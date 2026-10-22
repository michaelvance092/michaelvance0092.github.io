#!/usr/bin/env python3
"""Fail the build if the static site has broken local links, missing alt text,
missing titles, or the banned em dash. Standard library only."""
import pathlib
import re
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".github", "scripts", "_site", ".remember", "node_modules"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.errors = [], set(), []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "title":
            self._in_title = True
        if tag == "img" and "alt" not in a:
            self.errors.append(f"<img src={a.get('src')}> has no alt attribute")
        for key in ("href", "src"):
            if key in a:
                self.refs.append(a[key])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def pages():
    for p in sorted(ROOT.rglob("*.html")):
        if not SKIP_DIRS & set(p.relative_to(ROOT).parts):
            yield p


def resolve(page, ref):
    target = (page.parent / ref.split("#")[0].split("?")[0]).resolve()
    if target.is_dir():
        target = target / "index.html"
    return target


def main():
    parsed, problems = {}, []
    for p in pages():
        text = p.read_text(encoding="utf-8")
        parser = Page()
        parser.feed(text)
        parsed[p.resolve()] = parser
        rel = p.relative_to(ROOT)
        if "—" in text:
            problems.append(f"{rel}: contains an em dash")
        if not parser.title.strip():
            problems.append(f"{rel}: missing <title>")
        problems += [f"{rel}: {e}" for e in parser.errors]

    for page, parser in parsed.items():
        rel = page.relative_to(ROOT)
        for ref in parser.refs:
            if re.match(r"^(https?:|mailto:|tel:|data:|//)", ref) or ref.startswith("/"):
                continue
            if ref.startswith("#"):
                if ref[1:] and ref[1:] not in parser.ids:
                    problems.append(f"{rel}: anchor {ref} not found")
                continue
            target = resolve(page, ref)
            if not target.exists():
                problems.append(f"{rel}: broken link {ref}")
            elif "#" in ref and target in parsed and ref.split("#")[1] not in parsed[target].ids:
                problems.append(f"{rel}: anchor in {ref} not found")

    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print(f"OK: {len(parsed)} pages checked")


main()
