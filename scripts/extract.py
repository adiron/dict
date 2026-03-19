#!/usr/bin/env python3
"""
Extract a dictionary .mobi file into data/dictionary.sqlite

Schema:
  entries  - one row per <idx:entry> (headword + definition)
  phrases  - one row per ◦ fixed expression, linked to parent entry

Run: python3 scripts/extract.py path/to/dictionary.mobi
"""

import re
import sqlite3
import sys
from pathlib import Path

import mobi
from bs4 import BeautifulSoup, Tag
from loguru import logger

ROOT = Path(__file__).parent.parent
DB_FILE = ROOT / "data" / "dictionary.sqlite"

# The finite set of true part-of-speech values in this dictionary.
# Everything else in that position (domain labels, register labels) is
# captured raw but stored separately so POS stays clean.
TRUE_POS = {
    "zelfst nw",
    "bn",
    "bn, bw",
    "bw",
    "ov ww",
    "onov ww",
    "ov ww, ook abs",
    "onov ww, ook abs",
    "onpers ww",
    "ww, alleen onbep w",
    "wdk ww",
    "ww",
    "hulpww",
    "koppelww",
    "vz",
    "vw",
    "vnw",
    "tw",
    "lidw",
    "hoofdtelw",
    "rangtelw",
    "meervoud",
    "afk",
    "tussenwerpsel",
    "eigenn",
}

DDL = """
CREATE TABLE entries (
    id          INTEGER PRIMARY KEY,
    headword    TEXT    NOT NULL,
    homonym_num INTEGER,
    pos         TEXT,
    article     TEXT,
    gender      TEXT,
    body_html   TEXT    NOT NULL
);

CREATE TABLE inflections (
    id          INTEGER PRIMARY KEY,
    entry_id    INTEGER NOT NULL REFERENCES entries(id),
    value       TEXT    NOT NULL
);

CREATE INDEX idx_inflections_value ON inflections(value);

CREATE TABLE phrases (
    id          INTEGER PRIMARY KEY,
    entry_id    INTEGER NOT NULL REFERENCES entries(id),
    dutch       TEXT    NOT NULL,
    translation TEXT    NOT NULL,
    body_html   TEXT    NOT NULL
);

-- FTS on headword only
CREATE VIRTUAL TABLE entries_fts USING fts5(
    headword,
    content=entries,
    content_rowid=id
);

-- FTS on the Dutch phrase text
CREATE VIRTUAL TABLE phrases_fts USING fts5(
    dutch,
    content=phrases,
    content_rowid=id
);
"""


def extract_book_html(mobi_path: Path) -> Path:
    logger.info("Extracting MOBI...")
    tmpdir, _ = mobi.extract(str(mobi_path))
    book = Path(tmpdir) / "mobi7" / "book.html"
    if not book.exists():
        logger.error("Could not find book.html in extracted MOBI at {}", tmpdir)
        sys.exit(1)
    logger.info("Extracted to {}", book)
    return book


def iter_raw_entries(book_html: Path):
    """Yield raw HTML strings for each <idx:entry> block."""
    pattern = re.compile(r"<idx:entry[^>]*>.*?</idx:entry>", re.DOTALL)
    logger.info("Reading book.html ({:.1f} MB)...", book_html.stat().st_size / 1e6)
    text = book_html.read_text(encoding="utf-8", errors="replace")
    logger.info("Scanning for entries...")
    yield from pattern.finditer(text)


def parse_homonym_num(b_tag: Tag | None) -> int | None:
    """Return the superscript homonym number from <b>word<sup>N</sup></b>, or None."""
    if b_tag is None:
        return None
    sup = b_tag.find("sup")
    if sup:
        txt = sup.get_text(strip=True)
        if txt.isdigit():
            return int(txt)
    return None


def parse_article_gender(raw: str) -> tuple[str | None, str | None]:
    """
    Return (article, gender) from the span pattern:
      <span>de/het<sup><i>m/v</i></sup></span>
    Gender is m, v, or None.
    """
    m = re.search(r"<span>(de|het)(?:<sup><i>([mv])</i></sup>)?</span>", raw)
    if m:
        return m.group(1), m.group(2) or None
    return None, None


def parse_pos(soup: BeautifulSoup) -> str | None:
    """
    Find the first <i> tag whose text is a known POS value.
    The POS appears in the definition section before any sense numbers.
    """
    for i_tag in soup.find_all("i"):
        txt = i_tag.get_text(strip=True)
        if txt in TRUE_POS:
            return txt
    return None


def parse_inflections(soup: BeautifulSoup) -> list[str]:
    return [tag["value"] for tag in soup.find_all("idx:iform") if tag.get("value")]


def parse_body_html(soup: BeautifulSoup) -> str:
    """
    Return the inner HTML of the definition section - the last top-level <div>
    inside <idx:entry>. Strips idx: namespace tags.
    """
    entry = soup.find("idx:entry")
    if not entry:
        return ""
    # Top-level divs inside the entry: [headword div, article div, definition div]
    top_divs = [c for c in entry.children if isinstance(c, Tag) and c.name == "div"]
    if not top_divs:
        return ""
    # The definition is the last top-level div
    return str(top_divs[-1])


def is_leaf_phrase_div(div: Tag) -> bool:
    """
    True if this div directly contains a ◦ phrase (not a container of phrase divs).
    """
    text = div.get_text(strip=True)
    if not text.startswith("◦"):
        return False
    # Must not contain child divs that are themselves phrase divs
    for child in div.children:
        if isinstance(child, Tag) and child.name == "div":
            child_text = child.get_text(strip=True)
            if child_text.startswith("◦"):
                return False
    return True


def parse_phrases(soup: BeautifulSoup) -> list[dict]:
    """
    Return list of {dutch, translation, body_html} for each ◦ fixed expression.
    """
    results = []
    seen = set()

    for div in soup.find_all("div"):
        if not is_leaf_phrase_div(div):
            continue

        raw_html = str(div)
        if raw_html in seen:
            continue
        seen.add(raw_html)

        full_text = div.get_text(" ", strip=True)
        # Strip leading ◦ bullet
        full_text = re.sub(r"^◦\s*", "", full_text)

        # Split on | separator
        if "|" in full_text:
            dutch_part, _, translation_part = full_text.partition("|")
        else:
            dutch_part = full_text
            translation_part = ""

        dutch = dutch_part.strip()
        translation = translation_part.strip()

        if dutch:
            results.append(
                {
                    "dutch": dutch,
                    "translation": translation,
                    "body_html": raw_html,
                }
            )

    return results


def strip_phrases(soup: BeautifulSoup) -> None:
    """
    Remove all phrase divs (and any parent divs that become empty after removal)
    from the soup in-place, so parse_body_html doesn't include them.
    """
    for div in soup.find_all("div"):
        if is_leaf_phrase_div(div):
            parent = div.parent
            div.decompose()
            # Remove parent container if it's now empty
            if parent and isinstance(parent, Tag) and not parent.get_text(strip=True):
                parent.decompose()


def parse_entry(raw_html: str) -> dict | None:
    soup = BeautifulSoup(raw_html, "lxml")

    orth = soup.find("idx:orth")
    if not orth:
        return None
    headword = orth.get("value", "").strip()
    if not headword:
        return None

    inflections = parse_inflections(soup)
    homonym_num = parse_homonym_num(soup.find("b"))
    article, gender = parse_article_gender(raw_html)
    pos = parse_pos(soup)
    phrases = parse_phrases(soup)
    strip_phrases(soup)
    body_html = parse_body_html(soup)

    return {
        "headword": headword,
        "homonym_num": homonym_num,
        "pos": pos,
        "article": article,
        "gender": gender,
        "inflections": inflections,
        "body_html": body_html,
        "phrases": phrases,
    }


def build_db(book_html: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    con = sqlite3.connect(db_path)
    con.executescript(DDL)

    total = 0
    phrase_total = 0
    inflection_total = 0

    # Commit every BATCH entries to keep memory in check while still being fast
    BATCH = 2000

    pending_entries = []
    pending_inflections = []
    pending_phrases = []

    def flush():
        nonlocal total, phrase_total, inflection_total
        if not pending_entries:
            return

        for entry, inflections, phrases in zip(pending_entries, pending_inflections, pending_phrases):
            cur = con.execute(
                """
                INSERT INTO entries
                    (headword, homonym_num, pos, article, gender, body_html)
                VALUES
                    (:headword, :homonym_num, :pos, :article, :gender, :body_html)
                """,
                entry,
            )
            entry_id = cur.lastrowid
            for value in inflections:
                con.execute(
                    "INSERT INTO inflections (entry_id, value) VALUES (?, ?)",
                    (entry_id, value),
                )
                inflection_total += 1
            for phrase in phrases:
                con.execute(
                    "INSERT INTO phrases (entry_id, dutch, translation, body_html) VALUES (?,?,?,?)",
                    (entry_id, phrase["dutch"], phrase["translation"], phrase["body_html"]),
                )
                phrase_total += 1

        con.commit()
        total += len(pending_entries)
        pending_entries.clear()
        pending_inflections.clear()
        pending_phrases.clear()

        if total % 10000 == 0:
            logger.info("Inserted {} entries, {} inflections, {} phrases...", total, inflection_total, phrase_total)

    for match in iter_raw_entries(book_html):
        entry = parse_entry(match.group())
        if entry is None:
            continue

        phrases = entry.pop("phrases")
        inflections = entry.pop("inflections")
        pending_entries.append(entry)
        pending_inflections.append(inflections)
        pending_phrases.append(phrases)

        if len(pending_entries) >= BATCH:
            flush()

    flush()

    logger.info("Building FTS indexes...")
    con.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")
    con.execute("INSERT INTO phrases_fts(phrases_fts) VALUES('rebuild')")
    con.commit()
    con.close()

    logger.info(
        "Done. {} entries, {} inflections, {} phrases -> {}",
        total,
        inflection_total,
        phrase_total,
        db_path,
    )


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python3 scripts/extract.py path/to/dictionary.mobi")
        sys.exit(1)

    mobi_file = Path(sys.argv[1])
    if not mobi_file.exists():
        logger.error("MOBI file not found: {}", mobi_file)
        sys.exit(1)

    book_html = extract_book_html(mobi_file)
    build_db(book_html, DB_FILE)


if __name__ == "__main__":
    main()
