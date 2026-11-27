from pathlib import Path
from sqlmodel import SQLModel, Field, create_engine
from database import models
from sqlalchemy import event, inspect


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "app.db"

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

def create_db_and_tables():
    with engine.begin() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        SQLModel.metadata.create_all(connection)
        columns = {column["name"] for column in inspect(connection).get_columns("profiles")}
        if "weight_reminder_days" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE profiles ADD COLUMN weight_reminder_days INTEGER NOT NULL "
                f"DEFAULT {models.DEFAULT_WEIGHT_REMINDER_DAYS}"
            )
        if "training_assessment" not in columns:
            connection.exec_driver_sql("ALTER TABLE profiles ADD COLUMN training_assessment JSON")

if __name__ == "__main__":
    create_db_and_tables()
    print("База данных и таблицы созданы.")
