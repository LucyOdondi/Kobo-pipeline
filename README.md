# Kobo Learner Survey Pipeline

An automated Python pipeline for NGO monitoring and evaluation (M&E) data. It pulls learner attendance and literacy survey submissions from the KoboToolbox API, cleans and standardises the data, and flags quality problems such as duplicate records, conflicting learner IDs, implausible ages, missing GPS, and suspiciously fast interviews. The cleaned output feeds a Power BI dashboard that tracks programme reach and outcomes by county.

All data is synthetic. No real learners or beneficiaries are included.
