import Database from 'better-sqlite3';
import { resolve } from 'path';

const DB_PATH = resolve('data/van-dale.sqlite');
const db = new Database(DB_PATH, { readonly: true });

export default db;
