import sqlite3
import os
import sys
# Try to import tabulate, but fallback if not available
try:
    from tabulate import tabulate
except ImportError:
    def tabulate(data, headers=(), tablefmt="simple"):
        # Simple fallback formatter
        if not data:
            return ""
        
        # Calculate max width for each column
        col_widths = [len(h) for h in headers]
        for row in data:
            for i, val in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(val)))
        
        # Format header
        header_str = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        separator = "-+-".join("-" * w for w in col_widths)
        
        rows_str = []
        for row in data:
            rows_str.append(" | ".join(str(val).ljust(w) for val, w in zip(row, col_widths)))
            
        return f"{header_str}\n{separator}\n" + "\n".join(rows_str)

import argparse

# Determine DB path
# Assuming this script is in backend/tools/inspect_db.py
# DB is in backend/shortmaker.db
# We go up one level from 'tools' to 'backend'
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(BACKEND_DIR, "shortmaker.db")

def connect_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def get_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [t[0] for t in tables]

def inspect_table(conn, table_name, limit=5):
    cursor = conn.cursor()
    try:
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count_res = cursor.fetchone()
        count = count_res[0] if count_res else 0
        
        print(f"\n--- Table: {table_name} (Total Rows: {count}) ---")

        # Get columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        if count > 0:
            # Get data
            query = f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT ?"
            cursor.execute(query, (limit,))
            rows = cursor.fetchall()
            print(tabulate(rows, headers=columns, tablefmt="grid"))
        else:
            print("(Empty Table)")
            
    except sqlite3.OperationalError as e:
        print(f"Error inspecting {table_name}: {e}")

def run_query(conn, query):
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("PRAGMA"):
            rows = cursor.fetchall()
            if cursor.description:
                headers = [d[0] for d in cursor.description]
                print(tabulate(rows, headers=headers, tablefmt="grid"))
            else:
                print(rows)
        else:
            conn.commit()
            print(f"Query executed. Rows affected: {cursor.rowcount}")
    except sqlite3.Error as e:
        print(f"SQL Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Inspect ShortMaker SQLite Database")
    parser.add_argument("--table", help="Inspect a specific table")
    parser.add_argument("--query", "-q", help="Run a raw SQL query. Enclose in quotes.")
    parser.add_argument("--all", action="store_true", help="Inspect all tables")
    args = parser.parse_args()

    print(f"Database Path: {DB_PATH}")
    
    try:
        conn = connect_db()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    if args.query:
        run_query(conn, args.query)
    elif args.table:
        inspect_table(conn, args.table, limit=20)
    elif args.all:
        tables = get_tables(conn)
        for table in tables:
            inspect_table(conn, table)
    else:
        # Default behavior: List tables and show summary
        tables = get_tables(conn)
        print(f"Found Tables: {', '.join(tables)}")
        print("\nUsage:")
        print("  python inspect_db.py --table <name>   (View recently added rows)")
        print("  python inspect_db.py --query \"SELECT * FROM scheduled_posts\"")
        print("  python inspect_db.py --all            (View everything)")

if __name__ == "__main__":
    main()
