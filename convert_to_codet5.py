#!/usr/bin/env python3

import os
import json
import re
from pathlib import Path

def calculate_relative_line(bug_line, method_start_line):
    """
    Calculate the relative line number within the method
    by subtracting method_start_line from the bug line number
    """
    return bug_line - method_start_line + 1  # Add 1 to make it 1-based index

def create_buggyline_location(bug_info, output_dir):
    """
    Create buggyline_location.json file with vulnerability location information
    in VJBench-trans format
    """
    # Calculate relative line numbers
    bug_line = bug_info["line_number"]
    method_start_line = bug_info["method_start_line"]
    relative_bug_line = calculate_relative_line(bug_line, method_start_line)
    
    # Calculate end line (use bug_end_line if available, otherwise use bug_line)
    bug_end_line = bug_info.get("bug_end_line", bug_line)
    relative_bug_end_line = calculate_relative_line(bug_end_line, method_start_line)
    
    location_info = {
        "original": [
            [relative_bug_line, relative_bug_end_line]
        ],
        "rename_only": [
            [relative_bug_line, relative_bug_end_line]
        ],
        "structure_change_only": [
            [relative_bug_line, relative_bug_end_line]
        ],
        "rename+code_structure": [
            [relative_bug_line, relative_bug_end_line]
        ]
    }
    
    # Create bug_id directory
    bug_dir = os.path.join(output_dir, bug_info["bug_id"])
    os.makedirs(bug_dir, exist_ok=True)
    
    # Save to JSON file
    output_file = os.path.join(bug_dir, "buggyline_location.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(location_info, f, indent=4, ensure_ascii=False)
    
    return output_file

def save_original_method(bug_info, output_dir):
    """
    Save the original method code to a Java file
    """
    # Create bug_id directory
    bug_dir = os.path.join(output_dir, bug_info["bug_id"])
    os.makedirs(bug_dir, exist_ok=True)
    
    # Create Java file with original method
    output_file = os.path.join(bug_dir, f"{bug_info['bug_id']}_original_method.java")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(bug_info["method_code"])
    
    return output_file

def convert_to_codet5(input_file, output_dir):
    """
    Convert bug report to VJBench-trans format files
    """
    try:
        # Read input JSON file
        with open(input_file, 'r', encoding='utf-8') as f:
            bug_reports = json.load(f)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Process each bug report
        for bug in bug_reports:
            # Create bug_id directory
            bug_dir = os.path.join(output_dir, bug["bug_id"])
            os.makedirs(bug_dir, exist_ok=True)
            
            # Create buggyline_location.json
            location_file = create_buggyline_location(bug, output_dir)
            print(f"Created {location_file}")
            
            # Save original method
            method_file = save_original_method(bug, output_dir)
            print(f"Created {method_file}")
            
        print(f"Successfully converted {len(bug_reports)} bug reports")
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python convert_to_codet5.py <input_json> <output_directory>")
        print("Example: python convert_to_codet5.py bug-reports/all_bugs.json codet5-output")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not convert_to_codet5(input_file, output_dir):
        sys.exit(1)

if __name__ == "__main__":
    main() 