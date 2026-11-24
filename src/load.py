import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

clean_folder = Path("data/clean")
powerbi_folder = Path("data/powerbi")
indicators_sql_path = Path("sql/indicators.sql")
powerbi_folder.mkdir(parents=True, exist_ok=True)

connection_url = URL.create(
    "mysql+pymysql",
    username=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    database=os.getenv("MYSQL_DATABASE", "kobo_pipeline"),
)
database_engine = create_engine(connection_url)

views_to_export = [
    "county_indicators",
    "sex_indicators",
    "absence_reasons_by_county",
    "data_quality_summary",
]

learners_dataframe = pd.read_csv(
    clean_folder / "learners_clean.csv",
    parse_dates=["start", "end", "submission_time", "interview_date"],
)
issues_dataframe = pd.read_csv(clean_folder / "data_quality_issues.csv")

learners_dataframe.to_sql("learners", database_engine, if_exists="replace", index=False)
issues_dataframe.to_sql("data_quality_issues", database_engine, if_exists="replace", index=False)

indicator_sql_text = indicators_sql_path.read_text(encoding="utf-8")
sql_statements = [statement.strip() for statement in indicator_sql_text.split(";") if statement.strip()]

with database_engine.begin() as database_connection:
    for sql_statement in sql_statements:
        database_connection.execute(text(sql_statement))

for view_name in views_to_export:
    view_dataframe = pd.read_sql(text(f"SELECT * FROM {view_name}"), database_engine)
    view_dataframe.to_csv(powerbi_folder / f"{view_name}.csv", index=False)

learner_count = pd.read_sql(text("SELECT COUNT(*) AS n FROM learners"), database_engine)["n"][0]
valid_count = pd.read_sql(text("SELECT COUNT(*) AS n FROM learners_valid"), database_engine)["n"][0]

print(f"Learners loaded: {learner_count}")
print(f"Learners passing all quality checks: {valid_count}")
print()
print(pd.read_sql(text("SELECT * FROM county_indicators"), database_engine).to_string(index=False))