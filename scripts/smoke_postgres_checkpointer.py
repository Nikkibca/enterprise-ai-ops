from langgraph.checkpoint.postgres import PostgresSaver


DATABASE_URL = (
    "postgresql://"
    "app_user:app_password@localhost:5433/"
    "enterprise_ai_ops"
)


with PostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
    config = {
        "configurable": {
            "thread_id": "checkpoint-smoke-test",
        }
    }

    checkpoint = checkpointer.get(config)

    print("Initial checkpoint:", checkpoint)

    print("Postgres checkpointer read OK")
