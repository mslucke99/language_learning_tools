"""
Dart Model Generator
-------------------
Reads the local SQLite database schema and generates Dart data classes
for the Flutter application.

Usage:
    python src/tools/generate_dart_models.py
"""

import sqlite3
import os

DB_PATH = "flashcards.db"
OUTPUT_FILE = "models.dart"

# Tables to generate models for
TARGET_TABLES = [
    "decks", 
    "flashcards", 
    "imported_content", 
    "word_definitions", 
    "sentence_explanations",
    "grammar_book_entries",
    "pending_sync_actions"
]

# Type mapping: SQLite -> Dart
TYPE_MAP = {
    "INTEGER": "int",
    "TEXT": "String",
    "REAL": "double",
    "BLOB": "Uint8List",
    "NULL": "dynamic"
}

def to_camel_case(snake_str):
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def to_pascal_case(snake_str):
    """Convert snake_case to PascalCase."""
    return snake_str.replace("_", " ").title().replace(" ", "")

def get_dart_type(col_type, is_nullable):
    """Map SQLite type to Dart type."""
    base_type = TYPE_MAP.get(col_type.upper(), "String") # Default to String for unknowns
    if is_nullable and base_type != "dynamic":
        return f"{base_type}?"
    return base_type

def generate_model(table_name, columns):
    class_name = to_pascal_case(table_name)
    # Singulize (simple heuristic)
    if class_name.endswith("s"):
        class_name = class_name[:-1]
    if class_name.endswith("ie"): # entries -> entry
        class_name = class_name[:-2] + "y"
        
    dart_code = f"class {class_name} {{\n"
    
    # Fields
    for col in columns:
        name = col['name']
        dtype = get_dart_type(col['type'], not col['notnull'])
        camel_name = to_camel_case(name)
        dart_code += f"  final {dtype} {camel_name};\n"
        
    dart_code += "\n"
    
    # Constructor
    dart_code += f"  {class_name}({{\n"
    for col in columns:
        name = col['name']
        camel_name = to_camel_case(name)
        required = "required " if col['notnull'] else ""
        dart_code += f"    {required}this.{camel_name},\n"
    dart_code += "  });\n\n"
    
    # fromJson
    dart_code += f"  factory {class_name}.fromJson(Map<String, dynamic> json) {{\n"
    dart_code += f"    return {class_name}(\n"
    for col in columns:
        name = col['name']
        camel_name = to_camel_case(name)
        dtype = get_dart_type(col['type'], not col['notnull'])
        
        # Helper for int conversion (JSON sometimes sends ints as doubles or strings)
        json_access = f"json['{name}']"
        
        dart_code += f"      {camel_name}: {json_access},\n"
    dart_code += "    );\n"
    dart_code += "  }\n\n"
    
    # toJson
    dart_code += "  Map<String, dynamic> toJson() => {\n"
    for col in columns:
        name = col['name']
        camel_name = to_camel_case(name)
        dart_code += f"        '{name}': {camel_name},\n"
    dart_code += "      };\n"
    
    dart_code += "}\n\n"
    return dart_code

def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    full_output = "// GENERATED CODE - DO NOT MODIFY BY HAND\n\n"
    
    for table in TARGET_TABLES:
        print(f"Processing {table}...")
        try:
            cursor.execute(f"PRAGMA table_info({table})")
            rows = cursor.fetchall()
            if not rows:
                print(f"  Warning: Table {table} not found or empty.")
                continue
                
            columns = []
            for row in rows:
                # row structure: (cid, name, type, notnull, dflt_value, pk)
                col_type = row[2]
                # Fix for SQLite sometimes returning 'INTEGER' and sometimes 'INT' etc
                if 'INT' in col_type.upper(): col_type = 'INTEGER'
                if 'CHAR' in col_type.upper() or 'TEXT' in col_type.upper(): col_type = 'TEXT'
                if 'REAL' in col_type.upper() or 'FLOA' in col_type.upper() or 'DOUB' in col_type.upper(): col_type = 'REAL'
                
                columns.append({
                    'name': row[1],
                    'type': col_type,
                    'notnull': row[3] == 1
                })
                
            full_output += generate_model(table, columns)
            
        except Exception as e:
            print(f"Error generating {table}: {e}")

    with open(OUTPUT_FILE, "w") as f:
        f.write(full_output)
    
    print(f"Successfully generated {OUTPUT_FILE}")
    conn.close()

if __name__ == "__main__":
    main()
