import time
from agent import db, shift_store

db.init_db()

# Create a test operator
try:
    shift_store.create_operator("op_test", "Real Worker")
except Exception:
    pass

record = shift_store.create_attendance_record("op_test", "Real Worker", "2026-10-08")
print(f"Created: {record}")

import sqlite3
conn = sqlite3.connect("kelvin6k.db")
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM attendance_records WHERE operator_id = 'op_test'").fetchone()
print("\nDB ROW:")
for k in row.keys():
    print(f"{k}: {row[k]}")

# checkout
shift_store.checkout_attendance_record("op_test")
row_checkout = conn.execute("SELECT * FROM attendance_records WHERE operator_id = 'op_test'").fetchone()
print("\nDB ROW AFTER CHECKOUT:")
for k in row_checkout.keys():
    print(f"{k}: {row_checkout[k]}")
