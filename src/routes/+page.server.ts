import type { PageServerLoad } from './$types';
import { search } from '$lib/server/queries.js';

export const load: PageServerLoad = ({ url }) => {
  const q = url.searchParams.get('q')?.trim() ?? '';
  const openParam = url.searchParams.get('open');
  const openId = openParam ? parseInt(openParam, 10) : null;
  if (!q) return { q, results: null, openId: null };
  return { q, results: search(q, 20), openId };
};
