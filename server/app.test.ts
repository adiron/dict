import { describe, expect, it } from "vitest";
import app from "./app.ts";
import type { Entry, SearchResponse } from "./types.ts";

// Hono exposes app.request() for in-process testing - no HTTP server needed.

async function search(query: string): Promise<SearchResponse> {
  const res = await app.request(`/api/search?q=${encodeURIComponent(query)}`);
  return res.json() as Promise<SearchResponse>;
}

async function searchWithLimit(query: string, limit: number): Promise<SearchResponse> {
  const res = await app.request(`/api/search?q=${encodeURIComponent(query)}&limit=${limit}`);
  return res.json() as Promise<SearchResponse>;
}

async function getEntry(id: number): Promise<{ res: Response; body: Entry }> {
  const res = await app.request(`/api/entry/${id}`);
  const body = await res.json() as Entry;
  return { res, body };
}

describe("GET /search", () => {
  it("returns entries and phrases arrays", async () => {
    const res = await app.request("/api/search?q=fiets");
    expect(res.status).toBe(200);
    const body = await search("fiets");
    expect(Array.isArray(body.entries)).toBe(true);
    expect(Array.isArray(body.phrases)).toBe(true);
  });

  it("returns entry results matching the query prefix", async () => {
    const body = await search("fiets");
    const headwords = body.entries.map((e) => e.headword);
    expect(headwords.some((h) => h.startsWith("fiets"))).toBe(true);
  });

  it("entry results include expected fields and exclude body_html and inflections", async () => {
    const body = await search("bank");
    const entry = body.entries[0];
    expect(entry).toHaveProperty("id");
    expect(entry).toHaveProperty("headword");
    expect(entry).toHaveProperty("homonym_num");
    expect(entry).toHaveProperty("pos");
    expect(entry).toHaveProperty("article");
    expect(entry).toHaveProperty("gender");
    expect(entry).not.toHaveProperty("body_html");
    expect(entry).not.toHaveProperty("inflections");
  });

  it("returns empty results for blank query", async () => {
    const res = await app.request("/api/search?q=");
    expect(res.status).toBe(200);
    const body = await res.json() as SearchResponse;
    expect(body.entries).toHaveLength(0);
    expect(body.phrases).toHaveLength(0);
  });

  it("returns empty results when nothing matches", async () => {
    const body = await search("zzzznotaword");
    expect(body.entries).toHaveLength(0);
    expect(body.phrases).toHaveLength(0);
  });

  it("respects the limit parameter", async () => {
    const body = await searchWithLimit("de", 5);
    expect(body.entries.length).toBeLessThanOrEqual(5);
  });

  it("caps limit at 100", async () => {
    const body = await searchWithLimit("de", 999);
    expect(body.entries.length).toBeLessThanOrEqual(100);
  });

  it("phrase results include the expected fields", async () => {
    // 'staan' has known fixed expressions
    const body = await search("staan");
    if (body.phrases.length > 0) {
      const phrase = body.phrases[0];
      expect(phrase).toHaveProperty("id");
      expect(phrase).toHaveProperty("entry_id");
      expect(phrase).toHaveProperty("headword");
      expect(phrase).toHaveProperty("dutch");
      expect(phrase).toHaveProperty("translation");
    }
  });

  it("entry results include matched_inflection field", async () => {
    const body = await search("fiets");
    expect(body.entries.length).toBeGreaterThan(0);
    expect(body.entries[0]).toHaveProperty("matched_inflection");
  });

  it("direct headword matches have matched_inflection null", async () => {
    const body = await search("fiets");
    const exact = body.entries.find((e) => e.headword === "fiets");
    expect(exact).toBeDefined();
    expect(exact!.matched_inflection).toBeNull();
  });

  it("inflection search finds the base entry", async () => {
    // 'stond' is an inflection of 'staan'
    const body = await search("stond");
    const staan = body.entries.find((e) => e.headword === "staan");
    expect(staan).toBeDefined();
  });

  it("inflection match has matched_inflection set", async () => {
    const body = await search("stond");
    const staan = body.entries.find((e) => e.headword === "staan");
    expect(staan).toBeDefined();
    expect(staan!.matched_inflection).toBeTruthy();
    expect(staan!.matched_inflection!.toLowerCase()).toMatch(/^stond/);
  });
});

describe("GET /entry/:id", () => {
  it("returns a full entry for a valid id", async () => {
    const { res, body } = await getEntry(1);
    expect(res.status).toBe(200);
    expect(body).toHaveProperty("id", 1);
    expect(body).toHaveProperty("headword");
    expect(body).toHaveProperty("pos");
    expect(body).toHaveProperty("body_html");
    expect(body).toHaveProperty("inflections");
    expect(body).toHaveProperty("phrases");
  });

  it("inflections is a parsed string array", async () => {
    const { body } = await getEntry(1);
    expect(Array.isArray(body.inflections)).toBe(true);
    if (body.inflections.length > 0) {
      expect(typeof body.inflections[0]).toBe("string");
    }
  });

  it("phrases is an array", async () => {
    const { body } = await getEntry(1);
    expect(Array.isArray(body.phrases)).toBe(true);
  });

  it("entry with known phrases includes them", async () => {
    const { entries } = await search("staan");
    const staan = entries.find((e) => e.headword === "staan");
    expect(staan).toBeDefined();

    const { body } = await getEntry(staan!.id);
    expect(body.phrases.length).toBeGreaterThan(0);
    expect(body.phrases[0]).toHaveProperty("dutch");
    expect(body.phrases[0]).toHaveProperty("translation");
    expect(body.phrases[0]).toHaveProperty("body_html");
  });

  it("returns 404 for unknown id", async () => {
    const res = await app.request("/api/entry/99999999");
    expect(res.status).toBe(404);
    const body = await res.json() as { error: string };
    expect(body).toHaveProperty("error");
  });

  it("returns 400 for non-integer id", async () => {
    const res = await app.request("/api/entry/abc");
    expect(res.status).toBe(400);
    const body = await res.json() as { error: string };
    expect(body).toHaveProperty("error");
  });
});
