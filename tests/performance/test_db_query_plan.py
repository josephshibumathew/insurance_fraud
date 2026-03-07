from __future__ import annotations


def test_sqlite_explain_plan_uses_index(test_db):
    test_db.execute("CREATE TABLE IF NOT EXISTS claims_perf (id INTEGER PRIMARY KEY, policy_number TEXT, fraud_score REAL)")
    test_db.execute("CREATE INDEX IF NOT EXISTS idx_claims_perf_policy ON claims_perf(policy_number)")
    test_db.execute("INSERT INTO claims_perf (policy_number, fraud_score) VALUES ('P-100', 0.4)")
    test_db.commit()

    rows = test_db.execute("EXPLAIN QUERY PLAN SELECT * FROM claims_perf WHERE policy_number='P-100'").fetchall()
    plan_text = " ".join(str(row) for row in rows).lower()
    assert "index" in plan_text or "idx_claims_perf_policy" in plan_text
