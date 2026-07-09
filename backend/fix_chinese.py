import os
import re

chinese_to_english = {
    "Username already exists": "Username already exists",
    "Username or password error": "Username or password error",
    "Old password error": "Old password error",
    "Line code already exists": "Line code already exists",
    "Station code already exists": "Station code already exists",
    "Line not found": "Line not found",
    "Station not found": "Station not found",
    "Station already in line": "Station already in line",
    "explain mode requires route_id or context": "explain mode requires route_id or context",
    "Get success": "Get success",
    "Create success": "Create success",
    "Update success": "Update success",
    "Delete success": "Delete success",
    "Add success": "Add success",
    "Remove success": "Remove success",
    "Bad request": "Bad request",
    "Unauthorized": "Unauthorized",
    "Reserved field, not implemented yet": "Reserved field, not implemented yet",
    "Create new line": "Create new line",
    "Update line info": "Update line info",
    "Delete line": "Delete line",
    "Get line stations (ordered)": "Get line stations (ordered)",
    "Add station to line": "Add station to line",
    "Update line station relation (order, direction)": "Update line station relation (order, direction)",
    "Remove station from line": "Remove station from line",
    "Get station list with pagination and search": "Get station list with pagination and search",
    "Get station by ID": "Get station by ID",
    "Create new station": "Create new station",
    "Update station info": "Update station info",
    "Delete station": "Delete station",
    "Get nearby stations (sorted by distance)": "Get nearby stations (sorted by distance)",
    "Get lines for station": "Get lines for station",
    "Get all stations with coordinates": "Get all stations with coordinates",
    "User Register": "User Register",
    "User Login": "User Login",
    "Get Current User": "Get Current User",
    "Update Current User": "Update Current User",
    "Get User Query History": "Get User Query History",
    "Lines": "Lines",
    "Stations": "Stations",
    "User": "User",
    "Health Check": "Health Check"
}

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='latin-1') as f:
            content = f.read()
        
        modified = False
        for chinese, english in chinese_to_english.items():
            if chinese in content:
                content = content.replace(chinese, english)
                modified = True
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {filepath}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def main():
    root_dir = '.'
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                fix_file(filepath)

if __name__ == '__main__':
    main()