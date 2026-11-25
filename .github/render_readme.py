#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Write the readme of this repository from the About page of the blog.

GitHub shows this readme on the profile page of the account. The About page of the blog
is the one place where the bio is written, so the readme is a copy of it, and never a
second text to maintain. Change the bio in `content/pages/about.md` of `kdeldycke/blog`:
the `sync-readme` job overwrites this readme.

Each deploy of the blog publishes the Markdown of each page next to the page. In that
copy, the blog has replaced each Pelican marker by an address on the live site, and has
written each image with layout classes as an `<img>` tag, the one form that GitHub can
float. So this script needs no checkout of the blog. It changes the copy in three ways:

- The front matter goes: GitHub would draw it as a table.
- The section about the site stays out: it speaks of the blog, not of its author.
- A comment at the top says where the text comes from.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

SITE = "https://kevin.deldycke.com"
"""Address of the live site of the blog."""

SOURCE = f"{SITE}/about.md"
"""Markdown copy of the About page, which each deploy of the blog publishes."""

USER_AGENT = "sync-readme"
"""User agent of the download: the site answers 403, with error code 1010, to the one
that urllib sends by default."""

SKIPPED_SECTIONS = frozenset({"About this site"})
"""Titles of the sections that the readme leaves out."""

NOTICE = (
    f"<!-- Copy of {SITE}/about, written by .github/render_readme.py. Edit"
    " content/pages/about.md of kdeldycke/blog: a job of this repository overwrites"
    " this file. -->"
)

FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
HEADING = re.compile(r"(#+) +(.+?) *$")
MARKER = re.compile(r"[{|](?:attach|author|category|filename|index|static|tag)[}|]")
"""A Pelican marker, in either delimiter style, that the blog left in the copy."""


def _without_skipped_sections(text: str) -> str:
    """Drop each skipped section, from its heading to the next one of its level.

    :raises ValueError: When a skipped section is missing: a section that the page
        renamed would come back into the readme without a word.
    """
    kept = []
    found = set()
    skipped_level = 0
    for line in text.split("\n"):
        heading = HEADING.fullmatch(line)
        if heading:
            level = len(heading.group(1))
            if heading.group(2) in SKIPPED_SECTIONS:
                found.add(heading.group(2))
                skipped_level = level
            elif skipped_level and level <= skipped_level:
                skipped_level = 0
        if not skipped_level:
            kept.append(line)
    missing = sorted(SKIPPED_SECTIONS - found)
    if missing:
        raise ValueError(f"The page has no section named {', '.join(missing)}.")
    return "\n".join(kept)


def render(page: str) -> str:
    """Turn the Markdown copy of the About page into the text of the readme.

    :param page: Content of the copy that the blog publishes.
    :return: Markdown that GitHub renders.
    :raises ValueError: When a skipped section is missing, or when the copy keeps a
        Pelican marker: a readme with a dead link is worse than a job that fails.
    """
    text = FRONT_MATTER.sub("", page, count=1)
    text = _without_skipped_sections(text)
    if MARKER.search(text):
        raise ValueError("The copy keeps a Pelican marker.")
    # The formatter of this repository keeps one blank line between two blocks: writing
    # the same here leaves it nothing to change in the copy.
    text = re.sub(r"\n{3,}", "\n\n", text).strip("\n")
    return f"{NOTICE}\n\n{text}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source",
        default=SOURCE,
        help="Address or path of the copy to read. Defaults to the copy on the site.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="File to write. Defaults to the standard output.",
    )
    arguments = parser.parse_args()
    if arguments.source.startswith("https://"):
        request = urllib.request.Request(
            arguments.source, headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            page = response.read().decode("UTF-8")
    else:
        page = Path(arguments.source).read_text(encoding="UTF-8")
    readme = render(page)
    if arguments.output:
        arguments.output.write_text(readme, encoding="UTF-8")
    else:
        sys.stdout.write(readme)
    return 0


if __name__ == "__main__":
    sys.exit(main())
