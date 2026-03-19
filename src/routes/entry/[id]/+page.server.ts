import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getEntry } from '$lib/server/queries.js';

export const load: PageServerLoad = ({ params }) => {
  const id = Number(params.id);
  if (!Number.isInteger(id)) throw error(400, 'Invalid id');

  const entry = getEntry(id);
  if (!entry) throw error(404, 'Entry not found');

  return { entry };
};
