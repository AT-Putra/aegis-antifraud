-- T-21 (F-16): dimensi campaign + source_params (#5) di OLAP. Idempoten.

ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS campaign String;
ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS source_params String;
ALTER TABLE decision_log   ADD COLUMN IF NOT EXISTS campaign String;
