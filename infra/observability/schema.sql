-- Bootstrap schema for empty dashboards before the first real event arrives.
-- Logging may add its standard envelope fields during export.
CREATE TABLE IF NOT EXISTS `gen-lang-client-0842206246.wardrub_events.run_googleapis_com_stdout` (
 timestamp TIMESTAMP, insertId STRING,
 jsonpayload STRUCT<event_schema STRING, event_name STRING, user_id STRING,
                    event_time STRING, revision STRING, severity STRING, garment_count FLOAT64>
) PARTITION BY DATE(timestamp) OPTIONS(partition_expiration_days=180);

CREATE TABLE IF NOT EXISTS `gen-lang-client-0842206246.wardrub_events.user_snapshots` (
 collected_at TIMESTAMP, payload STRING
) PARTITION BY DATE(collected_at) OPTIONS(partition_expiration_days=180)
