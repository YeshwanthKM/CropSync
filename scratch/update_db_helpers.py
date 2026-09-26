with open("db.py", "r") as f:
    content = f.read()

# 1. Update get_user_by_email and get_user_by_id to left join logistics_profiles
content = content.replace("COALESCE(fp.name, bp.name, 'Admin') as name,", "COALESCE(fp.name, bp.name, lp.company_name, 'Admin') as name,")
content = content.replace("COALESCE(fp.phone, bp.phone) as phone,", "COALESCE(fp.phone, bp.phone, lp.phone) as phone,")
content = content.replace("COALESCE(fp.address, bp.address) as address,", "COALESCE(fp.address, bp.address, lp.service_area) as address,")
content = content.replace("COALESCE(fp.location, bp.location) as location,", "COALESCE(fp.location, bp.location, lp.service_area) as location,")
content = content.replace("LEFT JOIN buyer_profiles bp ON u.id = bp.user_id", "LEFT JOIN buyer_profiles bp ON u.id = bp.user_id\n                LEFT JOIN logistics_profiles lp ON u.id = lp.user_id")

# 2. Update create_user to support role == 'logistics'
logistics_postgres_prof = """            elif role == 'buyer':
                prof_sql = \"\"\"
                    INSERT INTO buyer_profiles (user_id, name, phone, organization, address, location)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, phone = EXCLUDED.phone, organization = EXCLUDED.organization, location = EXCLUDED.location
                \"\"\"
                cursor.execute(prof_sql, (uid, name, phone, organization, address, location))
            elif role == 'logistics':
                prof_sql = \"\"\"
                    INSERT INTO logistics_profiles (user_id, company_name, phone, service_area)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET company_name = EXCLUDED.company_name, phone = EXCLUDED.phone, service_area = EXCLUDED.service_area
                \"\"\"
                cursor.execute(prof_sql, (uid, name, phone, address or location or "Pan-India"))"""

content = content.replace("""            elif role == 'buyer':
                prof_sql = \"\"\"
                    INSERT INTO buyer_profiles (user_id, name, phone, organization, address, location)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET name = EXCLUDED.name, phone = EXCLUDED.phone, organization = EXCLUDED.organization, location = EXCLUDED.location
                \"\"\"
                cursor.execute(prof_sql, (uid, name, phone, organization, address, location))""", logistics_postgres_prof)

logistics_sqlite_prof = """            elif role == 'buyer':
                prof_sql = \"\"\"
                    INSERT INTO buyer_profiles (id, user_id, name, phone, organization, address, location, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                \"\"\"
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, organization, address, location, now, now))
            elif role == 'logistics':
                prof_sql = \"\"\"
                    INSERT INTO logistics_profiles (id, user_id, company_name, phone, service_area, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                \"\"\"
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, address or location or "Pan-India", now, now))"""

content = content.replace("""            elif role == 'buyer':
                prof_sql = \"\"\"
                    INSERT INTO buyer_profiles (id, user_id, name, phone, organization, address, location, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                \"\"\"
                cursor.execute(prof_sql, (str(uuid.uuid4()), uid, name, phone, organization, address, location, now, now))""", logistics_sqlite_prof)

with open("db.py", "w") as f:
    f.write(content)

print("[+] User helper functions in db.py updated for logistics role.")
