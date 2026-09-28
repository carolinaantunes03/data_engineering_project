
SELECT
    chronotype,
    chronotype_label,
    COUNT(participant_id) AS n_participants,
    ROUND(AVG(avg_daily_steps), 2) AS avg_daily_steps,
    ROUND(AVG(avg_total_sleep_min), 2) AS avg_total_sleep_min,
    ROUND(AVG(avg_sleep_efficiency_pct), 2) AS avg_sleep_efficiency_pct,
    ROUND(AVG(avg_deep_sleep_pct), 2) AS avg_deep_sleep_pct,
    ROUND(AVG(avg_heart_rate_bpm), 2) AS avg_heart_rate_bpm,
    ROUND(AVG(avg_wellness_composite), 2) AS avg_wellness_composite
FROM read_parquet('output/gold/gold_participant_profile.parquet')
GROUP BY chronotype, chronotype_label
ORDER BY chronotype;