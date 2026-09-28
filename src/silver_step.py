
from datetime import datetime, UTC 
import pandas as pd
import os
import re

bronze_data_dir = "../output/bronze"
silver_output_dir = "../output/silver"

os.makedirs(silver_output_dir, exist_ok=True)

# Read the bronze tables

participants = pd.read_parquet(f"{bronze_data_dir}/bronze_participants.parquet")

device_metadata = pd.read_parquet(f"{bronze_data_dir}/bronze_device_metadata.parquet")

wellness_survey = pd.read_parquet(f"{bronze_data_dir}/bronze_wellness_survey.parquet")

sleep_sessions = pd.read_parquet(f"{bronze_data_dir}/bronze_sleep_sessions.parquet")

sleep_stages = pd.read_parquet(f"{bronze_data_dir}/bronze_sleep_stages.parquet")

steps_events = pd.read_parquet(f"{bronze_data_dir}/bronze_steps_events.parquet")

heart_rate_events = pd.read_parquet(f"{bronze_data_dir}/bronze_heart_rate_events.parquet")

# Validation Functions

def flag_duplicates(df, key_columns):
    """Return duplicate rows based on a primary key."""
    return df[df.duplicated(subset=key_columns, keep=False)]


def flag_invalid_values(df, column, allowed_values):
    """Return rows where a categorical value is invalid."""
    return df[~df[column].isin(allowed_values)]


def flag_out_of_range(df, column, minimum, maximum):
    """Return rows outside the expected numeric range."""
    return df[~df[column].between(minimum, maximum)]


def remove_orphaned_participant_ids(df, valid_participant_ids):
    """Identify and remove rows with participant IDs not present in participants."""
    
    orphaned = df[~df["participant_id"].isin(valid_participant_ids)]
    
    cleaned = df[ df["participant_id"].isin(valid_participant_ids)].copy()
    
    return orphaned, cleaned

# Quality report to flag duplicates and invalid values in the silver tables

quality_report = []

def add_report(table, message):
    quality_report.append(f"[{table}] {message}")
    
# Table 1: silver_participants
# Validate duplicate participants and invalid chronotype values

duplicates = flag_duplicates(participants, ["participant_id"])

if duplicates.empty:
    add_report("silver_participants", "No duplicate participant IDs found.")
else:
    for pid in duplicates["participant_id"].unique():
        add_report("silver_participants", f"Duplicate participant: {pid}")

    participants = participants.drop_duplicates(subset="participant_id", keep="first")

invalid_chronotype = flag_invalid_values( participants,"chronotype",["A", "B"])

if invalid_chronotype.empty:
    add_report("silver_participants", "All chronotypes are valid (A/B).")
else:
    for _, row in invalid_chronotype.iterrows():
        add_report(
            "silver_participants", f"{row['participant_id']} has invalid chronotype '{row['chronotype']}'")

participants.to_parquet(f"{silver_output_dir}/silver_participants.parquet", index=False)

valid_participant_ids = set(participants["participant_id"].dropna().unique())

# Table 2: silver_device_metadata
# Validate duplicate data, invalid participant IDs, check if firmware version was originally blank and fill it 

duplicates = flag_duplicates(device_metadata, ["participant_id"])

if duplicates.empty:
    add_report("silver_device_metadata", "No duplicate participant IDs found.")
else:
    for pid in duplicates["participant_id"].unique():
        add_report("silver_device_metadata", f"Duplicate participant: {pid}")

    device_metadata = device_metadata.drop_duplicates(subset="participant_id", keep="first")

orphaned_ids, device_metadata = remove_orphaned_participant_ids(device_metadata,valid_participant_ids)

if orphaned_ids.empty:
    add_report(
        "silver_device_metadata",
        "No orphaned participant IDs found."
    )
else:
    orphan_ids = orphaned_ids["participant_id"].dropna().unique()

    add_report(
        "silver_device_metadata",
        f"{len(orphan_ids)} orphaned participant IDs found: "
        f"{', '.join(orphan_ids)}"

    )


missing_firmware = device_metadata["firmware_version"].isna()
device_metadata["is_legacy_firmware"] = missing_firmware

n_missing_firmware = missing_firmware.sum()

add_report(
    "silver_device_metadata",
    f"{n_missing_firmware} firmware_version values were originally blank and recovered from device_label."
)

# Fill null firmware_version using device_label
device_metadata.loc[missing_firmware, "firmware_version"] = (
    device_metadata.loc[missing_firmware, "device_label"]
    .str.extract(r"fw([\d.]+)", expand=False)
)

device_metadata.to_parquet(f"{silver_output_dir}/silver_device_metadata.parquet",index=False)

# Table 3: silver_wellness_survey
# Validate duplicate data, invalid participant IDs, and out-of-range values for fatigue, stress, readiness, and sleep quality

duplicates = flag_duplicates( wellness_survey,["participant_id", "date"])

if duplicates.empty:
    add_report("silver_wellness_survey",
        "No duplicate rows found."
    )
else:
    add_report("silver_wellness_survey",
        f"{len(duplicates)} duplicate rows found."
    )

    wellness_survey = wellness_survey.drop_duplicates(
        subset=["participant_id", "date"],
        keep="first"
    )

orphaned_ids, wellness_survey = remove_orphaned_participant_ids(wellness_survey,valid_participant_ids)

if orphaned_ids.empty:
    add_report(
        "silver_wellness_survey",
        "No orphaned participant IDs found."
    )
else:
    orphan_ids = orphaned_ids["participant_id"].dropna().unique()

    add_report(
        "silver_wellness_survey",
        f"{len(orphan_ids)} orphaned participant IDs found: "
        f"{', '.join(orphan_ids)}"
    )

invalid_fatigue_score = flag_out_of_range(wellness_survey, "fatigue_score", 1, 5)

if invalid_fatigue_score.empty:
    add_report(
        "silver_wellness_survey",
        "All fatigue_score values are within [1, 5]."
    )
else:
    add_report(
        "silver_wellness_survey",
        f"{len(invalid_fatigue_score)} fatigue_score values are out of range [1, 5]."
    )

invalid_stress_score = flag_out_of_range(wellness_survey, "stress_score", 1, 5)

if invalid_stress_score.empty:
    add_report(
        "silver_wellness_survey",
        "All stress_score values are within [1, 5]."
    )
else:
    add_report(
        "silver_wellness_survey",
        f"{len(invalid_stress_score)} stress_score values are out of range [1, 5]."
    )

invalid_readiness_score = flag_out_of_range(wellness_survey,"readiness_score", 0, 10)

if invalid_readiness_score.empty:
    add_report(
        "silver_wellness_survey",
        "All readiness_score values are within [0, 10]."
    )
else:
    add_report(
        "silver_wellness_survey",
        f"{len(invalid_readiness_score)} readiness_score values are out of range [0, 10]."
    )

invalid_sleep_quality_score = flag_out_of_range(wellness_survey,"sleep_quality_score", 1, 5)

if invalid_sleep_quality_score.empty:
    add_report(
        "silver_wellness_survey",
        "All sleep_quality_score values are within [1, 5]."
    )
else:
    add_report(
        "silver_wellness_survey",
        f"{len(invalid_sleep_quality_score)} sleep_quality_score values are out of range [1, 5]."
    )

wellness_survey.to_parquet(f"{silver_output_dir}/silver_wellness_survey.parquet", index=False)

# Table 4: silver_sleep_sessions
# Validate duplicate data, invalid participant IDs, check and add clock drift, and recalculate sleep_end

duplicates = flag_duplicates( sleep_sessions,["participant_id", "date"])

if duplicates.empty:
    add_report("silver_sleep_sessions", "No duplicate rows found.")
else:
    add_report("silver_sleep_sessions", f"{len(duplicates)} duplicate rows found.")

    sleep_sessions = sleep_sessions.drop_duplicates(subset=["participant_id", "date"],keep="first")

orphaned_ids, sleep_sessions = remove_orphaned_participant_ids(sleep_sessions,valid_participant_ids)

if orphaned_ids.empty:
    add_report(
        "silver_sleep_sessions",
        "No orphaned participant IDs found."
    )
else:
    orphan_ids = orphaned_ids["participant_id"].dropna().unique()

    add_report(
        "silver_sleep_sessions",
        f"{len(orphan_ids)} orphaned participant IDs found: "
        f"{', '.join(orphan_ids)}"

    )


sleep_sessions["sleep_onset"] = pd.to_datetime (sleep_sessions["sleep_onset"])
sleep_sessions["sleep_end"] = pd.to_datetime(sleep_sessions["sleep_end"])

sleep_duration_original = (sleep_sessions["sleep_end"] - sleep_sessions["sleep_onset"])

sleep_sessions["_clock_drift"] = (sleep_duration_original > pd.Timedelta(hours=12))

add_report(
    "silver_sleep_sessions",
    f"{sleep_sessions['_clock_drift'].sum()} sessions "
    "have sleep duration greater than 12 hours."
)

# Calculate the total duration of each sleep session by summing the durations of 5 consecutive sleep stages. 

sleep_stages["session_number"] = (sleep_stages.groupby("participant_id").cumcount() // 5
)

stage_totals = (
    sleep_stages
    .groupby(["participant_id", "session_number"])["duration_min"]
    .sum()
    .reset_index()
)

sleep_sessions["session_number"] = (
    sleep_sessions.groupby("participant_id").cumcount()
)

sleep_sessions = sleep_sessions.merge(
    stage_totals,
    on=["participant_id", "session_number"],
    how="left"
)

for index, row in sleep_sessions.iterrows():

    if row["_clock_drift"]:

        corrected_sleep_end = (
            row["sleep_onset"] +
            pd.Timedelta(minutes=row["duration_min"])
        )

        add_report(
            "silver_sleep_sessions",
            f"{row['participant_id']} ({row['date']}): "
            f"sleep_end corrected from "
            f"{row['sleep_end']} to {corrected_sleep_end}."
        )

        sleep_sessions.loc[index, "sleep_end"] = corrected_sleep_end

sleep_sessions = sleep_sessions.drop(columns=["session_number", "duration_min"])

sleep_sessions["sleep_onset"] = pd.to_datetime(
    sleep_sessions["sleep_onset"]
)

sleep_sessions["sleep_end"] = pd.to_datetime(
    sleep_sessions["sleep_end"]
)
sleep_sessions.to_parquet(f"{silver_output_dir}/silver_sleep_sessions.parquet", index=False)

# Table 5: silver_sleep_stages
# Validate duplicate data, invalid participant IDs, invalid sleep stages, and recalculate duration_min based on start_time and end_time

duplicates = flag_duplicates( sleep_stages,["participant_id", "start_time"])

if duplicates.empty:
    add_report("silver_sleep_stages", "No duplicate rows found.")
else:
    add_report("silver_sleep_stages", f"{len(duplicates)} duplicate rows found.")

    sleep_stages = sleep_stages.drop_duplicates(subset=["participant_id", "start_times"], keep="first")

orphaned_ids, sleep_stages = remove_orphaned_participant_ids(sleep_stages,valid_participant_ids)

if orphaned_ids.empty:
    add_report(
        "silver_sleep_stages",
        "No orphaned participant IDs found."
    )
else:
    orphan_ids = orphaned_ids["participant_id"].dropna().unique()

    add_report(
        "silver_sleep_stages",
        f"{len(orphan_ids)} orphaned participant IDs found: "
        f"{', '.join(orphan_ids)}"
    )

invalid_stage = flag_invalid_values(sleep_stages,"stage",["light", "deep","rem", "awake"])

if invalid_stage.empty:
    add_report("silver_sleep_stages", "All sleep stages are valid.")
else:
    for _, row in invalid_stage.iterrows():
        add_report(
            "silver_sleep_stages", f"{row['participant_id']} has invalid sleep stage '{row['stage']}'")

sleep_stages["start_time"] = pd.to_datetime(sleep_stages["start_time"])
sleep_stages["end_time"] = pd.to_datetime(sleep_stages["end_time"])

duration_from_timestamps = (sleep_stages["end_time"] - sleep_stages["start_time"]).dt.total_seconds() / 60
duration_from_timestamps = duration_from_timestamps.round().astype(int)

sleep_stages["_duration_corrected"] = (sleep_stages["duration_min"] != duration_from_timestamps)

corrected_durations = sleep_stages[sleep_stages["_duration_corrected"]]
if corrected_durations.empty:
    add_report(
        "silver_sleep_stages",
        "All duration values match the timestamps."
    )
else:
    add_report(
        "silver_sleep_stages",
        f"{len(corrected_durations)} duration values were corrected."
    )
    for _, row in corrected_durations.iterrows():
        add_report(
            "silver_sleep_stages",
            f"{row['participant_id']} at {row['start_time']}: "
            f"duration corrected from {row['duration_min']} "
            f"to {duration_from_timestamps[row.name]} minutes."
        )

sleep_stages.loc[sleep_stages["_duration_corrected"],"duration_min"] = duration_from_timestamps[sleep_stages["_duration_corrected"]]
sleep_stages = sleep_stages.drop(columns=["session_number"])
sleep_stages.to_parquet(f"{silver_output_dir}/silver_sleep_stages.parquet",index=False)

# Table 6: silver_steps_events
# Validate duplicate data, invalid participant IDs, unit errors ate steps, physically impossible values, multi-hour data gaps, and mis-dated first-day timestamps
steps_events = steps_events.drop(columns=["_unit"])
steps_events["timestamp"] = pd.to_datetime(steps_events["timestamp"])


duplicate_mask = steps_events.duplicated(subset=["participant_id", "timestamp"],keep=False)

duplicates = steps_events[duplicate_mask]

if duplicates.empty:
    add_report("silver_steps_events", "No duplicate timestamps found.")
else:
    number_to_remove = steps_events.duplicated(subset=["participant_id", "timestamp"],keep="first").sum()

    add_report(
       "silver_steps_events",
    f"{number_to_remove} duplicate rows found."
    )


orphaned_ids, steps_events = remove_orphaned_participant_ids(steps_events,valid_participant_ids)

if orphaned_ids.empty:
    add_report(
        "silver_steps_events",
        "No orphaned participant IDs found."
    )
else:
    orphan_ids = orphaned_ids["participant_id"].dropna().unique()

    add_report(
        "silver_steps_events",
        f"{len(orphan_ids)} orphaned participant IDs found: "
        f"{', '.join(orphan_ids)}"
    )


# Detect unit errors (steps/hour → steps/minute)
steps_events["_unit_corrected"] = steps_events["steps"] > 120

unit_errors = steps_events[steps_events["_unit_corrected"]]

if unit_errors.empty:
    add_report("silver_steps_events", "No unit errors detected.")
else:
    add_report(
        "silver_steps_events",
        f"{len(unit_errors)} rows had steps/hour unit errors."
    )

# Detect physically impossible values
steps_events["_range_violation"] = (steps_events["steps"] < 0)

range_errors = steps_events[steps_events["_range_violation"]]

if range_errors.empty:
    add_report(
        "silver_steps_events",
        "No physically impossible step values found."
    )
else:
    add_report(
        "silver_steps_events",
        f"{len(range_errors)} rows had physically impossible step values."
    )

# Detect multi-hour data gaps
steps_events = steps_events.sort_values(["participant_id", "timestamp"])

next_time = (
    steps_events.groupby("participant_id")["timestamp"]
    .shift(-1)
)

gap = next_time - steps_events["timestamp"]

steps_events["has_data_gap"] = gap > pd.Timedelta(hours=2)  # assumed "multi-hour" gap as at least 2 hours

gaps = steps_events[steps_events["has_data_gap"]]

if gaps.empty:
    add_report(
        "silver_steps_events",
        "No multi-hour data gaps detected."
    )
else:
    add_report(
        "silver_steps_events",
        f"{len(gaps)} multi-hour data gaps detected."
    )

# Correct unit errors in steps
steps_events.loc[steps_events["_unit_corrected"],"steps"] = (
    steps_events.loc[
        steps_events["_unit_corrected"],
        "steps"
    ] / 60
).round().astype(int)

steps_events.loc[ steps_events["_range_violation"] , "steps" ] = pd.NA

# Correct the first day timestamp (shift back 1 day)

expected_first_day = pd.Timestamp("2026-01-08")
timestamp_corrections = 0

for participant in steps_events["participant_id"].unique():

    participant_data = steps_events[
        steps_events["participant_id"] == participant
    ]

    first_timestamp = participant_data["timestamp"].min()
    first_day = first_timestamp.normalize()

    if first_day == expected_first_day + pd.Timedelta(days=1):

        mask = (
            (steps_events["participant_id"] == participant)
            & (steps_events["timestamp"].dt.normalize() == first_day)
        )

        number_corrected = mask.sum()
        timestamp_corrections += number_corrected

        add_report(
            "silver_steps_events",
            f"{participant}: {number_corrected} timestamps corrected "
            f"from {first_day.date()} to {expected_first_day.date()}."
        )

        steps_events.loc[mask, "timestamp"] = (
            steps_events.loc[mask, "timestamp"]
            - pd.Timedelta(days=1)
        )

if timestamp_corrections == 0:
    add_report(
        "silver_steps_events",
        "No mis-dated first-day timestamps found."
    )


steps_events.to_parquet(f"{silver_output_dir}/silver_steps_events.parquet",index=False)

# Table 7: silver_heart_rate_events

#heart_rate_events["timestamp"] = pd.to_datetime(heart_rate_events["timestamp"])

duplicates = flag_duplicates(heart_rate_events,["participant_id", "timestamp"])

if duplicates.empty: add_report(
        "silver_heart_rate_events",
        "No duplicate rows found."
    )
else:
    number_to_remove = heart_rate_events.duplicated(
        subset=["participant_id", "timestamp"],
        keep="first"
    ).sum()

    add_report(
        "silver_heart_rate_events",
        f"{number_to_remove} duplicate rows found."
    )

    heart_rate_events = heart_rate_events.drop_duplicates(subset=["participant_id", "timestamp"], keep="first")

orphaned_ids, heart_rate_events = remove_orphaned_participant_ids(heart_rate_events, valid_participant_ids)

if orphaned_ids.empty:
    add_report(
        "silver_heart_rate_events",
        "No orphaned participant IDs found."
    )
else:
    orphan_ids = orphaned_ids["participant_id"].dropna().unique()

    add_report(
        "silver_heart_rate_events",
        f"{len(orphan_ids)} orphaned participant IDs found: "
        f"{', '.join(orphan_ids)}"
    )

# Detect timestamps explicitly written as UTC
utc_mask = heart_rate_events["timestamp"].astype(str).str.endswith("Z")

heart_rate_events["_format_corrected"] = utc_mask

number_utc = utc_mask.sum()

if number_utc == 0:
    add_report(
        "silver_heart_rate_events",
        "No UTC timestamps found."
    )
else:
    add_report(
        "silver_heart_rate_events",
        f"{number_utc} UTC timestamps converted to local time."
    )

# Detect out-of-range heart rate values

invalid_heart_rate = flag_out_of_range( heart_rate_events, "heart_rate_bpm", 40, 200)

if invalid_heart_rate.empty:
    add_report(
        "silver_heart_rate_events",
        "All heart-rate values are within the valid range."
    )
else:
    add_report(
        "silver_heart_rate_events",
        f"{len(invalid_heart_rate)} heart-rate values are outside the valid range."
    )

heart_rate_events["_range_violation"] = (heart_rate_events["heart_rate_bpm"].index.isin(invalid_heart_rate.index))

heart_rate_events = heart_rate_events.sort_values(
    ["participant_id", "timestamp"]
)

flatline_minutes = 60

# Detect flatlines in heart rate data (consecutive identical values for at least 60 minutes)
heart_rate_events["_hr_group"] = (
    heart_rate_events.groupby("participant_id")["heart_rate_bpm"]
    .transform(lambda x: x.ne(x.shift()).cumsum())
)

heart_rate_events["_hr_run_length"] = (
    heart_rate_events
    .groupby(["participant_id", "_hr_group"])["heart_rate_bpm"]
    .transform("size")
)

heart_rate_events["_flatline"] = (
    heart_rate_events["heart_rate_bpm"].notna()
    & (heart_rate_events["_hr_run_length"] >= flatline_minutes)
)

flatline_values = heart_rate_events[heart_rate_events["_flatline"]]

if flatline_values.empty:
    add_report(
        "silver_heart_rate_events",
        "No long heart-rate flatlines found."
    )
else:
    add_report(
        "silver_heart_rate_events",
        f"{len(flatline_values)} heart-rate values identified as stuck-sensor flatlines."
    )

# Normalize timestamps to naive local time where utc was detected

heart_rate_events.loc[~utc_mask, "timestamp"] = pd.to_datetime(
    heart_rate_events.loc[~utc_mask, "timestamp"]
)

heart_rate_events.loc[utc_mask, "timestamp"] = (
    pd.to_datetime(
        heart_rate_events.loc[utc_mask, "timestamp"],
        utc=True
    )
    .dt.tz_convert("Etc/GMT+5")
    .dt.tz_localize(None)
)

heart_rate_events["timestamp"] = pd.to_datetime(heart_rate_events["timestamp"])

# Edit heart_rate_bpm to nulled where out of range or part of a stuck-sensor run
heart_rate_events.loc[heart_rate_events["_range_violation"],"heart_rate_bpm"] = pd.NA
heart_rate_events.loc[heart_rate_events["_flatline"],"heart_rate_bpm"] = pd.NA

heart_rate_events = heart_rate_events.drop(columns=["_hr_group", "_hr_run_length"])

heart_rate_events.to_parquet(f"{silver_output_dir}/silver_heart_rate_events.parquet",index=False)

# Save quality report 

with open(f"{silver_output_dir}/silver_data_quality_report.txt", "w") as f:

    f.write("SILVER DATA QUALITY REPORT\n")
    f.write("=" * 50 + "\n\n")

    tables = [
        "silver_participants",
        "silver_device_metadata",
        "silver_wellness_survey",
        "silver_sleep_sessions",
        "silver_sleep_stages",
        "silver_steps_events",
        "silver_heart_rate_events"
    ]

    for table in tables:
        f.write(f"{table.upper()}\n")

        for line in quality_report:
            if line.startswith(f"[{table}]"):
                message = line.replace(f"[{table}] ", "")
                f.write(f"• {message}\n")

        f.write("\n")