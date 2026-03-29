import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";

import * as schema from "./schema/index";

/** Local default matches README; override with CMS_DATABASE_URL in all real environments. */
const connectionString =
  process.env.CMS_DATABASE_URL ??
  "postgres://sidekick:sidekick@127.0.0.1:5432/sidekick_cms";

const client = postgres(connectionString, { max: 10 });

export const db = drizzle(client, { schema });
export type Database = typeof db;
