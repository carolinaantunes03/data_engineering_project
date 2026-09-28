SELECT
    chronotype,
    chronotype_label,
    n_participants,
    avg_daily_steps,
    avg_total_sleep_min,
    avg_sleep_efficiency_pct,
    avg_deep_sleep_pct,
    avg_heart_rate_bpm,
    avg_wellness_composite
FROM read_parquet('output/gold/gold_cohort_comparison.parquet')
ORDER BY chronotype;