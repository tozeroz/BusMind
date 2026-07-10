import os

files_to_fix = [
    "app/schemas/travel_experience.py",
    "app/schemas/recommendation.py",
    "app/models/bus_line.py",
    "app/models/user.py",
    "app/services/ai_service/service.py",
    "app/services/eta_service/service.py",
    "app/services/load_service/service.py",
    "app/services/recommend_service/experience_service.py",
    "app/services/recommend_service/recommendation_service.py",
    "app/services/intelligence_gateway.py",
    "app/core/config.py",
    "app/core/exception_handlers.py",
    "tests/test_ai_service.py",
    "app/schemas/ai_travel.py",
    "app/schemas/passenger_load.py"
]

def fix_binary_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        content = content.replace(b'\xe4\xb8\x8d', b'')
        content = content.replace(b'\xe5\xba\x94', b'')
        content = content.replace(b'\u00e8', b'')
        content = content.replace(b'\u00bf', b'')
        content = content.replace(b'\xe8\xb6\x85', b'')
        content = content.replace(b'\u00a1', b'')
        content = content.replace(b'\xe6\x9b\xb4', b'')
        content = content.replace(b'\xe8\x87\xb4', b'')
        content = content.replace(b'\xe6\x9c\x80', b'')
        content = content.replace(b'\xe5\xb0\x91', b'')
        content = content.replace(b'\u00e6', b'')
        content = content.replace(b'\u00b0', b'')
        content = content.replace(b'\u0091', b'')
        content = content.replace(b'\xe6\x8f\x90', b'')
        content = content.replace(b'\u00e6', b'')
        content = content.replace(b'\u008f', b'')
        content = content.replace(b'\u0090', b'')
        content = content.replace(b'\u00e4', b'')
        content = content.replace(b'\u00b8', b'')
        content = content.replace(b'\u0080', b'')
        content = content.replace(b'\xe3\x80\x81', b'')
        content = content.replace(b'\u00e3', b'')
        content = content.replace(b'\u0080', b'')
        content = content.replace(b'\u0081', b'')
        content = content.replace(b'\xc3\xa4', b'a')
        content = content.replace(b'\xc2\xb8', b'')
        content = content.replace(b'\xc2\x80', b'')
        content = content.replace(b'\xc3\xb6', b'o')
        content = content.replace(b'\xc2\xb0', b'')
        content = content.replace(b'\xc2\x91', b'')
        content = content.replace(b'\xc3\xa8', b'e')
        content = content.replace(b'\xc2\xbf', b'')
        content = content.replace(b'\xc2\xa1', b'')
        content = content.replace(b'\xe2\x80\x99', b"'")
        content = content.replace(b'\xe2\x80\x98', b"'")
        content = content.replace(b'\xe2\x80\x9c', b'"')
        content = content.replace(b'\xe2\x80\x9d', b'"')
        content = content.replace(b'\xc3\x83\xc2\xa4', b'a')
        content = content.replace(b'\xc3\x83\xc2\xb8', b'')
        content = content.replace(b'\xc3\x83\xc2\x80', b'')
        content = content.replace(b'\xc3\x83\xc2\xb6', b'o')
        content = content.replace(b'\xc3\x83\xc2\xb0', b'')
        content = content.replace(b'\xc3\x83\xc2\x91', b'')
        content = content.replace(b'\xc3\x83\xc2\xa8', b'e')
        content = content.replace(b'\xc3\x83\xc2\xbf', b'')
        content = content.replace(b'\xc3\x83\xc2\xa1', b'')
        
        try:
            text = content.decode('utf-8')
        except:
            try:
                text = content.decode('latin-1')
            except:
                text = content.decode('utf-8', errors='replace')
        
        text = text.replace('predicted_load_rate apredicted_load_level at least provide one', 'at least one of predicted_load_rate or predicted_load_level must be provided')
        text = text.replace('predicted_load_rate a', '')
        text = text.replace('predicted_load_level at least provide one', 'at least one of predicted_load_level')
        text = text.replace('must provide route_id or context', 'must provide route_id or context')
        text = text.replace('must provide start/end stations or context', 'must provide start/end stations or context')
        text = text.replace('should not exceed capacity * 2', 'should not exceed capacity * 2')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Fixed: {filepath}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def main():
    for filepath in files_to_fix:
        fix_binary_file(filepath)

if __name__ == '__main__':
    main()