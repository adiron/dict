"""Tests for extract.py parsing functions."""

import pytest
from bs4 import BeautifulSoup

from extract import (
    is_leaf_phrase_div,
    parse_article_gender,
    parse_body_html,
    parse_entry,
    parse_homonym_num,
    parse_inflections,
    parse_phrases,
    parse_pos,
    strip_phrases,
)

# ---------------------------------------------------------------------------
# Fixtures - minimal HTML snippets representative of real entries
# ---------------------------------------------------------------------------

SIMPLE_NOUN = """
<idx:entry scriptable="yes">
  <idx:orth value="fiets">
    <idx:infl>
      <idx:iform name="" value="fietsen"/>
      <idx:iform name="" value="fietsje"/>
    </idx:infl>
  </idx:orth>
  <div><div><b>fiets</b></div><div><span>de<sup><i>v</i></sup></span></div></div>
  <div><div><div><span><i>zelfst nw</i></span></div>
    <div><span><span><b>bicycle</b></span>; <span>bike</span></span></div>
  </div></div>
</idx:entry>
"""

HOMONYM_VERB = """
<idx:entry scriptable="yes">
  <idx:orth value="lopen">
    <idx:infl>
      <idx:iform name="" value="liep"/>
      <idx:iform name="" value="gelopen"/>
    </idx:infl>
  </idx:orth>
  <div><div><b>lopen<sup>1</sup></b></div></div>
  <div><div><div><span><i>onov ww</i></span></div>
    <div><span><b>walk</b></span></div>
  </div></div>
</idx:entry>
"""

NEUTER_NOUN = """
<idx:entry scriptable="yes">
  <idx:orth value="huis"/>
  <div><div><b>huis</b></div><div><span>het</span></div></div>
  <div><div><div><span><i>zelfst nw</i></span></div>
    <div><span><b>house</b></span></div>
  </div></div>
</idx:entry>
"""

ENTRY_WITH_PHRASES = """
<idx:entry scriptable="yes">
  <idx:orth value="staan"/>
  <div><div><b>staan</b></div></div>
  <div>
    <div><div><span><i>onov ww</i></span></div>
      <div><span><b>stand</b></span></div>
    </div>
    <div>
      <div><span><b>◦ </b></span><span><i>ergens voor staan</i></span> | <span>stand for something</span></div>
      <div><span><b>◦ </b></span><span><i>dat komt duur te staan</i></span> | <span>that will cost you</span></div>
    </div>
  </div>
</idx:entry>
"""

ENTRY_WITH_NESTED_PHRASE_CONTAINER = """
<idx:entry scriptable="yes">
  <idx:orth value="à"/>
  <div><div><b>à</b></div></div>
  <div><div><div><span><i>vz</i></span></div>
    <div><span><b>at</b></span></div>
  </div>
  <div>
    <div><span><b>◦ </b></span><span><i>à l'improviste</i></span> | <span>impromptu</span></div>
    <div><span><b>◦ </b></span><span><i>à titre personnel</i></span> | <span>personally</span></div>
  </div>
  </div>
</idx:entry>
"""

NO_POS_WITH_PHRASE = """
<idx:entry scriptable="yes">
  <idx:orth value="aagje"/>
  <div><div><b>aagje</b></div></div>
  <div><div><div></div></div>
    <div>
      <div><span><b>◦ </b></span><span><i>nieuwsgierig aagje</i></span> | <span>Nosy Parker</span></div>
    </div>
  </div>
</idx:entry>
"""

ABBREVIATION = """
<idx:entry scriptable="yes">
  <idx:orth value="AA"/>
  <div><div><b>AA</b></div></div>
  <div><div><div><span><i>afk</i></span></div>
    <div><span><b>Alcoholics Anonymous</b></span></div>
  </div></div>
</idx:entry>
"""


# ---------------------------------------------------------------------------
# parse_homonym_num
# ---------------------------------------------------------------------------

def test_homonym_num_present():
    soup = BeautifulSoup(HOMONYM_VERB, "lxml")
    assert parse_homonym_num(soup.find("b")) == 1


def test_homonym_num_absent():
    soup = BeautifulSoup(SIMPLE_NOUN, "lxml")
    assert parse_homonym_num(soup.find("b")) is None


def test_homonym_num_none_tag():
    assert parse_homonym_num(None) is None


# ---------------------------------------------------------------------------
# parse_article_gender
# ---------------------------------------------------------------------------

def test_article_de_with_gender():
    article, gender = parse_article_gender(SIMPLE_NOUN)
    assert article == "de"
    assert gender == "v"


def test_article_het_no_gender():
    article, gender = parse_article_gender(NEUTER_NOUN)
    assert article == "het"
    assert gender is None


def test_article_absent_for_verb():
    article, gender = parse_article_gender(HOMONYM_VERB)
    assert article is None
    assert gender is None


# ---------------------------------------------------------------------------
# parse_pos
# ---------------------------------------------------------------------------

def test_pos_noun():
    soup = BeautifulSoup(SIMPLE_NOUN, "lxml")
    assert parse_pos(soup) == "zelfst nw"


def test_pos_verb():
    soup = BeautifulSoup(HOMONYM_VERB, "lxml")
    assert parse_pos(soup) == "onov ww"


def test_pos_abbreviation():
    soup = BeautifulSoup(ABBREVIATION, "lxml")
    assert parse_pos(soup) == "afk"


def test_pos_none_when_absent():
    soup = BeautifulSoup(NO_POS_WITH_PHRASE, "lxml")
    assert parse_pos(soup) is None


# ---------------------------------------------------------------------------
# parse_inflections
# ---------------------------------------------------------------------------

def test_inflections_present():
    soup = BeautifulSoup(SIMPLE_NOUN, "lxml")
    assert parse_inflections(soup) == ["fietsen", "fietsje"]


def test_inflections_empty():
    soup = BeautifulSoup(NEUTER_NOUN, "lxml")
    assert parse_inflections(soup) == []


# ---------------------------------------------------------------------------
# is_leaf_phrase_div / parse_phrases
# ---------------------------------------------------------------------------

def test_phrase_extraction():
    soup = BeautifulSoup(ENTRY_WITH_PHRASES, "lxml")
    phrases = parse_phrases(soup)
    assert len(phrases) == 2
    dutches = [p["dutch"] for p in phrases]
    assert "ergens voor staan" in dutches
    assert "dat komt duur te staan" in dutches


def test_phrase_translation():
    soup = BeautifulSoup(ENTRY_WITH_PHRASES, "lxml")
    phrases = parse_phrases(soup)
    by_dutch = {p["dutch"]: p["translation"] for p in phrases}
    assert by_dutch["dat komt duur te staan"] == "that will cost you"


def test_phrase_no_duplicates():
    soup = BeautifulSoup(ENTRY_WITH_NESTED_PHRASE_CONTAINER, "lxml")
    phrases = parse_phrases(soup)
    dutches = [p["dutch"] for p in phrases]
    assert len(dutches) == len(set(dutches))


def test_no_phrases_when_absent():
    soup = BeautifulSoup(SIMPLE_NOUN, "lxml")
    assert parse_phrases(soup) == []


def test_phrase_without_translation():
    html = """
    <idx:entry scriptable="yes">
      <idx:orth value="test"/>
      <div><div><b>test</b></div></div>
      <div><div>
        <div><span><b>◦ </b></span><span><i>op de proef stellen</i></span></div>
      </div></div>
    </idx:entry>
    """
    soup = BeautifulSoup(html, "lxml")
    phrases = parse_phrases(soup)
    assert len(phrases) == 1
    assert phrases[0]["dutch"] == "op de proef stellen"
    assert phrases[0]["translation"] == ""


# ---------------------------------------------------------------------------
# parse_entry (integration)
# ---------------------------------------------------------------------------

def test_parse_entry_simple_noun():
    entry = parse_entry(SIMPLE_NOUN)
    assert entry is not None
    assert entry["headword"] == "fiets"
    assert entry["pos"] == "zelfst nw"
    assert entry["article"] == "de"
    assert entry["gender"] == "v"
    assert entry["homonym_num"] is None
    assert "fietsen" in entry["inflections"]
    assert entry["phrases"] == []
    assert entry["body_html"] != ""


def test_parse_entry_with_homonym():
    entry = parse_entry(HOMONYM_VERB)
    assert entry is not None
    assert entry["headword"] == "lopen"
    assert entry["homonym_num"] == 1
    assert entry["pos"] == "onov ww"
    assert entry["article"] is None


def test_parse_entry_with_phrases():
    entry = parse_entry(ENTRY_WITH_PHRASES)
    assert entry is not None
    assert len(entry["phrases"]) == 2

def test_parse_entry_phrases_stripped_from_body_html():
    entry = parse_entry(ENTRY_WITH_PHRASES)
    assert entry is not None
    assert "◦" not in entry["body_html"]


def test_parse_entry_no_orth_returns_none():
    html = "<idx:entry scriptable='yes'><div><b>test</b></div></idx:entry>"
    assert parse_entry(html) is None


def test_parse_entry_empty_headword_returns_none():
    html = '<idx:entry scriptable="yes"><idx:orth value=""/></idx:entry>'
    assert parse_entry(html) is None


def test_parse_entry_inflections_empty_list_when_absent():
    entry = parse_entry(NEUTER_NOUN)
    assert entry is not None
    assert entry["inflections"] == []
