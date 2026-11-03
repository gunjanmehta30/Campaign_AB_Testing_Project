"""02_load_and_run_sql.py: loads campaign_daily into SQLite, runs every query in sql/campaign_queries.sql,
saves each result to dashboard_data/sql_results/qNN.csv"""
import re, sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB, OUT = ROOT / "campaign.db", ROOT / "dashboard_data" / "sql_results"
OUT.mkdir(parents=True, exist_ok=True)
if DB.exists():
    DB.unlink()
con = sqlite3.connect(DB)
df = pd.read_csv(ROOT / "data" / "processed" / "campaign_daily.csv", parse_dates=["date"])
df["date"] = df["date"].dt.strftime("%Y-%m-%d")
df["is_weekend"] = df["is_weekend"].astype(int)
df["has_missing_metrics"] = df["has_missing_metrics"].astype(int)
df.to_sql("campaign_daily", con, index=False)
print(f"loaded campaign_daily: {len(df)} rows")

sql_text = (ROOT / "sql" / "campaign_queries.sql").read_text()
blocks = re.split(r"(?m)^-- (Q\d+)\.", sql_text)
pd.set_option("display.width", 220); pd.set_option("display.max_columns", 20)
for i in range(1, len(blocks), 2):
    qid, body = blocks[i], blocks[i + 1]
    title = body.split("\n", 1)[0].strip()
    rest = body.split("\n", 1)[1] if "\n" in body else ""
    result = None
    for s in [x.strip() for x in rest.split(";") if x.strip()]:
        code = "\n".join(l for l in s.splitlines() if not l.strip().startswith("--")).strip()
        if not code:
            continue
        if code.upper().startswith(("SELECT", "WITH")):
            result = pd.read_sql_query(code, con)
        else:
            con.executescript(code + ";")
    if result is not None:
        print(f"\n=== {qid}: {title} ===")
        print(result.head(10).to_string(index=False))
        result.to_csv(OUT / f"{qid.lower()}.csv", index=False)
con.close()
