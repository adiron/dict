import { serveStatic } from "@hono/node-server/serve-static";
import { Hono } from "hono";
import { logger } from "hono/logger";
import db from "./db.ts";
import type { Entry, PhraseResult, SearchResponse, SearchResult } from "./types.ts";

const app = new Hono();

app.use(logger());

// ---------------------------------------------------------------------------
// GET /search?q=<query>&limit=<n>
//
// Searches headwords by prefix and phrase text by token.
// Returns matching entries and phrases separately so the frontend can
// render them in two groups.
// ---------------------------------------------------------------------------
app.get("/api/search", (c) => {
  const q = c.req.query("q")?.trim();
  const limit = Math.min(Number(c.req.query("limit") ?? 20), 100);

  if (!q || q.length < 1) {
    return c.json<SearchResponse>({ entries: [], phrases: [] });
  }

  type RankedResult = SearchResult & { _rank: number };

  const headwordEntries = db
    .prepare(
      `SELECT e.id, e.headword, e.homonym_num, e.pos, e.article, e.gender,
              NULL as matched_inflection,
              CASE WHEN e.headword = ? THEN 0 ELSE 2 END as _rank
       FROM entries_fts f
       JOIN entries e ON e.id = f.rowid
       WHERE entries_fts MATCH 'headword: ' || ?
       LIMIT ?`,
    )
    .all(q, `${q}*`, limit) as RankedResult[];

  const headwordIds = new Set(headwordEntries.map((e) => e.id));

  const inflectionEntries = db
    .prepare(
      `SELECT e.id, e.headword, e.homonym_num, e.pos, e.article, e.gender,
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

  const entries = [
    ...headwordEntries,
    ...inflectionEntries.filter((e) => !headwordIds.has(e.id)),
  ]
    .sort((a, b) => a._rank - b._rank || a.headword.length - b.headword.length)
    .slice(0, limit)
    .map(({ _rank: _r, ...e }) => e) as SearchResult[];

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

  return c.json<SearchResponse>({ entries, phrases });
});

// ---------------------------------------------------------------------------
// GET /entry/:id
//
// Full entry by id - includes body_html and all linked phrases.
// ---------------------------------------------------------------------------
app.get("/api/entry/:id", (c) => {
  const id = Number(c.req.param("id"));

  if (!Number.isInteger(id)) {
    return c.json({ error: "invalid id" }, 400);
  }

  const row = db
    .prepare(
      `SELECT id, headword, homonym_num, pos, article, gender, body_html
       FROM entries WHERE id = ?`,
    )
    .get(id) as Omit<Entry, "inflections" | "phrases" | "matched_inflection"> | undefined;

  if (!row) {
    return c.json({ error: "not found" }, 404);
  }

  const inflections = (
    db
      .prepare(`SELECT value FROM inflections WHERE entry_id = ? ORDER BY id`)
      .all(id) as { value: string }[]
  ).map((r) => r.value);

  const phrases = db
    .prepare(
      `SELECT id, dutch, translation, body_html FROM phrases WHERE entry_id = ?`,
    )
    .all(id) as Entry["phrases"];

  const entry: Entry = {
    ...row,
    matched_inflection: null,
    inflections,
    phrases,
  };

  return c.json<Entry>(entry);
});

// ---------------------------------------------------------------------------
// Static frontend - production only
// In dev the Vite dev server handles the frontend on a separate port.
// ---------------------------------------------------------------------------
if (process.env["NODE_ENV"] === "production") {
  app.use("/*", serveStatic({ root: "./dist" }));
}

export default app;
