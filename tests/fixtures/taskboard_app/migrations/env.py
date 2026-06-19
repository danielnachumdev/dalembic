import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

SCHEMA = os.environ.get("DB_SCHEMA", "public")


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
        connection.execute(text(f"SET search_path TO {SCHEMA}"))
        connection.commit()
        context.configure(
            connection=connection,
            version_table="alembic_version",
            version_table_schema=SCHEMA,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
