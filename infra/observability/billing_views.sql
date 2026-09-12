-- Run ONLY after Standard usage cost export is enabled and the source exists.
-- Standard billing export contains the whole billing account. These views filter
-- to Wardrub's project; do not connect the raw account export to Looker Studio.
-- No currency conversion, projected costs or inferred per-user costs.
CREATE OR REPLACE VIEW `gen-lang-client-0842206246.wardrub_reporting.daily_cost` AS
SELECT DATE(usage_start_time, 'Asia/Kolkata') AS day,
  service.description AS service, currency,
  SUM(cost) AS gross_cost,
  SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) AS c), 0)) AS credits,
  SUM(cost + IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) AS c), 0)) AS net_cost,
  MAX(export_time) AS last_export_time
FROM `gen-lang-client-0842206246.wardrub_billing.gcp_billing_export_v1_01CB0B_4400EB_4C366F`
WHERE project.id = 'gen-lang-client-0842206246'
GROUP BY day, service, currency;

CREATE OR REPLACE VIEW `gen-lang-client-0842206246.wardrub_reporting.monthly_invoice_cost` AS
SELECT invoice.month AS invoice_month, currency, service.description AS service,
  cost_type,
  SUM(cost + IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) AS c), 0)) AS net_cost,
  MAX(export_time) AS last_export_time
FROM `gen-lang-client-0842206246.wardrub_billing.gcp_billing_export_v1_01CB0B_4400EB_4C366F`
WHERE project.id = 'gen-lang-client-0842206246'
GROUP BY invoice_month, currency, service, cost_type
