from agent import db, shift_store
import agent.config as config
config.DATABASE_PATH = "test_debug.db"
db.init_db(config.DATABASE_PATH)
shift_store.create_operator("OP_JOHN", "John Doe", role="operator", active=1)
op = shift_store.find_operator_by_name("John Doe", active_only=True)
print("op found:", op)
