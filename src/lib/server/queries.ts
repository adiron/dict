import type { Entry, Phrase, PhraseResult, SearchResponse, SearchResult } from '$lib/types.js';
import db from './db.js';

type RankedResult = Pick<SearchResult, 'id' | 'matched_inflection'> & { _rank: number };

function hydrateEntries(ranked: RankedResult[]): Entry[] {
  if (ranked.length === 0) return [];

  const ids = ranked.map((r) => r.id);
  const ph = ids.map(() => '?').join(',');

  const rows = db
    .prepare(
      `SELECT id, headword, homonym_num, pos, article, gender, body_html
       FROM entries WHERE id IN (${ph})`,
    )
    .all(...ids) as Omit<Entry, 'inflections' | 'phrases' | 'matched_inflection'>[];

  const inflectionRows = db
    .prepare(`SELECT entry_id, value FROM inflections WHERE entry_id IN (${ph}) ORDER BY id`)
    .all(...ids) as { entry_id: number; value: string }[];

  const phraseRows = db
    .prepare(`SELECT id, entry_id, dutch, translation, body_html FROM phrases WHERE entry_id IN (${ph})`)
    .all(...ids) as (Phrase & { entry_id: number })[];

  const inflectionsByEntry = new Map<number, string[]>();
  for (const { entry_id, value } of inflectionRows) {
    const arr = inflectionsByEntry.get(entry_id) ?? [];
    arr.push(value);
    inflectionsByEntry.set(entry_id, arr);
  }

  const phrasesByEntry = new Map<number, Phrase[]>();
  for (const { entry_id, ...phrase } of phraseRows) {
    const arr = phrasesByEntry.get(entry_id) ?? [];
    arr.push(phrase);
    phrasesByEntry.set(entry_id, arr);
  }

  const rowById = new Map(rows.map((r) => [r.id, r]));

  return ranked.map(({ id, matched_inflection }) => ({
    ...rowById.get(id)!,
    matched_inflection,
    inflections: inflectionsByEntry.get(id) ?? [],
    phrases: phrasesByEntry.get(id) ?? [],
  }));
}

export function search(q: string, limit: number): SearchResponse {
  if (!q) return { entries: [], phrases: [] };

  const headwordRanked = db
    .prepare(
      `SELECT e.id, NULL as matched_inflection,
              CASE WHEN e.headword = ? THEN 0 ELSE 2 END as _rank
       FROM entries_fts f
       JOIN entries e ON e.id = f.rowid
       WHERE entries_fts MATCH 'headword: ' || ?
       LIMIT ?`,
    )
    .all(q, `${q}*`, limit) as RankedResult[];

  const headwordIds = new Set(headwordRanked.map((e) => e.id));

  const inflectionRanked = db
    .prepare(
      `SELECT e.id,
              MIN(CASE WHEN lower(i.value) = lower(?) THEN i.value ELSE NULL END) as matched_inflection,
              MIN(CASE WHEN lower(i.value) = lower(?) THEN 1 ELSE 3 END) as _rank
       FROM inflections i
       JOIN entries e ON e.id = i.entry_id
       WHERE lower(i.value) LIKE lower(?) || '%'
       GROUP BY e.id
       ORDER BY _rank, length(e.headword)
       LIMIT ?`,
    )
    .all(q, q, q, limit) as RankedResult[];

  const ranked = [
    ...headwordRanked,
    ...inflectionRanked.filter((e) => !headwordIds.has(e.id)),
  ]
    .sort((a, b) => a._rank - b._rank)
    .slice(0, limit);

  const entries = hydrateEntries(ranked);

  const phrases = db
    .prepare(
      `SELECT p.id, p.entry_id, e.headword, p.dutch, p.translation
       FROM phrases_fts f
       JOIN phrases p ON p.id = f.rowid
       JOIN entries e ON e.id = p.entry_id
       WHERE phrases_fts MATCH ?
       ORDER BY rank
       LIMIT ?`,
    )
    .all(`${q}*`, limit) as PhraseResult[];

  return { entries, phrases };
}

export function getEntry(id: number): Entry | null {
  const row = db
    .prepare(
      `SELECT id, headword, homonym_num, pos, article, gender, body_html
       FROM entries WHERE id = ?`,
    )
    .get(id) as Omit<Entry, 'inflections' | 'phrases' | 'matched_inflection'> | undefined;

  if (!row) return null;

  const inflections = (
    db
      .prepare(`SELECT value FROM inflections WHERE entry_id = ? ORDER BY id`)
      .all(id) as { value: string }[]
  ).map((r) => r.value);

  const phrases = db
    .prepare(`SELECT id, dutch, translation, body_html FROM phrases WHERE entry_id = ?`)
    .all(id) as Entry['phrases'];

  return { ...row, matched_inflection: null, inflections, phrases };
}
