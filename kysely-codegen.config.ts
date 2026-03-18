import { defineConfig } from "kysely-codegen";

export default defineConfig({
  dialect: "sqlite",
  url: "data/van-dale.sqlite",
  outFile: "src/lib/db.d.ts",

  // FTS5 creates several internal shadow tables alongside each virtual table
  // (entries_fts_data, entries_fts_idx, entries_fts_config, entries_fts_docsize,
  // phrases_fts_data, etc.). These are SQLite implementation details for the
  // inverted index - never queried directly. Exclude them to keep the types clean.
  excludePattern: "*_fts_*",
});
