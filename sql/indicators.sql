-- Only records that passed every quality check are used for indicators
CREATE OR REPLACE VIEW learners_valid AS
SELECT *
FROM learners
WHERE passes_quality_checks = 1;

CREATE OR REPLACE VIEW county_indicators AS
SELECT
    county,
    COUNT(*) AS learners_assessed,
    ROUND(AVG(attendance_days_last_week), 2) AS avg_attendance_days,
    ROUND(100.0 * AVG(CASE WHEN attendance_days_last_week = 5 THEN 1 ELSE 0 END), 1) AS pct_full_attendance,
    ROUND(AVG(literacy_score), 1) AS avg_literacy_score
FROM learners_valid
GROUP BY county
ORDER BY county;

CREATE OR REPLACE VIEW sex_indicators AS
SELECT
    county,
    learner_sex,
    COUNT(*) AS learners_assessed,
    ROUND(AVG(attendance_days_last_week), 2) AS avg_attendance_days,
    ROUND(AVG(literacy_score), 1) AS avg_literacy_score
FROM learners_valid
GROUP BY county, learner_sex
ORDER BY county, learner_sex;

CREATE OR REPLACE VIEW absence_reasons_by_county AS
SELECT
    county,
    SUM(absent_illness) AS illness,
    SUM(absent_fees) AS fees,
    SUM(absent_chores) AS chores,
    SUM(absent_distance) AS distance,
    SUM(absent_drought_hunger) AS drought_hunger,
    SUM(absent_other) AS other
FROM learners_valid
GROUP BY county
ORDER BY county;

CREATE OR REPLACE VIEW data_quality_summary AS
SELECT
    issue,
    county,
    COUNT(*) AS records_flagged
FROM data_quality_issues
GROUP BY issue, county
ORDER BY issue, county;