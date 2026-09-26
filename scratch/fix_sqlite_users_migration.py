with open("db.py", "r") as f:
    content = f.read()

migration_code = """
            # SQLite users table role CHECK constraint migration
            if db_type != "postgres":
                try:
                    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
                    row = cursor.fetchone()
                    if row and "'logistics'" not in row[0]:
                        cursor.execute("PRAGMA foreign_keys=OFF")
                        cursor.execute("CREATE TABLE users_old AS SELECT * FROM users")
                        cursor.execute("DROP TABLE users")
                        cursor.execute(\"\"\"
                            CREATE TABLE users (
                                id TEXT PRIMARY KEY,
                                email TEXT UNIQUE NOT NULL,
                                password_hash TEXT NOT NULL,
                                role TEXT CHECK (role IN ('farmer', 'buyer', 'admin', 'logistics')) NOT NULL,
                                account_status TEXT CHECK (account_status IN ('pending', 'active', 'suspended')) DEFAULT 'pending' NOT NULL,
                                suspension_reason TEXT,
                                email_verified INTEGER DEFAULT 0,
                                email_verified_at TEXT,
                                phone_verified INTEGER DEFAULT 0,
                                phone_verified_at TEXT,
                                otp_hash TEXT,
                                otp_expires_at TEXT,
                                otp_attempts INTEGER DEFAULT 0,
                                otp_last_sent_at TEXT,
                                verification_token TEXT,
                                created_at TEXT NOT NULL,
                                updated_at TEXT NOT NULL
                            );
                        \"\"\")
                        cursor.execute("INSERT INTO users SELECT * FROM users_old")
                        cursor.execute("DROP TABLE users_old")
                        cursor.execute("PRAGMA foreign_keys=ON")
                except Exception as e:
                    print("[!] SQLite users table migration warning:", e)
"""

if "SQLite users table role CHECK constraint migration" not in content:
    content = content.replace("# Order Logistics Column Migrations", migration_code + "\n            # Order Logistics Column Migrations")

with open("db.py", "w") as f:
    f.write(content)

print("[+] SQLite users migration added to db.py.")
