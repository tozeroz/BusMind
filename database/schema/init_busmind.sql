-- BusMind current schema initialization.
-- Target database and user are managed on the cloud server:
--   database: busmind
--   app user: busmind_dev
--
-- This file only initializes tables and views. It does not create the
-- database, user, or SSH tunnel.

USE busmind;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS user_account (
    user_id BIGINT NOT NULL AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NULL,
    email VARCHAR(100) NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'passenger',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at DATETIME NULL,
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_user_username (username),
    UNIQUE KEY uk_user_email (email),
    KEY idx_user_role (role),
    KEY idx_user_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bus_station (
    station_id BIGINT NOT NULL,
    bus_stop_code VARCHAR(30) NULL,
    station_name VARCHAR(100) NOT NULL,
    road_name VARCHAR(100) NULL,
    latitude DECIMAL(10,7) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (station_id),
    UNIQUE KEY uk_station_code (bus_stop_code),
    KEY idx_station_name (station_name),
    KEY idx_station_coordinate (longitude, latitude),
    KEY idx_station_status_coordinate (status, longitude, latitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_query_history (
    history_id BIGINT NOT NULL AUTO_INCREMENT,
    user_id BIGINT NULL,
    query_type VARCHAR(30) NOT NULL,
    origin_name VARCHAR(100) NULL,
    origin_longitude DECIMAL(10,7) NULL,
    origin_latitude DECIMAL(10,7) NULL,
    destination_name VARCHAR(100) NULL,
    destination_longitude DECIMAL(10,7) NULL,
    destination_latitude DECIMAL(10,7) NULL,
    selected_route_id BIGINT NULL,
    query_content TEXT NULL,
    result_summary TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (history_id),
    KEY idx_history_user_time (user_id, created_at),
    KEY idx_history_type (query_type),
    CONSTRAINT fk_history_user FOREIGN KEY (user_id) REFERENCES user_account (user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS location_poi (
    location_id BIGINT NOT NULL AUTO_INCREMENT,
    location_name VARCHAR(100) NOT NULL,
    location_type VARCHAR(30) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    latitude DECIMAL(10,7) NOT NULL,
    address VARCHAR(255) NULL,
    nearest_station_id BIGINT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (location_id),
    KEY idx_location_name (location_name),
    KEY idx_location_type (location_type),
    KEY idx_location_coordinate (longitude, latitude),
    KEY idx_location_station (nearest_station_id),
    CONSTRAINT fk_location_nearest_station FOREIGN KEY (nearest_station_id) REFERENCES bus_station (station_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bus_line (
    line_id BIGINT NOT NULL,
    service_no VARCHAR(30) NOT NULL,
    line_name VARCHAR(100) NOT NULL,
    operator VARCHAR(100) NULL,
    direction TINYINT NOT NULL DEFAULT 1,
    category VARCHAR(50) NULL,
    origin_station_id BIGINT NULL,
    origin_stop_code VARCHAR(30) NULL,
    destination_station_id BIGINT NULL,
    destination_stop_code VARCHAR(30) NULL,
    am_peak_freq VARCHAR(20) NULL,
    am_offpeak_freq VARCHAR(20) NULL,
    pm_peak_freq VARCHAR(20) NULL,
    pm_offpeak_freq VARCHAR(20) NULL,
    avg_service_frequency DECIMAL(6,2) NULL,
    loop_desc VARCHAR(255) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (line_id),
    UNIQUE KEY uk_line_service_direction (service_no, direction),
    KEY idx_line_service_no (service_no),
    KEY idx_line_name (line_name),
    KEY idx_line_status (status),
    KEY idx_line_origin_station (origin_station_id),
    KEY idx_line_destination_station (destination_station_id),
    CONSTRAINT fk_line_origin_station FOREIGN KEY (origin_station_id) REFERENCES bus_station (station_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_line_destination_station FOREIGN KEY (destination_station_id) REFERENCES bus_station (station_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS line_station (
    line_station_id VARCHAR(50) NOT NULL,
    line_id BIGINT NOT NULL,
    service_no VARCHAR(30) NULL,
    line_name VARCHAR(100) NULL,
    operator VARCHAR(100) NULL,
    direction TINYINT NULL,
    stop_sequence INT NOT NULL,
    station_id BIGINT NOT NULL,
    bus_stop_code VARCHAR(30) NULL,
    route_distance_km DECIMAL(8,3) NULL,
    wd_first_bus TIME NULL,
    wd_last_bus TIME NULL,
    sat_first_bus TIME NULL,
    sat_last_bus TIME NULL,
    sun_first_bus TIME NULL,
    sun_last_bus TIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (line_station_id),
    UNIQUE KEY uk_line_station_sequence (line_id, stop_sequence),
    KEY idx_line_station_pair (line_id, station_id),
    KEY idx_line_station_station (station_id),
    KEY idx_line_station_line_station_sequence (line_id, station_id, stop_sequence),
    KEY idx_line_station_station_line_sequence (station_id, line_id, stop_sequence),
    CONSTRAINT fk_line_station_line FOREIGN KEY (line_id) REFERENCES bus_line (line_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_line_station_station FOREIGN KEY (station_id) REFERENCES bus_station (station_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bus_vehicle (
    vehicle_id BIGINT NOT NULL,
    vehicle_code VARCHAR(30) NULL,
    line_id BIGINT NOT NULL,
    service_no VARCHAR(30) NULL,
    line_name VARCHAR(100) NULL,
    current_station_id BIGINT NULL,
    next_station_id BIGINT NULL,
    next_station_name VARCHAR(100) NULL,
    current_position_text VARCHAR(150) NULL,
    longitude DECIMAL(10,7) NULL,
    latitude DECIMAL(10,7) NULL,
    speed_kph DECIMAL(6,2) NULL,
    onboard_count INT NULL,
    capacity INT NULL,
    load_level VARCHAR(30) NULL,
    load_code VARCHAR(10) NULL,
    load_score DECIMAL(6,2) NULL,
    operation_status VARCHAR(20) NOT NULL DEFAULT 'normal',
    delay_minutes INT NOT NULL DEFAULT 0,
    data_status VARCHAR(20) NOT NULL DEFAULT 'estimated',
    last_reported_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (vehicle_id),
    UNIQUE KEY uk_vehicle_code (vehicle_code),
    KEY idx_vehicle_line (line_id),
    KEY idx_vehicle_current_station (current_station_id),
    KEY idx_vehicle_next_station (next_station_id),
    KEY idx_vehicle_status (operation_status),
    KEY idx_vehicle_updated (updated_at),
    KEY idx_vehicle_line_code (line_id, vehicle_code, vehicle_id),
    KEY idx_vehicle_line_reported (line_id, last_reported_at, updated_at),
    CONSTRAINT fk_vehicle_line FOREIGN KEY (line_id) REFERENCES bus_line (line_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_vehicle_current_station FOREIGN KEY (current_station_id) REFERENCES bus_station (station_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_vehicle_next_station FOREIGN KEY (next_station_id) REFERENCES bus_station (station_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bus_eta_status (
    eta_status_id BIGINT NOT NULL AUTO_INCREMENT,
    vehicle_id BIGINT NOT NULL,
    line_id BIGINT NOT NULL,
    target_station_id BIGINT NOT NULL,
    bus_stop_code VARCHAR(30) NULL,
    query_time DATETIME NOT NULL,
    eta_minutes DECIMAL(8,2) NOT NULL,
    arrival_time DATETIME NULL,
    vehicle_to_stop_distance_m DECIMAL(10,2) NULL,
    speed_kph DECIMAL(6,2) NULL,
    confidence DECIMAL(5,4) NULL,
    data_source VARCHAR(100) NOT NULL DEFAULT 'lta_bus_arrival',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (eta_status_id),
    UNIQUE KEY uk_eta_vehicle_station_time (vehicle_id, target_station_id, query_time),
    KEY idx_eta_vehicle_time (vehicle_id, query_time),
    KEY idx_eta_line_station (line_id, target_station_id),
    KEY idx_eta_line_time (line_id, query_time),
    KEY idx_eta_line_station_time (line_id, target_station_id, query_time),
    KEY idx_eta_target_line_time (target_station_id, line_id, query_time),
    KEY idx_eta_arrival_time (arrival_time),
    CONSTRAINT fk_eta_line FOREIGN KEY (line_id) REFERENCES bus_line (line_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_eta_station FOREIGN KEY (target_station_id) REFERENCES bus_station (station_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bus_load_status (
    load_status_id BIGINT NOT NULL AUTO_INCREMENT,
    vehicle_id BIGINT NOT NULL,
    line_id BIGINT NOT NULL,
    station_id BIGINT NULL,
    bus_stop_code VARCHAR(30) NULL,
    query_time DATETIME NOT NULL,
    load_code VARCHAR(10) NULL,
    load_level VARCHAR(30) NOT NULL,
    load_score DECIMAL(6,2) NULL,
    load_rate DECIMAL(6,4) NULL,
    onboard_count INT NULL,
    capacity INT NULL,
    confidence DECIMAL(5,4) NULL,
    data_source VARCHAR(100) NOT NULL DEFAULT 'lta_bus_arrival',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (load_status_id),
    UNIQUE KEY uk_load_vehicle_station_time (vehicle_id, station_id, query_time),
    KEY idx_load_vehicle_time (vehicle_id, query_time),
    KEY idx_load_line_time (line_id, query_time),
    KEY idx_load_station_time (station_id, query_time),
    KEY idx_load_line_station_time (line_id, station_id, query_time),
    KEY idx_load_station_line_time (station_id, line_id, query_time),
    CONSTRAINT fk_load_line FOREIGN KEY (line_id) REFERENCES bus_line (line_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_load_station FOREIGN KEY (station_id) REFERENCES bus_station (station_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS passenger_flow_trend (
    flow_record_id BIGINT NOT NULL AUTO_INCREMENT,
    target_type VARCHAR(20) NOT NULL,
    target_id BIGINT NOT NULL,
    bus_stop_code VARCHAR(30) NULL,
    record_time DATETIME NOT NULL,
    record_hour TINYINT GENERATED ALWAYS AS (HOUR(record_time)) STORED,
    day_type VARCHAR(20) NULL,
    tap_in_volume INT NOT NULL DEFAULT 0,
    tap_out_volume INT NOT NULL DEFAULT 0,
    total_flow INT NOT NULL DEFAULT 0,
    flow_level VARCHAR(20) NULL,
    data_source VARCHAR(100) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (flow_record_id),
    UNIQUE KEY uk_flow_target_time (target_type, target_id, record_time, day_type),
    KEY idx_flow_target_time (target_type, target_id, record_time),
    KEY idx_flow_target_hour (target_type, target_id, record_hour, record_time),
    KEY idx_flow_target_hour_level (target_type, target_id, record_hour, flow_level),
    KEY idx_flow_record_time (record_time),
    KEY idx_flow_level (flow_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS passenger_flow_prediction (
    prediction_id BIGINT NOT NULL AUTO_INCREMENT,
    target_type VARCHAR(20) NOT NULL,
    target_id VARCHAR(50) NOT NULL,
    prediction_time DATETIME NOT NULL,
    predict_time DATETIME NOT NULL,
    predicted_flow INT NOT NULL,
    crowd_level VARCHAR(20) NOT NULL,
    confidence DECIMAL(5,4) NULL,
    model_version VARCHAR(100) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (prediction_id),
    KEY idx_flow_prediction_target_time (target_type, target_id, predict_time),
    KEY idx_flow_prediction_created (prediction_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS map_road_segment (
    segment_id VARCHAR(50) NOT NULL,
    segment_name VARCHAR(150) NOT NULL,
    line_id BIGINT NOT NULL,
    service_no VARCHAR(30) NULL,
    line_name VARCHAR(100) NULL,
    direction TINYINT NULL,
    stop_sequence INT NULL,
    start_station_id BIGINT NOT NULL,
    start_station_name VARCHAR(100) NULL,
    end_station_id BIGINT NOT NULL,
    end_station_name VARCHAR(100) NULL,
    start_lat DECIMAL(10,7) NOT NULL,
    start_lon DECIMAL(10,7) NOT NULL,
    end_lat DECIMAL(10,7) NOT NULL,
    end_lon DECIMAL(10,7) NOT NULL,
    segment_distance_km DECIMAL(8,3) NULL,
    ride_time_minutes DECIMAL(8,2) NULL,
    avg_speed_kph DECIMAL(6,2) NULL,
    delay_minutes INT NOT NULL DEFAULT 0,
    avg_passenger_flow DECIMAL(10,2) NULL,
    flow_level VARCHAR(20) NULL,
    path_coordinates JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (segment_id),
    KEY idx_segment_line (line_id),
    KEY idx_segment_line_sequence (line_id, stop_sequence),
    KEY idx_segment_start_end (start_station_id, end_station_id),
    KEY idx_segment_flow_level (flow_level),
    CONSTRAINT fk_segment_line FOREIGN KEY (line_id) REFERENCES bus_line (line_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_segment_start_station FOREIGN KEY (start_station_id) REFERENCES bus_station (station_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_segment_end_station FOREIGN KEY (end_station_id) REFERENCES bus_station (station_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS lta_bus_arrival (
    arrival_record_id BIGINT NOT NULL AUTO_INCREMENT,
    query_time DATETIME NOT NULL,
    station_id BIGINT NULL,
    bus_stop_code VARCHAR(30) NULL,
    service_no VARCHAR(30) NULL,
    line_id BIGINT NULL,
    line_name VARCHAR(100) NULL,
    operator VARCHAR(100) NULL,
    visit_order INT NULL,
    origin_stop_code VARCHAR(30) NULL,
    destination_stop_code VARCHAR(30) NULL,
    estimated_arrival DATETIME NULL,
    eta_minutes DECIMAL(8,2) NULL,
    duration_ms BIGINT NULL,
    monitored TINYINT NULL,
    vehicle_id BIGINT NULL,
    vehicle_latitude DECIMAL(10,7) NULL,
    vehicle_longitude DECIMAL(10,7) NULL,
    visit_number INT NULL,
    load_code VARCHAR(10) NULL,
    load_level VARCHAR(30) NULL,
    load_score DECIMAL(6,2) NULL,
    load_rate DECIMAL(6,4) NULL,
    onboard_count INT NULL,
    capacity INT NULL,
    bus_type VARCHAR(30) NULL,
    feature VARCHAR(30) NULL,
    vehicle_to_stop_distance_m DECIMAL(10,2) NULL,
    speed_kph DECIMAL(6,2) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (arrival_record_id),
    UNIQUE KEY uk_lta_arrival_sample (vehicle_id, station_id, line_id, query_time, visit_order),
    KEY idx_lta_service_stop_time (service_no, bus_stop_code, query_time),
    KEY idx_lta_vehicle_time (vehicle_id, query_time),
    KEY idx_lta_station_line_vehicle_time (station_id, line_id, vehicle_id, query_time),
    KEY idx_lta_stop_line_vehicle_time (bus_stop_code, line_id, vehicle_id, query_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS traffic_speed_bands (
    traffic_record_id BIGINT NOT NULL AUTO_INCREMENT,
    query_time DATETIME NOT NULL,
    link_id BIGINT NULL,
    road_name VARCHAR(150) NULL,
    road_category VARCHAR(80) NULL,
    speed_band INT NOT NULL,
    minimum_speed_kmh DECIMAL(6,2) NULL,
    maximum_speed_kmh DECIMAL(6,2) NULL,
    congestion_score DECIMAL(6,4) NULL,
    heat_color VARCHAR(20) NULL,
    start_lon DECIMAL(10,7) NOT NULL,
    start_lat DECIMAL(10,7) NOT NULL,
    end_lon DECIMAL(10,7) NOT NULL,
    end_lat DECIMAL(10,7) NOT NULL,
    line_coordinates JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (traffic_record_id),
    UNIQUE KEY uk_traffic_link_time (link_id, query_time),
    KEY idx_traffic_road_name (road_name),
    KEY idx_traffic_record_time (query_time),
    KEY idx_traffic_speed_band (speed_band)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

-- Email verification code table for registration and other flows.
CREATE TABLE IF NOT EXISTS email_verification_code (
    code_id BIGINT NOT NULL AUTO_INCREMENT,
    email VARCHAR(100) NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    purpose VARCHAR(30) NOT NULL DEFAULT 'register',
    expires_at DATETIME NOT NULL,
    used_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (code_id),
    KEY idx_email_verification_email (email),
    KEY idx_email_verification_purpose (purpose),
    KEY idx_email_verification_expires (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
