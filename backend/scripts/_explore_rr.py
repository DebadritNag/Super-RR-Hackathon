import duckdb
import sys

c = duckdb.connect("data/database/superr.duckdb", read_only=True)
e = duckdb.connect("data/database/exploratory.duckdb", read_only=True)
for q in sys.argv[1:]:
    x = e if q.startswith("E:") else c
    q = q[2:] if q.startswith("E:") else q
    print(">>", q)
    print(x.execute(q).fetchdf().to_string())
