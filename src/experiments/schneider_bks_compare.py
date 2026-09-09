"""Compare our constructive E-VRPTW baseline to Schneider (2014) best-known solutions.

BKS values are Schneider et al. (2014) published best-known solutions, taken from
open secondary sources (we could not access the original paper PDF):
  - C5 small instances (5 customers): from jmanzolli/E-VRPTW, which reports the
    Schneider et al. (2014) CPLEX results directly.
  - _21 large instances (100 customers): from Adachi et al. (2022, IEICE NOLTA),
    which cites Schneider (2014) for the BKS table.
"""
import csv, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "results", "schneider_evrptw_baseline.csv")
OUT = os.path.join(HERE, "..", "results", "schneider_evrptw_bks_comparison.csv")

BKS = {
    # C5 small (5 customers) — jmanzolli/E-VRPTW reporting Schneider (2014)
    "c101C5": (2, 257.75), "c103C5": (1, 176.05), "c206C5": (1, 242.55),
    "c208C5": (1, 158.48), "r104C5": (2, 136.69), "r105C5": (2, 156.08),
    "r202C5": (1, 128.78), "r203C5": (1, 179.06), "rc105C5": (2, 241.30),
    "rc108C5": (1, 253.92), "rc204C5": (1, 176.39), "rc208C5": (1, 167.98),
    # _21 large (100 customers) — Adachi et al. (2022) citing Schneider (2014)
    "c201_21": (4, 629.95), "c206_21": (4, 629.95), "r201_21": (3, 1258.40),
    "r206_21": (3, 929.39), "rc201_21": (4, 1446.60), "rc206_21": (3, 1207.98),
}
SRC = {k: "jmanzolli/E-VRPTW (Schneider 2014)" for k in
       ["c101C5", "c103C5", "c206C5", "c208C5", "r104C5", "r105C5",
        "r202C5", "r203C5", "rc105C5", "rc108C5", "rc204C5", "rc208C5"]}
SRC.update({k: "Adachi et al. (2022, IEICE), cit. Schneider (2014)" for k in
            ["c201_21", "c206_21", "r201_21", "r206_21", "rc201_21", "rc206_21"]})

rows = []
with open(BASE) as f:
    for row in csv.DictReader(f):
        name = row["instance"]
        if name not in BKS:
            continue
        my_v = int(row["vehicles"]); my_d = float(row["total_distance"])
        uns = int(row["unserved"])
        bk_v, bk_d = BKS[name]
        dgap = 100 * (my_d - bk_d) / bk_d
        rows.append([name, row["n_customers"], row["n_stations"], my_v,
                     round(my_d, 2), bk_v, bk_d, round(dgap, 1),
                     my_v - bk_v, uns, SRC[name]])

with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["instance", "n_customers", "n_stations", "my_vehicles",
                "my_distance", "bks_vehicles", "bks_distance", "dist_gap_pct",
                "vehicle_gap", "unserved", "bks_source"])
    w.writerows(rows)

served = [r for r in rows if r[9] == 0]
print(f"wrote {OUT} ({len(rows)} rows; fully served {len(served)}/{len(rows)})")
if served:
    gaps = [r[7] for r in served]
    print(f"mean |dist gap| % (fully served): {round(statistics.mean(abs(g) for g in gaps),1)}")
    print(f"mean  dist gap % (fully served): {round(statistics.mean(gaps),1)}")
for r in rows:
    print(f"{r[0]:10s} my({r[3]:2d},{r[4]:7.1f}) bks({r[5]},{r[6]:7.1f}) "
          f"dgap={r[7]:+5.1f}% vgap={r[8]:+d} uns={r[9]}")
