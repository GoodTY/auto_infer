#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path

def convert_bug_reports_to_java_files(bug_reports_dir, output_dir):
    """
    Convert bug report method codes into individual Java files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each project's bug report
    for project_dir in os.listdir(bug_reports_dir):
        project_path = os.path.join(bug_reports_dir, project_dir)
        if not os.path.isdir(project_path):
            continue
            
        # Find the bug report JSON file
        bug_report = None
        for file in os.listdir(project_path):
            if file.endswith('_bugs.json'):
                bug_report = os.path.join(project_path, file)
                break
                
        if not bug_report:
            print(f"No bug report found in {project_path}")
            continue
            
        # Read and process the bug report
        with open(bug_report, 'r', encoding='utf-8') as f:
            bugs = json.load(f)
            
        for bug in bugs:
            bug_id = bug['bug_id']
            method_code = bug['method_code']
            
            # Remove leading whitespace from each line
            lines = method_code.split('\n')
            min_indent = float('inf')
            for line in lines:
                if line.strip():  # Skip empty lines
                    indent = len(line) - len(line.lstrip())
                    min_indent = min(min_indent, indent)
            
            # Remove the minimum indent from all lines
            cleaned_lines = []
            for line in lines:
                if line.strip():  # Non-empty line
                    cleaned_lines.append(line[min_indent:])
                else:  # Empty line
                    cleaned_lines.append('')
            
            method_code = '\n'.join(cleaned_lines)
            
            # Create bug-specific directory
            bug_dir = os.path.join(output_dir, bug_id)
            os.makedirs(bug_dir, exist_ok=True)
            
            # Create Java file with method code
            java_file = os.path.join(bug_dir, f"{bug_id}_original_method.java")
            with open(java_file, 'w', encoding='utf-8') as f:
                f.write(method_code)
                
            print(f"Created {java_file}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python convert_to_java_files.py <bug_reports_directory> <output_directory>")
        print("Example: python convert_to_java_files.py bug-reports trans_VJBench")
        sys.exit(1)
        
    bug_reports_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    convert_bug_reports_to_java_files(bug_reports_dir, output_dir)

if __name__ == "__main__":
    main() 