#!/usr/bin/env python3
"""
Extract a dictionary .mobi file into data/dictionary.sqlite

Schema:
  entries  - one row per <idx:entry> (headword + definition)
  phrases  - one row per ◦ fixed expression, linked to parent entry

Run: python3 scripts/extract.py path/to/dictionary.mobi
"""

import argparse
import re
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

import mobi
from lxml import etree
from loguru import logger
from tqdm import tqdm

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
    filepos     INTEGER,
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

_ARTICLE_RE = re.compile(r"<span>(de|het)(?:<sup><i>([mv])</i></sup>)?</span>")


def extract_book_html(mobi_path: Path) -> Path:
    logger.info("Extracting MOBI...")
    tmpdir, _ = mobi.extract(str(mobi_path))
    book = Path(tmpdir) / "mobi7" / "book.html"
    if not book.exists():
        logger.error("Could not find book.html in extracted MOBI at {}", tmpdir)
        sys.exit(1)
    logger.info("Extracted to {}", book)
    return book


def parse_book_html(book_html: Path) -> etree._Element:
    logger.info("Parsing book.html ({:.1f} MB)...", book_html.stat().st_size / 1e6)
    data = book_html.read_bytes()
    parser = etree.HTMLParser(encoding="utf-8")
    return etree.fromstring(data, parser)


def _text(el: etree._Element) -> str:
    """All text content of an element, stripped."""
    return "".join(el.itertext()).strip()


def _tohtml(el: etree._Element) -> str:
    return etree.tostring(el, encoding="unicode", method="html")


def _is_leaf_phrase_div(div: etree._Element) -> bool:
    """True if this div directly contains a ◦ phrase (not a container of phrase divs)."""
    text = _text(div)
    if not text.startswith("◦"):
        return False
    for child in div:
        if child.tag == "div" and _text(child).startswith("◦"):
            return False
    return True


def _parse_phrases(body_div: etree._Element) -> list[dict]:
    results = []
    seen: set[str] = set()

    for div in body_div.iter("div"):
        if not _is_leaf_phrase_div(div):
            continue
        raw_html = _tohtml(div)
        if raw_html in seen:
            continue
        seen.add(raw_html)

        full_text = " ".join(_text(div).split())
        full_text = re.sub(r"^◦\s*", "", full_text)

        if "|" in full_text:
            dutch_part, _, translation_part = full_text.partition("|")
        else:
            dutch_part, translation_part = full_text, ""

        dutch = dutch_part.strip()
        translation = translation_part.strip()
        if dutch:
            results.append({"dutch": dutch, "translation": translation, "body_html": raw_html})

    return results


def _strip_phrases(body_div: etree._Element) -> None:
    for div in list(body_div.iter("div")):
        if _is_leaf_phrase_div(div):
            parent = div.getparent()
            if parent is not None:
                parent.remove(div)
                if parent is not body_div and not _text(parent):
                    gp = parent.getparent()
                    if gp is not None:
                        gp.remove(parent)


def _strip_pos_label(body_div: etree._Element, pos: str | None) -> None:
    if not pos:
        return
    for i in body_div.iter("i"):
        if _text(i) == pos:
            node = i
            while True:
                parent = node.getparent()
                if parent is None:
                    break
                parent.remove(node)
                if parent is body_div or _text(parent):
                    break
                node = parent
            return


def _strip_presentation_attrs(body_div: etree._Element) -> None:
    for el in body_div.iter():
        el.attrib.pop("align", None)


def iter_entries(root: etree._Element):
    """Yield (filepos, entry_element) for each idx:entry in the lxml tree."""
    for el in root.iter():
        if el.tag != "idx:entry":
            continue
        anchor = next(
            (c for c in el.iter() if c.tag == "a" and (c.get("id") or "").startswith("filepos")),
            None,
        )
        filepos = int(anchor.get("id")[7:]) if anchor is not None else None
        yield filepos, el


def parse_entry(entry_el: etree._Element, keep_html: bool = False) -> dict | None:
    orth = next((c for c in entry_el if c.tag == "idx:orth"), None)
    if orth is None:
        return None
    headword = (orth.get("value") or "").strip()
    if not headword:
        return None

    inflections = [
        el.get("value")
        for el in entry_el.iter()
        if el.tag == "idx:iform" and el.get("value")
    ]

    homonym_num = None
    b = next((el for el in entry_el.iter("b")), None)
    if b is not None:
        sup = b.find("sup")
        if sup is not None:
            txt = (sup.text or "").strip()
            if txt.isdigit():
                homonym_num = int(txt)

    # Article/gender: regex on the second top-level div's HTML
    top_divs = [c for c in entry_el if c.tag == "div"]
    if not top_divs:
        return None
    body_div = top_divs[-1]

    m = _ARTICLE_RE.search(_tohtml(top_divs[0]))
    article = m.group(1) if m else None
    gender = (m.group(2) or None) if m else None

    pos = None
    for i in body_div.iter("i"):
        txt = _text(i)
        if txt in TRUE_POS:
            pos = txt
            break

    phrases = _parse_phrases(body_div)
    _strip_phrases(body_div)

    if not keep_html:
        _strip_pos_label(body_div, pos)
        _strip_presentation_attrs(body_div)

    body_html = _tohtml(body_div)

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


def resolve_links(con: sqlite3.Connection) -> None:
    """
    Replace href="#fileposN" links with /?q=headword&open=id using the
    filepos->entry mapping recorded during extraction.
    """
    rows = con.execute("SELECT id, headword, filepos FROM entries WHERE filepos IS NOT NULL").fetchall()
    filepos_map = {filepos: (eid, headword) for eid, headword, filepos in rows}

    link_rows = con.execute(
        "SELECT id, body_html FROM entries WHERE body_html LIKE '%href=\"#filepos%'"
    ).fetchall()

    updated = 0
    for entry_id, body_html in link_rows:
        def replace(m, _map=filepos_map):
            fp = int(m.group(1))
            if fp not in _map:
                return m.group(0)
            eid, headword = _map[fp]
            return f'href="/?q={quote(headword)}&open={eid}"'

        new_html = re.sub(r'href="#filepos(\d+)"', replace, body_html)
        if new_html != body_html:
            con.execute("UPDATE entries SET body_html = ? WHERE id = ?", (new_html, entry_id))
            updated += 1

    logger.info("Resolved links in {} entries", updated)


def build_db(book_html: Path, db_path: Path, keep_html: bool = False) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    root = parse_book_html(book_html)
    entry_count = sum(1 for el in root.iter() if el.tag == "idx:entry")
    logger.info("Found {} entries", entry_count)

    con = sqlite3.connect(db_path)
    con.executescript(DDL)

    total = 0
    phrase_total = 0
    inflection_total = 0

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
                    (filepos, headword, homonym_num, pos, article, gender, body_html)
                VALUES
                    (:filepos, :headword, :homonym_num, :pos, :article, :gender, :body_html)
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

    for filepos, entry_el in tqdm(iter_entries(root), total=entry_count, unit="entries", desc="Parsing"):
        entry = parse_entry(entry_el, keep_html=keep_html)
        if entry is None:
            continue
        entry["filepos"] = filepos

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

    logger.info("Resolving internal links...")
    resolve_links(con)
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
    parser = argparse.ArgumentParser(description="Extract a dictionary .mobi into dictionary.sqlite")
    parser.add_argument("mobi", type=Path, help="Path to the .mobi dictionary file")
    parser.add_argument("--keep-html", action="store_true", help="Skip HTML cleanup (keep POS label in body)")
    args = parser.parse_args()

    if not args.mobi.exists():
        logger.error("MOBI file not found: {}", args.mobi)
        sys.exit(1)

    book_html = extract_book_html(args.mobi)
    build_db(book_html, DB_FILE, keep_html=args.keep_html)


if __name__ == "__main__":
    main()
