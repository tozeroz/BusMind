import os
import sys
import csv
from datetime import datetime
from sqlalchemy import create_engine, text

def create_tables(conn):
    print("Creating tables...")
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_account (
            user_id BIGINT PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            nickname VARCHAR(50),
            role VARCHAR(20) NOT NULL DEFAULT 'passenger',
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at DATETIME
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS bus_station (
            station_id BIGINT PRIMARY KEY,
            bus_stop_code VARCHAR(30) UNIQUE,
            station_name VARCHAR(100) NOT NULL,
            road_name VARCHAR(100),
            longitude DECIMAL(10,7) NOT NULL,
            latitude DECIMAL(10,7) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS bus_line (
            line_id BIGINT PRIMARY KEY,
            service_no VARCHAR(30) NOT NULL,
            line_name VARCHAR(100) NOT NULL,
            operator VARCHAR(100),
            direction TINYINT NOT NULL DEFAULT 1,
            origin_station_id BIGINT,
            destination_station_id BIGINT,
            am_peak_freq VARCHAR(20),
            am_offpeak_freq VARCHAR(20),
            pm_peak_freq VARCHAR(20),
            pm_offpeak_freq VARCHAR(20),
            avg_service_frequency DECIMAL(6,2),
            status VARCHAR(20) NOT NULL DEFAULT 'running',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (origin_station_id) REFERENCES bus_station(station_id),
            FOREIGN KEY (destination_station_id) REFERENCES bus_station(station_id)
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS line_station (
            line_station_id VARCHAR(50) PRIMARY KEY,
            line_id BIGINT NOT NULL,
            station_id BIGINT NOT NULL,
            stop_sequence INTEGER NOT NULL,
            route_distance_km DECIMAL(8,3),
            wd_first_bus TIME,
            wd_last_bus TIME,
            sat_first_bus TIME,
            sat_last_bus TIME,
            sun_first_bus TIME,
            sun_last_bus TIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (line_id) REFERENCES bus_line(line_id),
            FOREIGN KEY (station_id) REFERENCES bus_station(station_id)
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS bus_vehicle (
            vehicle_id BIGINT PRIMARY KEY,
            vehicle_code VARCHAR(30) UNIQUE,
            line_id BIGINT NOT NULL,
            current_station_id BIGINT,
            next_station_id BIGINT,
            next_station_name VARCHAR(100),
            current_position_text VARCHAR(150),
            longitude DECIMAL(10,7),
            latitude DECIMAL(10,7),
            speed_kph DECIMAL(6,2),
            onboard_count INTEGER,
            capacity INTEGER,
            predicted_load_level VARCHAR(30),
            operation_status VARCHAR(20) NOT NULL DEFAULT 'normal',
            delay_minutes INTEGER NOT NULL DEFAULT 0,
            data_status VARCHAR(20) NOT NULL DEFAULT 'estimated',
            last_reported_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (line_id) REFERENCES bus_line(line_id),
            FOREIGN KEY (current_station_id) REFERENCES bus_station(station_id),
            FOREIGN KEY (next_station_id) REFERENCES bus_station(station_id)
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS passenger_flow_trend (
            flow_record_id BIGINT PRIMARY KEY AUTOINCREMENT,
            target_type VARCHAR(20) NOT NULL,
            target_id BIGINT NOT NULL,
            bus_stop_code VARCHAR(30),
            record_time DATETIME NOT NULL,
            day_type VARCHAR(20),
            tap_in_volume INTEGER NOT NULL DEFAULT 0,
            tap_out_volume INTEGER NOT NULL DEFAULT 0,
            total_flow INTEGER NOT NULL DEFAULT 0,
            flow_level VARCHAR(20),
            data_source VARCHAR(100),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS passenger_flow_prediction (
            prediction_id BIGINT PRIMARY KEY AUTOINCREMENT,
            target_type VARCHAR(20) NOT NULL,
            target_id VARCHAR(50) NOT NULL,
            prediction_time DATETIME NOT NULL,
            predict_time DATETIME NOT NULL,
            predicted_flow INTEGER NOT NULL,
            crowd_level VARCHAR(20) NOT NULL,
            confidence DECIMAL(5,4),
            model_version VARCHAR(100),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS eta_prediction (
            eta_prediction_id BIGINT PRIMARY KEY AUTOINCREMENT,
            vehicle_id BIGINT NOT NULL,
            line_id BIGINT NOT NULL,
            target_station_id BIGINT NOT NULL,
            prediction_time DATETIME NOT NULL,
            predicted_eta_minutes DECIMAL(8,2) NOT NULL,
            arrival_time DATETIME,
            vehicle_to_stop_distance_m DECIMAL(10,2),
            speed_kph DECIMAL(6,2),
            confidence DECIMAL(5,4),
            model_version VARCHAR(100),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicle_id) REFERENCES bus_vehicle(vehicle_id),
            FOREIGN KEY (line_id) REFERENCES bus_line(line_id),
            FOREIGN KEY (target_station_id) REFERENCES bus_station(station_id)
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS load_prediction (
            load_prediction_id BIGINT PRIMARY KEY AUTOINCREMENT,
            vehicle_id BIGINT NOT NULL,
            line_id BIGINT NOT NULL,
            station_id BIGINT,
            prediction_time DATETIME NOT NULL,
            predicted_load_level VARCHAR(30) NOT NULL,
            load_score DECIMAL(6,2),
            predicted_load_rate DECIMAL(6,4),
            onboard_count INTEGER,
            capacity INTEGER,
            confidence DECIMAL(5,4),
            model_version VARCHAR(100),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicle_id) REFERENCES bus_vehicle(vehicle_id),
            FOREIGN KEY (line_id) REFERENCES bus_line(line_id),
            FOREIGN KEY (station_id) REFERENCES bus_station(station_id)
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS location_poi (
            location_id BIGINT PRIMARY KEY AUTOINCREMENT,
            location_name VARCHAR(100) NOT NULL,
            location_type VARCHAR(30) NOT NULL,
            longitude DECIMAL(10,7) NOT NULL,
            latitude DECIMAL(10,7) NOT NULL,
            address VARCHAR(255),
            nearest_station_id BIGINT,
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nearest_station_id) REFERENCES bus_station(station_id)
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS map_road_segment (
            segment_id VARCHAR(50) PRIMARY KEY,
            segment_name VARCHAR(150) NOT NULL,
            line_id BIGINT NOT NULL,
            start_station_id BIGINT NOT NULL,
            end_station_id BIGINT NOT NULL,
            start_lat DECIMAL(10,7) NOT NULL,
            start_lon DECIMAL(10,7) NOT NULL,
            end_lat DECIMAL(10,7) NOT NULL,
            end_lon DECIMAL(10,7) NOT NULL,
            segment_distance_km DECIMAL(8,3),
            ride_time_minutes DECIMAL(8,2),
            avg_speed_kph DECIMAL(6,2),
            delay_minutes INTEGER NOT NULL DEFAULT 0,
            avg_passenger_flow DECIMAL(10,2),
            flow_level VARCHAR(20),
            path_coordinates VARCHAR(5000),
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (line_id) REFERENCES bus_line(line_id),
            FOREIGN KEY (start_station_id) REFERENCES bus_station(station_id),
            FOREIGN KEY (end_station_id) REFERENCES bus_station(station_id)
        )
    """))
    
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_query_history (
            history_id BIGINT PRIMARY KEY AUTOINCREMENT,
            user_id BIGINT,
            query_type VARCHAR(30) NOT NULL,
            origin_name VARCHAR(100),
            origin_longitude DECIMAL(10,7),
            origin_latitude DECIMAL(10,7),
            destination_name VARCHAR(100),
            destination_longitude DECIMAL(10,7),
            destination_latitude DECIMAL(10,7),
            selected_route_id BIGINT,
            query_content TEXT,
            result_summary TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user_account(user_id)
        )
    """))
    
    conn.commit()
    print("Tables created successfully!")

def main(data_dir):
    engine = create_engine("sqlite:///busmind.db")
    
    with engine.connect() as conn:
        create_tables(conn)
        
        print("Deleting existing data...")
        tables_to_delete = [
            "user_query_history", "map_road_segment", "location_poi",
            "load_prediction", "eta_prediction", "passenger_flow_prediction",
            "passenger_flow_trend", "bus_vehicle", "line_station", 
            "bus_line", "bus_station", "user_account"
        ]
        for table in tables_to_delete:
            try:
                conn.execute(text(f"DELETE FROM {table}"))
            except Exception:
                pass
        conn.commit()
        
        print("Importing bus stations...")
        with open(os.path.join(data_dir, 'bus_station.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(text("""
                    INSERT INTO bus_station (station_id, bus_stop_code, station_name, road_name, longitude, latitude)
                    VALUES (:station_id, :bus_stop_code, :station_name, :road_name, :longitude, :latitude)
                """), {
                    'station_id': int(row['station_id']),
                    'bus_stop_code': row['bus_stop_code'],
                    'station_name': row['station_name'],
                    'road_name': row.get('road_name', ''),
                    'longitude': float(row['longitude']),
                    'latitude': float(row['latitude'])
                })
        conn.commit()
        print("Imported bus stations")
        
        print("Importing bus lines...")
        with open(os.path.join(data_dir, 'bus_line.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(text("""
                    INSERT INTO bus_line (line_id, service_no, line_name, origin_station_id, destination_station_id, total_stations, distance_km, first_departure_time, last_departure_time, interval_minutes, status)
                    VALUES (:line_id, :service_no, :line_name, :origin_station_id, :destination_station_id, :total_stations, :distance_km, :first_departure_time, :last_departure_time, :interval_minutes, :status)
                """), {
                    'line_id': int(row['line_id']),
                    'service_no': row['service_no'],
                    'line_name': row['line_name'],
                    'origin_station_id': int(row['origin_station_id']) if row.get('origin_station_id') else None,
                    'destination_station_id': int(row['destination_station_id']) if row.get('destination_station_id') else None,
                    'total_stations': int(row.get('total_stations', 0)),
                    'distance_km': float(row.get('distance_km', 0.0)),
                    'first_departure_time': row.get('first_bus_time', ''),
                    'last_departure_time': row.get('last_bus_time', ''),
                    'interval_minutes': int(row.get('interval_minutes', 10)),
                    'status': 'running'
                })
        conn.commit()
        print("Imported bus lines")
        
        print("Importing line stations...")
        with open(os.path.join(data_dir, 'line_station.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                line_station_id = f"{row['line_id']}_{str(row['stop_sequence']).zfill(3)}"
                conn.execute(text("""
                    INSERT INTO line_station (line_station_id, line_id, station_id, stop_sequence)
                    VALUES (:line_station_id, :line_id, :station_id, :stop_sequence)
                """), {
                    'line_station_id': line_station_id,
                    'line_id': int(row['line_id']),
                    'station_id': int(row['station_id']),
                    'stop_sequence': int(row['stop_sequence'])
                })
        conn.commit()
        print("Imported line stations")
        
        print("Importing bus vehicles...")
        with open(os.path.join(data_dir, 'bus_vehicle.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(text("""
                    INSERT INTO bus_vehicle (vehicle_id, vehicle_code, line_id, longitude, latitude, capacity)
                    VALUES (:vehicle_id, :vehicle_code, :line_id, :longitude, :latitude, :capacity)
                """), {
                    'vehicle_id': int(row['vehicle_id']),
                    'vehicle_code': row.get('plate_number', f"VH{row['vehicle_id']}"),
                    'line_id': int(row['line_id']),
                    'longitude': 103.8521 + (int(row['vehicle_id']) % 5) * 0.002,
                    'latitude': 1.2897 + (int(row['vehicle_id']) % 5) * 0.001,
                    'capacity': int(row.get('capacity', 60))
                })
        conn.commit()
        print("Imported bus vehicles")
        
        print("Importing passenger flow trend...")
        with open(os.path.join(data_dir, 'passenger_flow_trend.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(text("""
                    INSERT INTO passenger_flow_trend (target_type, target_id, record_time, day_type, tap_in_volume, tap_out_volume, total_flow, flow_level)
                    VALUES (:target_type, :target_id, :record_time, :day_type, :tap_in_volume, :tap_out_volume, :total_flow, :flow_level)
                """), {
                    'target_type': 'station',
                    'target_id': int(row['station_id']),
                    'record_time': f"{row['year_month']}-01 {row['hour']}:00:00",
                    'day_type': row['day_type'],
                    'tap_in_volume': int(row['tap_in_volume']),
                    'tap_out_volume': int(row['tap_out_volume']),
                    'total_flow': int(row['total_flow']),
                    'flow_level': row.get('flow_level', '')
                })
        conn.commit()
        print("Imported passenger flow trend")
        
        print("Importing ETA predictions...")
        with open(os.path.join(data_dir, 'eta_prediction.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(text("""
                    INSERT INTO eta_prediction (vehicle_id, line_id, target_station_id, prediction_time, predicted_eta_minutes, arrival_time, vehicle_to_stop_distance_m, speed_kph, model_version)
                    VALUES (:vehicle_id, :line_id, :target_station_id, :prediction_time, :predicted_eta_minutes, :arrival_time, :vehicle_to_stop_distance_m, :speed_kph, :model_version)
                """), {
                    'vehicle_id': int(row['vehicle_id']),
                    'line_id': int(row['line_id']),
                    'target_station_id': int(row['target_station_id']),
                    'prediction_time': datetime.now(),
                    'predicted_eta_minutes': float(row['predicted_eta_minutes']),
                    'arrival_time': row['arrival_time'],
                    'vehicle_to_stop_distance_m': float(row['vehicle_to_stop_distance_m']),
                    'speed_kph': float(row['speed_kph']),
                    'model_version': row['model_version']
                })
        conn.commit()
        print("Imported ETA predictions")
        
        print("Importing load predictions...")
        with open(os.path.join(data_dir, 'load_prediction.csv'), 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(text("""
                    INSERT INTO load_prediction (vehicle_id, line_id, station_id, prediction_time, predicted_load_level, load_score, predicted_load_rate, onboard_count, capacity, confidence, model_version)
                    VALUES (:vehicle_id, :line_id, :station_id, :prediction_time, :predicted_load_level, :load_score, :predicted_load_rate, :onboard_count, :capacity, :confidence, :model_version)
                """), {
                    'vehicle_id': int(row['vehicle_id']),
                    'line_id': int(row['line_id']),
                    'station_id': int(row['station_id']),
                    'prediction_time': datetime.now(),
                    'predicted_load_level': row['predicted_load_level'],
                    'load_score': float(row['load_score']),
                    'predicted_load_rate': float(row['predicted_load_rate']),
                    'onboard_count': int(row['onboard_count']) if row['onboard_count'] else None,
                    'capacity': int(row['capacity']) if row['capacity'] else None,
                    'confidence': float(row['confidence']),
                    'model_version': row['model_version']
                })
        conn.commit()
        print("Imported load predictions")
        
        print("All data imported successfully!")

if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'import')
    
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    
    main(data_dir)