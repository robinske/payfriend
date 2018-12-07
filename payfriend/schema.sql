-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS payments;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  phone_number TEXT UNIQUE NOT NULL,
  authy_id INTEGER UNIQUE,
  verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE payments (
  request_id TEXT PRIMARY KEY,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  authy_id INTEGER NOT NULL,
  send_to TEXT NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT DEFAULT 'pending',
  FOREIGN KEY (authy_id) REFERENCES users (authy_id)
);
