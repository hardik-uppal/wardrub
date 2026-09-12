CREATE OR REPLACE VIEW `gen-lang-client-0842206246.wardrub_reporting.registration_summary` AS
SELECT collected_at AS snapshot_time,
 TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), collected_at, HOUR) AS snapshot_age_hours,
 CAST(JSON_VALUE(payload, '$.counts.total_registered') AS INT64) AS total_registered,
 CAST(JSON_VALUE(payload, '$.counts.enabled_accounts') AS INT64) AS enabled_accounts,
 CAST(JSON_VALUE(payload, '$.counts.disabled_accounts') AS INT64) AS disabled_accounts,
 CAST(JSON_VALUE(payload, '$.counts.with_avatar') AS INT64) AS with_avatar,
 CAST(JSON_VALUE(payload, '$.counts.with_any_garment') AS INT64) AS with_any_garment,
 CAST(JSON_VALUE(payload, '$.counts.with_ten_garments') AS INT64) AS with_ten_garments,
 CAST(JSON_VALUE(payload, '$.counts.with_profile') AS INT64) AS with_profile,
 CAST(JSON_VALUE(payload, '$.counts.with_saved_magazine') AS INT64) AS with_saved_magazine,
 CAST(JSON_VALUE(payload, '$.counts.ten_garments_without_saved_magazine') AS INT64) AS ten_garments_without_saved_magazine,
 CAST(JSON_VALUE(payload, '$.counts.ten_garments_without_profile') AS INT64) AS ten_garments_without_profile,
 CAST(JSON_VALUE(payload, '$.counts.color_ready') AS INT64) AS explicit_color_stage_ready,
 CAST(JSON_VALUE(payload, '$.counts.fit_ready') AS INT64) AS explicit_fit_stage_ready
FROM `gen-lang-client-0842206246.wardrub_events.user_snapshots`
QUALIFY ROW_NUMBER() OVER (ORDER BY collected_at DESC) = 1;

-- Registrations of currently existing accounts, not an immutable historical signup ledger.
CREATE OR REPLACE VIEW `gen-lang-client-0842206246.wardrub_reporting.registrations_by_day` AS
WITH latest AS (
 SELECT collected_at, PARSE_JSON(payload).signup_days AS signups
 FROM `gen-lang-client-0842206246.wardrub_events.user_snapshots`
 QUALIFY ROW_NUMBER() OVER (ORDER BY collected_at DESC) = 1
)
SELECT DATE(day) AS signup_day, INT64(signups[day]) AS registered_accounts,
 collected_at AS snapshot_time
FROM latest, UNNEST(JSON_KEYS(signups)) AS day;

-- 7/30 rolling calendar days include today. Never SUM daily distinct user counts.
CREATE OR REPLACE VIEW `gen-lang-client-0842206246.wardrub_reporting.active_user_summary` AS
WITH events AS (
 SELECT timestamp, jsonpayload.user_id AS uid, jsonpayload.event_name AS event_name
 FROM `gen-lang-client-0842206246.wardrub_events.run_googleapis_com_stdout`
 WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
   AND jsonpayload.event_schema = 'wardrub_product_v1'
   AND jsonpayload.user_id != ''
   AND jsonpayload.event_name IN ('sign_in_completed','avatar_created','first_garment_added',
     'first_try_on_completed','first_look_saved','profile_loaded','magazine_requested',
     'magazine_generated','magazine_cache_hit','magazine_failed','magazine_onboarding')
), stats AS (
 SELECT MIN(timestamp) AS first_observed_event, MAX(timestamp) AS last_observed_event,
 COUNT(DISTINCT IF(DATE(timestamp,'Asia/Kolkata')=CURRENT_DATE('Asia/Kolkata'),uid,NULL)) AS dau,
 COUNT(DISTINCT IF(DATE(timestamp,'Asia/Kolkata')>=DATE_SUB(CURRENT_DATE('Asia/Kolkata'),INTERVAL 6 DAY),uid,NULL)) AS wau,
 COUNT(DISTINCT IF(DATE(timestamp,'Asia/Kolkata')>=DATE_SUB(CURRENT_DATE('Asia/Kolkata'),INTERVAL 29 DAY),uid,NULL)) AS mau
 FROM events
)
SELECT first_observed_event, last_observed_event,
 IF(last_observed_event IS NULL, NULL, dau) AS dau,
 IF(last_observed_event IS NULL, NULL, wau) AS wau,
 IF(last_observed_event IS NULL, NULL, mau) AS mau,
 IF(last_observed_event IS NULL,'NO_OBSERVED_DATA','PARTIAL_INSTRUMENTATION') AS coverage_status
FROM stats;
