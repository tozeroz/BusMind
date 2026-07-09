import os
import sys
import csv
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.bus_line import BusLine, BusStation, LineStation
from app.models.bus_vehicle import BusVehicle, BusRealtime
from app.models.history import PassengerFlowTrend, PassengerLoadHistory, EtaPrediction, LoadPrediction

def get_session():
    engine = create_engine("sqlite:///busmind.db")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def import_bus_stations(session, csv_path):
    print(f"Importing bus stations from {csv_path}...")
    session.query(BusStation).delete()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            station = BusStation(
                station_id=int(row['station_id']),
                station_name=row['station_name'],
                station_code=row['bus_stop_code'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                address=row.get('road_name', ''),
                zone=row.get('zone', '')
            )
            session.add(station)
            count += 1
        session.commit()
    print(f"Imported {count} bus stations")

def import_bus_lines(session, csv_path):
    print(f"Importing bus lines from {csv_path}...")
    session.query(BusLine).delete()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            line = BusLine(
                line_id=int(row['line_id']),
                line_name=row['line_name'],
                line_code=row['service_no'],
                start_station=row.get('origin_station_name', ''),
                end_station=row.get('destination_station_name', ''),
                total_stations=int(row.get('total_stations', 0)),
                distance_km=float(row.get('distance_km', 0.0)),
                first_departure_time=row.get('first_bus_time', ''),
                last_departure_time=row.get('last_bus_time', ''),
                interval_minutes=int(row.get('interval_minutes', 10)),
                status='active'
            )
            session.add(line)
            count += 1
        session.commit()
    print(f"Imported {count} bus lines")

def import_line_stations(session, csv_path):
    print(f"Importing line stations from {csv_path}...")
    session.query(LineStation).delete()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            line_station = LineStation(
                line_id=int(row['line_id']),
                station_id=int(row['station_id']),
                order_index=int(row['stop_sequence'])
            )
            session.add(line_station)
            count += 1
        session.commit()
    print(f"Imported {count} line stations")

def import_bus_vehicles(session, csv_path):
    print(f"Importing bus vehicles from {csv_path}...")
    session.query(BusVehicle).delete()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            vehicle = BusVehicle(
                vehicle_id=int(row['vehicle_id']),
                vehicle_code=row.get('plate_number', f"VH{row['vehicle_id']}"),
                line_id=int(row['line_id']),
                current_latitude=1.2897 + (int(row['vehicle_id']) % 5) * 0.001,
                current_longitude=103.8521 + (int(row['vehicle_id']) % 5) * 0.002,
                capacity=int(row.get('capacity', 60))
            )
            session.add(vehicle)
            count += 1
        session.commit()
    print(f"Imported {count} bus vehicles")

def import_passenger_flow_trend(session, csv_path):
    print(f"Importing passenger flow trend from {csv_path}...")
    session.query(PassengerFlowTrend).delete()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            flow = PassengerFlowTrend(
                year_month=row['year_month'],
                day_type=row['day_type'],
                hour=int(row['hour']),
                station_id=int(row['station_id']) if row['station_id'] else None,
                tap_in_volume=int(row['tap_in_volume']),
                tap_out_volume=int(row['tap_out_volume']),
                total_flow=int(row['total_flow']),
                flow_level=row.get('flow_level', '')
            )
            session.add(flow)
            count += 1
        session.commit()
    print(f"Imported {count} passenger flow records")

def import_eta_predictions(session, csv_path):
    print(f"Importing ETA predictions from {csv_path}...")
    session.query(EtaPrediction).delete()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            eta = EtaPrediction(
                vehicle_id=int(row['vehicle_id']),
                line_id=int(row['line_id']) if row['line_id'] else None,
                target_station_id=int(row['target_station_id']),
                predicted_eta_minutes=float(row['predicted_eta_minutes']),
                arrival_time=datetime.fromisoformat(row['arrival_time']),
                vehicle_to_stop_distance_m=float(row['vehicle_to_stop_distance_m']),
                speed_kph=float(row['speed_kph']),
                model_version=row['model_version']
            )
            session.add(eta)
            count += 1
        session.commit()
    print(f"Imported {count} ETA predictions")

def import_load_predictions(session, csv_path):
    print(f"Importing load predictions from {csv_path}...")
    session.query(LoadPrediction).delete()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            load = LoadPrediction(
                vehicle_id=int(row['vehicle_id']) if row['vehicle_id'] else None,
                line_id=int(row['line_id']),
                station_id=int(row['station_id']),
                predicted_load_level=row['predicted_load_level'],
                load_score=float(row['load_score']),
                predicted_load_rate=float(row['predicted_load_rate']),
                onboard_count=int(row['onboard_count']) if row['onboard_count'] else None,
                capacity=int(row['capacity']) if row['capacity'] else None,
                confidence=float(row['confidence']),
                model_version=row['model_version']
            )
            session.add(load)
            count += 1
        session.commit()
    print(f"Imported {count} load predictions")

def import_all_data(data_dir):
    session = get_session()
    
    csv_files = {
        'bus_stations': 'bus_station.csv',
        'bus_lines': 'bus_line.csv',
        'line_stations': 'line_station.csv',
        'bus_vehicles': 'bus_vehicle.csv',
        'passenger_flow': 'passenger_flow_trend.csv',
        'eta_predictions': 'eta_prediction.csv',
        'load_predictions': 'load_prediction.csv'
    }
    
    import_functions = {
        'bus_stations': import_bus_stations,
        'bus_lines': import_bus_lines,
        'line_stations': import_line_stations,
        'bus_vehicles': import_bus_vehicles,
        'passenger_flow': import_passenger_flow_trend,
        'eta_predictions': import_eta_predictions,
        'load_predictions': import_load_predictions
    }
    
    for key, filename in csv_files.items():
        csv_path = os.path.join(data_dir, filename)
        if os.path.exists(csv_path):
            import_functions[key](session, csv_path)
        else:
            print(f"Warning: {csv_path} not found, skipping...")
    
    session.close()
    print("All data import completed!")

if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    
    import_all_data(data_dir)