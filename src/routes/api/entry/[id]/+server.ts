import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getEntry } from '$lib/server/queries.js';

export const GET: RequestHandler = ({ params }) => {
  const id = Number(params.id);

  if (!Number.isInteger(id)) {
    throw error(400, 'invalid id');
  }

  const entry = getEntry(id);
  if (!entry) {
    throw error(404, 'not found');
  }

  return json(entry);
};
