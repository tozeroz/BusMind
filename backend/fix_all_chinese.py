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
    "tests/test_ai_service.py"
]

def fix_chinese_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
            content = f.read()
        
        content = content.replace('不应超过', 'should not exceed')
        content = content.replace('至少提供一个', 'at least one of')
        content = content.replace('必须提供', 'must provide')
        content = content.replace('预留字段', 'reserved field')
        content = content.replace('当前未实现', 'not implemented')
        content = content.replace('起终点站', 'start/end stations')
        content = content.replace('推荐结果', 'recommendation result')
        content = content.replace('�', '')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def main():
    for filepath in files_to_fix:
        fix_chinese_in_file(filepath)

if __name__ == '__main__':
    main()