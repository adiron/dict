/**
 * API response types shared between server and frontend.
 * These are the shapes returned by the Hono endpoints - not raw DB rows.
 * Note: inflections is string[] here (parsed from the JSON string in the DB).
 */

export interface SearchResult {
  id: number;
  headword: string;
  homonym_num: number | null;
  pos: string | null;
  article: string | null;
  gender: string | null;
  matched_inflection: string | null;
}

export interface PhraseResult {
  id: number;
  entry_id: number;
  headword: string;
  dutch: string;
  translation: string;
}

export interface SearchResponse {
  entries: SearchResult[];
  phrases: PhraseResult[];
}

export interface Phrase {
  id: number;
  dutch: string;
  translation: string;
  body_html: string;
}

export interface Entry extends SearchResult {
  inflections: string[];
  body_html: string;
  phrases: Phrase[];
}
