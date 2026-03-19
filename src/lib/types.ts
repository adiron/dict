/**
 * API response types shared between server and frontend.
 * These are the shapes returned by the API endpoints.
 * Note: inflections is string[] here (fetched from the inflections table).
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
  entries: Entry[];
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
