-- SQL script to set up the initial Linkography database

-- Table to store user information
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

-- Table to store Linkography diagrams
CREATE TABLE IF NOT EXISTS linkography (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    move_count INTEGER,
    links TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
