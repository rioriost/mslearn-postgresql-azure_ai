#!/usr/bin/env python

# built-in modules
import os
import sys

cur_python = f"python{sys.version_info[0]}.{sys.version_info[1]}"

# third-party modules
try:
    import psycopg as pg
    from psycopg.rows import namedtuple_row
except ModuleNotFoundError:
    os.system(f'{cur_python} -m pip install psycopg')
    import psycopg as pg
    from psycopg.rows import namedtuple_row

def input_number(prompt: str) -> int:
    num = 0
    while num == 0:
        try:
            num = int(input(prompt))
        except ValueError:
            print("Please enter a valid number.")
    return num

def main() -> None:
    print("Please input the question for semantic search.\nTo exit, press Ctrl+C.")
    try:
        query = input()
        num_limit = input_number("Please input the number of results you want to see: ")
        with pg.connect(
                    host="psql-learn-japaneast-hm34mav6hvmci.postgres.database.azure.com",
                    port=5432,
                    dbname="rentals",
                    user="pgAdmin",
                    password=os.environ.get('ADMIN_PASSWORD')
            ) as conn:
            with conn.cursor(row_factory = namedtuple_row) as cur:
                print("Seaching...")
                cur.execute(f"""
                    SELECT id, name FROM listings
                      ORDER BY listing_vector <=>
                      azure_openai.create_embeddings('embedding', '{query}')::vector LIMIT {str(num_limit)};
                    """)
                rows = cur.fetchall()
                if rows is not None:
                    for row in rows:
                        print(f"Listing ID: {row.id}, Name: {row.name}")
                else:
                    print("Maybe something wrong...\nExiting...")
                    sys.exit(1)
    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
