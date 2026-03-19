import { describe, expect, it } from 'vitest';
import { getEntry, search } from './queries.js';

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

describe('getEntry', () => {
  it('returns a full entry for a valid id', () => {
    const entry = getEntry(1);
    expect(entry).not.toBeNull();
    expect(entry!).toHaveProperty('id', 1);
    expect(entry!).toHaveProperty('headword');
    expect(entry!).toHaveProperty('body_html');
    expect(entry!).toHaveProperty('inflections');
    expect(entry!).toHaveProperty('phrases');
  });

  it('inflections is a string array', () => {
    const entry = getEntry(1);
    expect(Array.isArray(entry!.inflections)).toBe(true);
    if (entry!.inflections.length > 0) {
      expect(typeof entry!.inflections[0]).toBe('string');
    }
  });

  it('phrases is an array', () => {
    const entry = getEntry(1);
    expect(Array.isArray(entry!.phrases)).toBe(true);
  });

  it('entry with known phrases includes them', () => {
    const { entries } = search('staan', 20);
    const staan = entries.find((e) => e.headword === 'staan');
    expect(staan).toBeDefined();

    const entry = getEntry(staan!.id);
    expect(entry!.phrases.length).toBeGreaterThan(0);
    expect(entry!.phrases[0]).toHaveProperty('dutch');
    expect(entry!.phrases[0]).toHaveProperty('translation');
    expect(entry!.phrases[0]).toHaveProperty('body_html');
  });

  it('returns null for unknown id', () => {
    expect(getEntry(99999999)).toBeNull();
  });

  it('matched_inflection is null for direct lookups', () => {
    const entry = getEntry(1);
    expect(entry!.matched_inflection).toBeNull();
  });
});
