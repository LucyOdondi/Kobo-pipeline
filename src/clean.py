import json
from pathlib import Path

import pandas as pd

raw_file_path = Path("data/raw/submissions_raw.json")
clean_folder = Path("data/clean")
clean_folder.mkdir(parents=True, exist_ok=True)

# Thresholds for the quality checks (adjust as the project grows)
MIN_LEARNER_AGE = 4
MAX_LEARNER_AGE = 17
FAST_INTERVIEW_SHARE_OF_MEDIAN = 0.4
MIN_RECORDS_FOR_STRAIGHT_LINING_CHECK = 3

county_labels = {
    "turkana": "Turkana",
    "kilifi": "Kilifi",
    "nairobi": "Nairobi City",
    "kisumu": "Kisumu",
    "garissa": "Garissa",
}
code_prefix_to_county = {
    "TUR": "Turkana",
    "KIL": "Kilifi",
    "NAI": "Nairobi City",
    "KIS": "Kisumu",
    "GAR": "Garissa",
}
grade_level_labels = {
    "pp1_pp2": "PP1 to PP2",
    "grade_1_3": "Grade 1 to 3",
    "grade_4_6": "Grade 4 to 6",
    "grade_7_9": "Grade 7 to 9",
}
absence_reason_codes = ["illness", "fees", "chores", "distance", "drought_hunger", "other"]

column_renames = {
    "_id": "submission_id",
    "_uuid": "submission_uuid",
    "_submission_time": "submission_time",
    "start": "start",
    "end": "end",
    "consent": "consent",
    "survey_info/enumerator_id": "enumerator_id",
    "survey_info/interview_date": "interview_date",
    "survey_info/county": "county",
    "survey_info/residence_type": "residence_type",
    "survey_info/school_name": "school_name",
    "_geolocation": "geolocation",
    "learner_info/learner_code": "learner_code",
    "learner_info/learner_age": "learner_age",
    "learner_info/learner_sex": "learner_sex",
    "learner_info/grade_level": "grade_level",
    "learner_info/attendance_days_last_week": "attendance_days_last_week",
    "learner_info/absence_reasons": "absence_reasons",
    "learner_info/literacy_score": "literacy_score",
}


def load_raw_submissions():
    with open(raw_file_path, encoding="utf-8") as raw_file:
        submissions_list = json.load(raw_file)
    return pd.DataFrame(submissions_list)


def select_and_rename_columns(raw_dataframe):
    # reindex keeps the script working even if a column is missing in every record
    return raw_dataframe.reindex(columns=list(column_renames)).rename(columns=column_renames)


def split_geolocation(geolocation_value):
    if isinstance(geolocation_value, list) and len(geolocation_value) == 2:
        return pd.Series(geolocation_value, index=["latitude", "longitude"])
    return pd.Series([None, None], index=["latitude", "longitude"])


def convert_data_types_and_labels(learners_dataframe):
    gps_dataframe = learners_dataframe["geolocation"].apply(split_geolocation)
    learners_dataframe["latitude"] = pd.to_numeric(gps_dataframe["latitude"], errors="coerce")
    learners_dataframe["longitude"] = pd.to_numeric(gps_dataframe["longitude"], errors="coerce")
    learners_dataframe = learners_dataframe.drop(columns="geolocation")

    for time_column in ["start", "end", "submission_time"]:
        learners_dataframe[time_column] = (
            pd.to_datetime(learners_dataframe[time_column], utc=True)
            .dt.tz_convert("Africa/Nairobi")
            .dt.tz_localize(None)
        )
    learners_dataframe["interview_date"] = pd.to_datetime(learners_dataframe["interview_date"])

    for numeric_column in ["learner_age", "attendance_days_last_week", "literacy_score"]:
        learners_dataframe[numeric_column] = pd.to_numeric(learners_dataframe[numeric_column], errors="coerce")

    learners_dataframe["county_code"] = learners_dataframe["county"]
    learners_dataframe["county"] = learners_dataframe["county"].map(county_labels)
    learners_dataframe["grade_level"] = learners_dataframe["grade_level"].map(grade_level_labels)
    learners_dataframe["learner_sex"] = learners_dataframe["learner_sex"].str.title()
    learners_dataframe["residence_type"] = learners_dataframe["residence_type"].str.title()

    learners_dataframe["absence_reasons"] = learners_dataframe["absence_reasons"].fillna("")
    absence_reason_lists = learners_dataframe["absence_reasons"].str.split()
    for reason_code in absence_reason_codes:
        learners_dataframe[f"absent_{reason_code}"] = absence_reason_lists.apply(
            lambda reasons: int(reason_code in reasons)
        )
    learners_dataframe["absence_reason_count"] = absence_reason_lists.str.len()

    learners_dataframe["interview_minutes"] = (
        (learners_dataframe["end"] - learners_dataframe["start"]).dt.total_seconds() / 60
    ).round(1)
    learners_dataframe["learner_code"] = (
    learners_dataframe["learner_code"].str.replace(r"\s+", "", regex=True).str.upper()
)
    return learners_dataframe


def add_quality_flags(learners_dataframe):
    duplicate_check_columns = [
        "enumerator_id", "interview_date", "county", "school_name", "learner_code", "learner_age",
        "learner_sex", "grade_level", "attendance_days_last_week", "absence_reasons", "literacy_score",
    ]
    learners_dataframe["flag_exact_duplicate"] = learners_dataframe.duplicated(
        subset=duplicate_check_columns, keep="first"
    )

    not_duplicate = ~learners_dataframe["flag_exact_duplicate"]
    code_counts = learners_dataframe.loc[not_duplicate, "learner_code"].value_counts()
    conflicting_codes = code_counts[code_counts > 1].index
    learners_dataframe["flag_learner_code_conflict"] = (
        learners_dataframe["learner_code"].isin(conflicting_codes) & not_duplicate
    )

    learners_dataframe["flag_missing_gps"] = learners_dataframe["latitude"].isna()
    learners_dataframe["flag_code_county_mismatch"] = (
    learners_dataframe["learner_code"].str[:3].map(code_prefix_to_county)
    != learners_dataframe["county"]
)

    learners_dataframe["flag_implausible_age"] = ~learners_dataframe["learner_age"].between(
        MIN_LEARNER_AGE, MAX_LEARNER_AGE
    )

    median_interview_minutes = learners_dataframe["interview_minutes"].median()
    learners_dataframe["flag_fast_interview"] = (
        learners_dataframe["interview_minutes"] < median_interview_minutes * FAST_INTERVIEW_SHARE_OF_MEDIAN
    )

    enumerator_groups = learners_dataframe.groupby("enumerator_id")
    records_per_enumerator = enumerator_groups["submission_id"].transform("count")
    distinct_attendance_values = enumerator_groups["attendance_days_last_week"].transform("nunique")
    distinct_literacy_values = enumerator_groups["literacy_score"].transform("nunique")
    learners_dataframe["flag_straight_lining"] = (
        (records_per_enumerator >= MIN_RECORDS_FOR_STRAIGHT_LINING_CHECK)
        & (distinct_attendance_values == 1)
        & (distinct_literacy_values == 1)
    )

    flag_columns = [column for column in learners_dataframe.columns if column.startswith("flag_")]
    learners_dataframe["quality_issue_count"] = learners_dataframe[flag_columns].sum(axis=1)
    learners_dataframe["passes_quality_checks"] = learners_dataframe["quality_issue_count"] == 0
    return learners_dataframe, flag_columns


def build_issue_log(learners_dataframe, flag_columns):
    issue_tables = []
    for flag_column in flag_columns:
        flagged_records = learners_dataframe.loc[
            learners_dataframe[flag_column],
            ["submission_id", "learner_code", "enumerator_id", "county"],
        ].copy()
        flagged_records["issue"] = flag_column.replace("flag_", "")
        issue_tables.append(flagged_records)
    return pd.concat(issue_tables, ignore_index=True)


if __name__ == "__main__":
    raw_dataframe = load_raw_submissions()
    renamed_dataframe = select_and_rename_columns(raw_dataframe)
    typed_dataframe = convert_data_types_and_labels(renamed_dataframe)

    refusal_count = int((typed_dataframe["consent"] == "no").sum())
    consented_learners = typed_dataframe[typed_dataframe["consent"] == "yes"].copy()

    flagged_learners, flag_columns = add_quality_flags(consented_learners)
    issue_log = build_issue_log(flagged_learners, flag_columns)

    learners_for_analysis = flagged_learners[~flagged_learners["flag_exact_duplicate"]]
    learners_for_analysis.to_csv(clean_folder / "learners_clean.csv", index=False)
    issue_log.to_csv(clean_folder / "data_quality_issues.csv", index=False)

    print(f"Raw submissions: {len(raw_dataframe)}")
    print(f"Consent refusals removed: {refusal_count}")
    print(f"Exact duplicates removed: {int(flagged_learners['flag_exact_duplicate'].sum())}")
    print(f"Records saved to learners_clean.csv: {len(learners_for_analysis)}")
    print()
    print("Quality issues found:")
    print(flagged_learners[flag_columns].sum().to_string())