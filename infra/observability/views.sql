-- Source is the partitioned Cloud Run stdout table produced by the filtered sink.
-- Logging can deliver duplicates: deduplicate by insertId before counting.
-- Only aggregate views are connected to Looker Studio. No UID/email fields exported.
CREATE OR REPLACE VIEW `gen-lang-client-0842206246.wardrub_reporting.daily_activity` AS
WITH events AS (
  SELECT timestamp, jsonpayload.event_name AS event_name, jsonpayload.user_id AS user_id
  FROM `gen-lang-client-0842206246.wardrub_events.run_googleapis_com_stdout`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
    AND jsonpayload.event_schema = 'wardrub_product_v1'
    AND jsonpayload.user_id != ''
  QUALIFY ROW_NUMBER() OVER (PARTITION BY insertId ORDER BY timestamp) = 1
)
SELECT DATE(timestamp, 'Asia/Kolkata') AS day,
  COUNT(DISTINCT user_id) AS observed_active_users,
  COUNT(*) AS observed_events,
  COUNT(DISTINCT IF(event_name = 'profile_loaded', user_id, NULL)) AS profile_visitors,
  COUNT(DISTINCT IF(event_name = 'magazine_requested', user_id, NULL)) AS magazine_users
FROM events GROUP BY day;

CREATE OR REPLACE VIEW `gen-lang-client-0842206246.wardrub_reporting.daily_milestones` AS
WITH events AS (
  SELECT timestamp, jsonpayload.event_name AS event_name, jsonpayload.user_id AS user_id
  FROM `gen-lang-client-0842206246.wardrub_events.run_googleapis_com_stdout`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
    AND jsonpayload.event_schema = 'wardrub_product_v1'
    AND jsonpayload.user_id != ''
  QUALIFY ROW_NUMBER() OVER (PARTITION BY insertId ORDER BY timestamp) = 1
)
SELECT DATE(timestamp, 'Asia/Kolkata') AS day, event_name,
  COUNT(*) AS event_count, COUNT(DISTINCT user_id) AS unique_users
FROM events GROUP BY day, event_name;

CREATE OR REPLACE VIEW `gen-lang-client-0842206246.wardrub_reporting.daily_magazine` AS
WITH events AS (
  SELECT timestamp, jsonpayload.event_name AS event_name
  FROM `gen-lang-client-0842206246.wardrub_events.run_googleapis_com_stdout`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
    AND jsonpayload.event_schema = 'wardrub_product_v1'
    AND jsonpayload.user_id != ''
  QUALIFY ROW_NUMBER() OVER (PARTITION BY insertId ORDER BY timestamp) = 1
)
SELECT DATE(timestamp, 'Asia/Kolkata') AS day,
  COUNTIF(event_name = 'magazine_requested') AS requests,
  COUNTIF(event_name = 'magazine_generated') AS generations,
  COUNTIF(event_name = 'magazine_cache_hit') AS cache_hits,
  COUNTIF(event_name = 'magazine_failed') AS failures,
  COUNTIF(event_name = 'magazine_onboarding') AS below_garment_threshold
FROM events GROUP BY day
