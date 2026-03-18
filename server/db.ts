import Database from "better-sqlite3";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const DB_PATH = path.join(root, "data", "van-dale.sqlite");

const db = new Database(DB_PATH, { readonly: true });

export default db;
