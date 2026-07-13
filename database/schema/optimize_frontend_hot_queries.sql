-- BusMind frontend hot-query optimization for existing MySQL databases.
-- Run this after the base schema is already present:
--   mysql -u <user> -p busmind < database/schema/optimize_frontend_hot_queries.sql

USE busmind;

SET NAMES utf8mb4;
SET @schema_name = DATABASE();

-- Add generated hour column used by station-flow lookups if it does not exist yet.
SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = @schema_name
              AND table_name = 'passenger_flow_trend'
              AND column_name = 'record_hour'
        ),
        'SELECT 1',
        'ALTER TABLE passenger_flow_trend ADD COLUMN record_hour TINYINT GENERATED ALWAYS AS (HOUR(record_time)) STORED'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'bus_station' AND index_name = 'idx_station_status_coordinate'
        ),
        'SELECT 1',
        'ALTER TABLE bus_station ADD KEY idx_station_status_coordinate (status, longitude, latitude)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'line_station' AND index_name = 'idx_line_station_line_station_sequence'
        ),
        'SELECT 1',
        'ALTER TABLE line_station ADD KEY idx_line_station_line_station_sequence (line_id, station_id, stop_sequence)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'line_station' AND index_name = 'idx_line_station_station_line_sequence'
        ),
        'SELECT 1',
        'ALTER TABLE line_station ADD KEY idx_line_station_station_line_sequence (station_id, line_id, stop_sequence)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'bus_vehicle' AND index_name = 'idx_vehicle_line_code'
        ),
        'SELECT 1',
        'ALTER TABLE bus_vehicle ADD KEY idx_vehicle_line_code (line_id, vehicle_code, vehicle_id)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'bus_vehicle' AND index_name = 'idx_vehicle_line_reported'
        ),
        'SELECT 1',
        'ALTER TABLE bus_vehicle ADD KEY idx_vehicle_line_reported (line_id, last_reported_at, updated_at)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'bus_eta_status' AND index_name = 'idx_eta_line_time'
        ),
        'SELECT 1',
        'ALTER TABLE bus_eta_status ADD KEY idx_eta_line_time (line_id, query_time)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'bus_eta_status' AND index_name = 'idx_eta_line_station_time'
        ),
        'SELECT 1',
        'ALTER TABLE bus_eta_status ADD KEY idx_eta_line_station_time (line_id, target_station_id, query_time)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'bus_eta_status' AND index_name = 'idx_eta_target_line_time'
        ),
        'SELECT 1',
        'ALTER TABLE bus_eta_status ADD KEY idx_eta_target_line_time (target_station_id, line_id, query_time)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'bus_load_status' AND index_name = 'idx_load_line_station_time'
        ),
        'SELECT 1',
        'ALTER TABLE bus_load_status ADD KEY idx_load_line_station_time (line_id, station_id, query_time)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'bus_load_status' AND index_name = 'idx_load_station_line_time'
        ),
        'SELECT 1',
        'ALTER TABLE bus_load_status ADD KEY idx_load_station_line_time (station_id, line_id, query_time)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'passenger_flow_trend' AND index_name = 'idx_flow_target_hour'
        ),
        'SELECT 1',
        'ALTER TABLE passenger_flow_trend ADD KEY idx_flow_target_hour (target_type, target_id, record_hour, record_time)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'passenger_flow_trend' AND index_name = 'idx_flow_target_hour_level'
        ),
        'SELECT 1',
        'ALTER TABLE passenger_flow_trend ADD KEY idx_flow_target_hour_level (target_type, target_id, record_hour, flow_level)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'map_road_segment' AND index_name = 'idx_segment_line_sequence'
        ),
        'SELECT 1',
        'ALTER TABLE map_road_segment ADD KEY idx_segment_line_sequence (line_id, stop_sequence)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'lta_bus_arrival' AND index_name = 'idx_lta_station_line_vehicle_time'
        ),
        'SELECT 1',
        'ALTER TABLE lta_bus_arrival ADD KEY idx_lta_station_line_vehicle_time (station_id, line_id, vehicle_id, query_time)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = (
    SELECT IF(
        EXISTS (
            SELECT 1 FROM information_schema.statistics
            WHERE table_schema = @schema_name AND table_name = 'lta_bus_arrival' AND index_name = 'idx_lta_stop_line_vehicle_time'
        ),
        'SELECT 1',
        'ALTER TABLE lta_bus_arrival ADD KEY idx_lta_stop_line_vehicle_time (bus_stop_code, line_id, vehicle_id, query_time)'
    )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

DROP VIEW IF EXISTS v_map_station;
CREATE VIEW v_map_station AS
SELECT
    s.station_id,
    s.bus_stop_code,
    s.station_name,
    s.road_name,
    s.longitude,
    s.latitude,
    COUNT(DISTINCT ls.line_id) AS line_count,
    COUNT(DISTINCT l.service_no) AS service_count,
    GROUP_CONCAT(DISTINCT l.line_id ORDER BY l.line_id SEPARATOR '|') AS line_ids,
    GROUP_CONCAT(DISTINCT l.line_name ORDER BY l.line_id SEPARATOR '|') AS line_names,
    GROUP_CONCAT(DISTINCT l.service_no ORDER BY l.service_no SEPARATOR '|') AS service_nos
FROM bus_station s
LEFT JOIN line_station ls ON ls.station_id = s.station_id
LEFT JOIN bus_line l ON l.line_id = ls.line_id
GROUP BY
    s.station_id,
    s.bus_stop_code,
    s.station_name,
    s.road_name,
    s.longitude,
    s.latitude;

DROP VIEW IF EXISTS v_station_flow_hourly_profile;
CREATE VIEW v_station_flow_hourly_profile AS
SELECT
    target_id AS station_id,
    record_hour,
    AVG(total_flow) AS avg_total_flow,
    MAX(record_time) AS latest_record_time,
    COUNT(*) AS sample_count,
    CASE
        WHEN SUM(flow_level = 'overcrowded') >= GREATEST(
            SUM(flow_level = 'limited_standing'),
            SUM(flow_level = 'standing_available'),
            SUM(flow_level = 'seats_available'),
            SUM(flow_level = 'high'),
            SUM(flow_level = 'medium'),
            SUM(flow_level = 'low')
        ) THEN 'overcrowded'
        WHEN SUM(flow_level = 'limited_standing') >= GREATEST(
            SUM(flow_level = 'standing_available'),
            SUM(flow_level = 'seats_available'),
            SUM(flow_level = 'high'),
            SUM(flow_level = 'medium'),
            SUM(flow_level = 'low')
        ) THEN 'limited_standing'
        WHEN SUM(flow_level = 'standing_available') >= GREATEST(
            SUM(flow_level = 'seats_available'),
            SUM(flow_level = 'high'),
            SUM(flow_level = 'medium'),
            SUM(flow_level = 'low')
        ) THEN 'standing_available'
        WHEN SUM(flow_level = 'seats_available') >= GREATEST(
            SUM(flow_level = 'high'),
            SUM(flow_level = 'medium'),
            SUM(flow_level = 'low')
        ) THEN 'seats_available'
        WHEN SUM(flow_level = 'high') >= GREATEST(
            SUM(flow_level = 'medium'),
            SUM(flow_level = 'low')
        ) THEN 'high'
        WHEN SUM(flow_level = 'medium') >= SUM(flow_level = 'low') THEN 'medium'
        ELSE 'low'
    END AS dominant_flow_level
FROM passenger_flow_trend
WHERE target_type = 'station'
GROUP BY target_id, record_hour;
