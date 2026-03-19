import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { search } from '$lib/server/queries.js';

export const GET: RequestHandler = ({ url }) => {
  const q = url.searchParams.get('q')?.trim() ?? '';
  const limit = Math.min(Number(url.searchParams.get('limit') ?? 20), 100);

  if (!q) {
    return json({ entries: [], phrases: [] });
  }

  return json(search(q, limit));
};
