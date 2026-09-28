from datetime import datetime, UTC 
import pandas as pd
import os
import re

silver_data_dir = "../output/silver"
gold_output_dir = "../output/gold"

os.makedirs(gold_output_dir, exist_ok=True)

# Read the silver tables

silver_participants = pd.read_parquet(f"{silver_data_dir}/silver_participants.parquet")

silver_device_metadata = pd.read_parquet(f"{silver_data_dir}/silver_device_metadata.parquet")

silver_wellness_survey = pd.read_parquet(f"{silver_data_dir}/silver_wellness_survey.parquet")

silver_sleep_sessions = pd.read_parquet(f"{silver_data_dir}/silver_sleep_sessions.parquet")

silver_sleep_stages = pd.read_parquet(f"{silver_data_dir}/silver_sleep_stages.parquet")

silver_steps_events = pd.read_parquet(f"{silver_data_dir}/silver_steps_events.parquet")

silver_heart_rate_events = pd.read_parquet(f"{silver_data_dir}/silver_heart_rate_events.parquet")

# Table 1: gold_daily_activity

participants = silver_participants[["participant_id","chronotype"]]

dates = pd.DataFrame({"date": pd.date_range(start="2026-01-08",end="2026-02-04",freq="D")})

gold_daily_activity = (participants.merge(dates, how="cross"))

gold_daily_activity["chronotype_label"] = (
    gold_daily_activity["chronotype"]
    .map({
        "A": "morning",
        "B": "evening"
    })
)

# Calculate total steps and steps_7d_avg

steps = silver_steps_events.copy()
steps["date"] = steps["timestamp"].dt.normalize()

# Sum the steps for each participant and each day

daily_steps = (steps.groupby(["participant_id", "date"])["steps"].sum().reset_index())
daily_steps = daily_steps.rename(columns={"steps": "total_steps"})

gold_daily_activity = gold_daily_activity.merge(daily_steps,on=["participant_id", "date"],how="left")

gold_daily_activity = gold_daily_activity.sort_values(["participant_id", "date"])

gold_daily_activity["steps_7d_avg"] = (
    gold_daily_activity
    .groupby("participant_id")["total_steps"]
    .rolling(7, min_periods=1)
    .mean()
    .reset_index(level=0, drop=True)
)

# Calculate total_sleep_

sleep_duration = silver_sleep_stages[silver_sleep_stages["stage"] != "awake"].copy()

sleep_duration["date"] = pd.to_datetime(sleep_duration["date"])

sleep_duration = (
    sleep_duration
    .groupby(["participant_id", "date"])["duration_min"]
    .sum()
    .reset_index()
    .rename(columns={"duration_min": "total_sleep_min"})
)

gold_daily_activity = gold_daily_activity.merge(
    sleep_duration,
    on=["participant_id", "date"],
    how="left"
)

# Add sleep efficiency 
silver_sleep_sessions["date"] = pd.to_datetime(silver_sleep_sessions["date"])

sleep_efficiency = silver_sleep_sessions[
    ["participant_id", "date", "efficiency_pct"]
].rename(columns={
    "efficiency_pct": "sleep_efficiency_pct"
})

gold_daily_activity = gold_daily_activity.merge(
    sleep_efficiency,
    on=["participant_id", "date"],
    how="left"
)

# Calculate deep sleep %

deep_sleep = silver_sleep_stages[silver_sleep_stages["stage"] == "deep"].copy()
deep_sleep["date"] = pd.to_datetime(deep_sleep["date"])

deep_sleep = (
    deep_sleep
    .groupby(["participant_id", "date"])["duration_min"]
    .sum()
    .reset_index()
    .rename(columns={"duration_min": "deep_sleep_min"})
)

gold_daily_activity = gold_daily_activity.merge(
    deep_sleep,
    on=["participant_id", "date"],
    how="left"
)

gold_daily_activity["deep_sleep_pct"] = (
    gold_daily_activity["deep_sleep_min"] /
    gold_daily_activity["total_sleep_min"] * 100
)

gold_daily_activity = gold_daily_activity.drop(columns=["deep_sleep_min"])

# Calculate avg heart rate

heart_rate = silver_heart_rate_events.copy()

heart_rate["date"] = heart_rate["timestamp"].dt.normalize()

heart_rate = (
    heart_rate
    .groupby(["participant_id", "date"])["heart_rate_bpm"]
    .mean()
    .reset_index()
    .rename(columns={"heart_rate_bpm": "avg_heart_rate_bpm"})
)

gold_daily_activity = gold_daily_activity.merge(
    heart_rate,
    on=["participant_id", "date"],
    how="left"
)

# Add fatigue, stress, readiness and sleep quality scores from wellness survey

silver_wellness_survey["date"] = pd.to_datetime(silver_wellness_survey["date"])
wellness_data = silver_wellness_survey[
    [
        "participant_id",
        "date",
        "fatigue_score",
        "stress_score",
        "readiness_score",
        "sleep_quality_score"
    ]
]

gold_daily_activity = gold_daily_activity.merge(wellness_data,on=["participant_id", "date"],how="left")

gold_daily_activity["wellness_composite"] = (
    gold_daily_activity["fatigue_score"] +
    gold_daily_activity["stress_score"] +
    gold_daily_activity["readiness_score"] +
    gold_daily_activity["sleep_quality_score"]
) / 4

gold_daily_activity = gold_daily_activity[
    [
        "participant_id",
        "date",
        "chronotype",
        "chronotype_label",
        "total_steps",
        "steps_7d_avg",
        "total_sleep_min",
        "sleep_efficiency_pct",
        "deep_sleep_pct",
        "avg_heart_rate_bpm",
        "fatigue_score",
        "stress_score",
        "readiness_score",
        "sleep_quality_score",
        "wellness_composite"
    ]
]

gold_daily_activity.to_parquet(f"{gold_output_dir}/gold_daily_activity.parquet", index=False)

# Flag missing values in gold_daily_activity

missing_rows = []

for column in gold_daily_activity.columns:
    missing_mask = gold_daily_activity[column].isna()

    for _, row in gold_daily_activity.loc[missing_mask].iterrows():
        missing_rows.append({
            "participant_id": row["participant_id"],
            "date": row["date"],
            "column": column
        })

missing_report = pd.DataFrame(missing_rows)
print(f"Missing values report:\n{missing_report}")

# Table 2: gold_participant_profile

gold_participant_profile = silver_participants[
    [
        "participant_id",
        "age",
        "gender",
        "chronotype",
        "max_heart_rate"
    ]
].copy()

gold_participant_profile["chronotype_label"] = (
    gold_participant_profile["chronotype"]
    .map({
        "A": "morning",
        "B": "evening"
    })
)

firmware = silver_device_metadata[ ["participant_id","is_legacy_firmware"]]

gold_participant_profile = gold_participant_profile.merge(
    firmware,
    on="participant_id",
    how="left"
)

# Calculate participant averages from gold_daily_activity

participant_averages = (
    gold_daily_activity
    .groupby("participant_id")
    .agg(
        avg_daily_steps=("total_steps", "mean"),
        avg_total_sleep_min=("total_sleep_min", "mean"),
        avg_sleep_efficiency_pct=("sleep_efficiency_pct", "mean"),
        avg_deep_sleep_pct=("deep_sleep_pct", "mean"),
        avg_heart_rate_bpm=("avg_heart_rate_bpm", "mean"),
        avg_wellness_composite=("wellness_composite", "mean")
    )
    .reset_index()
)

gold_participant_profile = gold_participant_profile.merge(
    participant_averages,
    on="participant_id",
    how="left"
)

# Count days with data gap

data_gaps = silver_steps_events.copy()

data_gaps["date"] = data_gaps["timestamp"].dt.normalize()

data_gaps = data_gaps[data_gaps["has_data_gap"] == True]

data_gaps = (
    data_gaps
    .groupby("participant_id")["date"]
    .nunique()
    .reset_index()
    .rename(columns={"date": "n_days_with_data_gap"})
)

gold_participant_profile = gold_participant_profile.merge(
    data_gaps,
    on="participant_id",
    how="left"
)

# Participants with no gaps should have 0
gold_participant_profile["n_days_with_data_gap"] = (
    gold_participant_profile["n_days_with_data_gap"]
    .fillna(0)
    .astype(int)
)

gold_participant_profile = gold_participant_profile[
    [
        "participant_id",
        "age",
        "gender",
        "chronotype",
        "chronotype_label",
        "max_heart_rate",
        "is_legacy_firmware", 
        "avg_daily_steps",
        "avg_total_sleep_min",
        "avg_sleep_efficiency_pct",
        "avg_deep_sleep_pct",
        "avg_heart_rate_bpm",
        "avg_wellness_composite",
        "n_days_with_data_gap"
    ]
]

gold_participant_profile.to_parquet(f"{gold_output_dir}/gold_participant_profile.parquet", index=False)

# Table 3: gold_cohort_comparison

gold_cohort_comparison = (
    gold_participant_profile
    .groupby(["chronotype", "chronotype_label"])
    .agg(
        n_participants=("participant_id", "count"),
        avg_daily_steps=("avg_daily_steps", "mean"),
        avg_total_sleep_min=("avg_total_sleep_min", "mean"),
        avg_sleep_efficiency_pct=("avg_sleep_efficiency_pct", "mean"),
        avg_deep_sleep_pct=("avg_deep_sleep_pct", "mean"),
        avg_heart_rate_bpm=("avg_heart_rate_bpm", "mean"),
        avg_wellness_composite=("avg_wellness_composite", "mean")
    )
    .reset_index()
)


gold_cohort_comparison.to_parquet( f"{gold_output_dir}/gold_cohort_comparison.parquet",index=False)
