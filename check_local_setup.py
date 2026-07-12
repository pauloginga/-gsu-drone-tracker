with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

print("Checking app.py...\n")

if "os.environ.get(\"DATABASE_URL\"" in content:
    print("  [OK] app.py reads DATABASE_URL from the environment.")
else:
    print("  [MISSING] app.py does NOT reference DATABASE_URL.")
    print("            -> Your local file is the OLD version.")

if "postgres://" in content and "postgresql://" in content:
    print("  [OK] app.py has the postgres:// -> postgresql:// fix.")
else:
    print("  [MISSING] The postgres:// URL fix is not present.")

print("\nChecking requirements.txt...\n")
try:
    with open("requirements.txt", "r", encoding="utf-8") as f:
        reqs = f.read()
    if "psycopg2" in reqs:
        print("  [OK] psycopg2-binary is listed in requirements.txt.")
    else:
        print("  [MISSING] psycopg2-binary is NOT in requirements.txt.")
except FileNotFoundError:
    print("  [ERROR] requirements.txt not found in this folder.")

print("\nDone.")