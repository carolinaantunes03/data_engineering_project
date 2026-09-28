from pathlib import Path
from datetime import datetime, UTC 
import json
import pandas as pd
import os


bronze_output_dir = "../output/bronze"

os.makedirs(bronze_output_dir, exist_ok=True)

# create one ingestion timestamp
ingestion_time = datetime.now(UTC)

# create tables with the source file + timestamp

# Table 1: bronze_participants
participants = pd.read_csv("../data/participants/participants.csv")
participants["_source_file"] = "participants/participants.csv"
participants["_ingested_at"] = ingestion_time

participants.to_parquet(f"{bronze_output_dir}/bronze_participants.parquet", index=False)

# Table 2: bronze_device_metadata
device_metadata = pd.read_csv("../data/health_summaries/device_metadata.csv")
device_metadata["_source_file"] = "health_summaries/device_metadata.csv"
device_metadata["_ingested_at"] = ingestion_time

device_metadata.to_parquet(f"{bronze_output_dir}/bronze_device_metadata.parquet", index=False)

# Table 3: bronze_wellness_survey
wellness_survey = pd.read_csv("../data/health_summaries/wellness_survey.csv")
wellness_survey["_source_file"] = "health_summaries/wellness_survey.csv"
wellness_survey["_ingested_at"] = ingestion_time

wellness_survey.to_parquet(f"{bronze_output_dir}/bronze_wellness_survey.parquet", index=False)

wearable_events_dir = "../data/wearable_events"

# Table 4 and 5: bronze_sleep_sessions and bronze_sleep_stages
sleep_sessions_list = []
sleep_stages_list = []

for participant in sorted(os.listdir(wearable_events_dir)):
    file_path = os.path.join(wearable_events_dir, participant, "sleep.json")

    if os.path.exists(file_path):

        with open(file_path, "r") as f:
            nights = json.load(f)

        for night in nights:
        
            sleep_sessions_list.append({
                "participant_id": night["participant_id"],
                "date": night["date"],
                "sleep_onset": night["sleep_onset"],
                "sleep_end": night["sleep_end"],
                "efficiency_pct": night["efficiency_pct"],
                "restlessness": night["restlessness"],
                "_source_file": f"wearable_events/{participant}/sleep.json",
                "_ingested_at": ingestion_time
            })

            for stage in night["stages"]:

                sleep_stages_list.append({
                    "participant_id": night["participant_id"],
                    "date": night["date"],
                    "stage": stage["stage"],
                    "start_time": stage["start_time"],
                    "end_time": stage["end_time"],
                    "duration_min": stage["duration_min"],
                    "_source_file": f"wearable_events/{participant}/sleep.json",
                    "_ingested_at": ingestion_time
                })

bronze_sleep_sessions = pd.DataFrame(sleep_sessions_list)
bronze_sleep_stages = pd.DataFrame(sleep_stages_list)

bronze_sleep_sessions.to_parquet(
    f"{bronze_output_dir}/bronze_sleep_sessions.parquet",
    index=False
)

bronze_sleep_stages.to_parquet(
    f"{bronze_output_dir}/bronze_sleep_stages.parquet",
    index=False
)


# Table 6: bronze_steps_events
steps_list = []

for participant in sorted(os.listdir(wearable_events_dir)):

    file_path = os.path.join(wearable_events_dir, participant, "steps.json")
    if os.path.exists(file_path):

        with open(file_path, "r") as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        df["_source_file"] = f"wearable_events/{participant}/steps.json"
        df["_ingested_at"] = ingestion_time

        steps_list.append(df)

bronze_steps = pd.concat(steps_list, ignore_index=True)
bronze_steps.to_parquet(f"{bronze_output_dir}/bronze_steps_events.parquet", index=False)

# Table 7: bronze_heart_rate_events

heart_rate_list = []

for participant in sorted(os.listdir(wearable_events_dir)):

    file_path = os.path.join(wearable_events_dir, participant, "heart_rate.json")
    if os.path.exists(file_path):

        with open(file_path, "r") as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        df["_source_file"] = f"wearable_events/{participant}/heart_rate.json"
        df["_ingested_at"] = ingestion_time

        heart_rate_list.append(df)

bronze_heart_rate = pd.concat(heart_rate_list, ignore_index=True)
bronze_heart_rate.to_parquet(f"{bronze_output_dir}/bronze_heart_rate_events.parquet", index=False)