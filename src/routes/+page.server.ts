import type { PageServerLoad } from './$types';
import { search } from '$lib/server/queries.js';

export const load: PageServerLoad = ({ url }) => {
  const q = url.searchParams.get('q')?.trim() ?? '';
  if (!q) return { q, results: null };
  return { q, results: search(q, 20) };
};
