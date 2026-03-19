import { describe, expect, it } from 'vitest';
import { search } from './queries.js';

describe('search', () => {
  it('returns entries and phrases arrays', () => {
    const result = search('fiets', 20);
    expect(Array.isArray(result.entries)).toBe(true);
    expect(Array.isArray(result.phrases)).toBe(true);
  });

  it('returns entry results matching the query prefix', () => {
    const result = search('fiets', 20);
    const headwords = result.entries.map((e) => e.headword);
    expect(headwords.some((h) => h.startsWith('fiets'))).toBe(true);
  });

  it('entry results include expected fields', () => {
    const result = search('bank', 20);
    const entry = result.entries[0];
    expect(entry).toHaveProperty('id');
    expect(entry).toHaveProperty('headword');
    expect(entry).toHaveProperty('homonym_num');
    expect(entry).toHaveProperty('pos');
    expect(entry).toHaveProperty('article');
    expect(entry).toHaveProperty('gender');
    expect(entry).toHaveProperty('matched_inflection');
  });

  it('returns empty results for blank query', () => {
    const result = search('', 20);
    expect(result.entries).toHaveLength(0);
    expect(result.phrases).toHaveLength(0);
  });

  it('returns empty results when nothing matches', () => {
    const result = search('zzzznotaword', 20);
    expect(result.entries).toHaveLength(0);
    expect(result.phrases).toHaveLength(0);
  });

  it('respects the limit', () => {
    const result = search('de', 5);
    expect(result.entries.length).toBeLessThanOrEqual(5);
  });

  it('phrase results include expected fields', () => {
    const result = search('staan', 20);
    if (result.phrases.length > 0) {
      const phrase = result.phrases[0];
      expect(phrase).toHaveProperty('id');
      expect(phrase).toHaveProperty('entry_id');
      expect(phrase).toHaveProperty('headword');
      expect(phrase).toHaveProperty('dutch');
      expect(phrase).toHaveProperty('translation');
    }
  });

  it('direct headword matches have matched_inflection null', () => {
    const result = search('fiets', 20);
    const exact = result.entries.find((e) => e.headword === 'fiets');
    expect(exact).toBeDefined();
    expect(exact!.matched_inflection).toBeNull();
  });

  it('inflection search finds the base entry', () => {
    const result = search('stond', 20);
    const staan = result.entries.find((e) => e.headword === 'staan');
    expect(staan).toBeDefined();
  });

  it('exact inflection match ranks before prefix headword match', () => {
    // 'stond' is an exact inflection of 'staan'; 'stonde' is a headword starting with 'stond'
    const result = search('stond', 20);
    const staanIdx = result.entries.findIndex((e) => e.headword === 'staan');
    const stondeIdx = result.entries.findIndex((e) => e.headword === 'stonde');
    expect(staanIdx).toBeGreaterThanOrEqual(0);
    expect(staanIdx).toBeLessThan(stondeIdx === -1 ? Infinity : stondeIdx);
  });

  it('inflection match has matched_inflection set', () => {
    const result = search('stond', 20);
    const staan = result.entries.find((e) => e.headword === 'staan');
    expect(staan!.matched_inflection).toBeTruthy();
    expect(staan!.matched_inflection!.toLowerCase()).toMatch(/^stond/);
  });

  it('no duplicate entry ids', () => {
    const result = search('stond', 20);
    const ids = result.entries.map((e) => e.id);
    expect(ids.length).toBe(new Set(ids).size);
  });
});

