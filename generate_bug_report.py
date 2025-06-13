#!/usr/bin/env python3

import json
import csv
import sys
import os
from pathlib import Path

def extract_method_name(procedure):
    """
    Extract method name from procedure string
    Example: "org.jsoup.helper.CookieUtil.parseCookie(java.lang.String,org.jsoup.helper.HttpConnection$Response):void"
    Returns: "parseCookie"
    """
    if not procedure:
        return ""
    # Split by '(' and take the last part before that
    method_part = procedure.split('(')[0]
    # Split by '.' and take the last part
    return method_part.split('.')[-1]

def get_method_code(file_path, method_name, line_number):
    """
    Get the actual method code from the source file
    """
    try:
        if not os.path.exists(file_path):
            return "File not found"
            
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Find method start
        start_line = max(0, line_number - 1)  # Convert to 0-based index
        method_code = []
        brace_count = 0
        found_method = False
        
        # Look for method declaration
        for i in range(start_line, -1, -1):
            if method_name in lines[i] and '(' in lines[i]:
                start_line = i
                found_method = True
                break
                
        if not found_method:
            return "Method not found"
            
        # Extract method code
        for i in range(start_line, len(lines)):
            line = lines[i]
            method_code.append(line)
            
            # Count braces to find method end
            brace_count += line.count('{') - line.count('}')
            if brace_count == 0 and i > start_line:
                break
                
        return ''.join(method_code)
        
    except Exception as e:
        return f"Error extracting code: {str(e)}"

def convert_json_to_csv(project_path, output_dir):
    """
    Convert JSON bug report to CSV format from project's infer-out directory
    """
    try:
        # Construct path to report.json
        report_json = os.path.join(project_path, "infer-out", "report.json")
        
        if not os.path.exists(report_json):
            print(f"Warning: No report.json found in {project_path}/infer-out")
            return False

        # Read JSON file
        with open(report_json, 'r', encoding='utf-8') as f:
            bug_reports = json.load(f)

        # Get project name from directory name
        project_name = os.path.basename(project_path)
        
        # Create project-specific directory
        project_dir = os.path.join(output_dir, project_name)
        os.makedirs(project_dir, exist_ok=True)

        # Create output CSV file path
        output_file = os.path.join(project_dir, f"{project_name}_bugs.csv")

        # CSV header
        fieldnames = ['File', 'Method', 'Bug Type', 'Description', 'Start Line', 'End Line', 'Severity', 'Method Code']

        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            # Process each bug report
            for bug in bug_reports:
                method_name = extract_method_name(bug.get('procedure', ''))
                method_code = get_method_code(
                    os.path.join(project_path, bug.get('file', '')),
                    method_name,
                    bug.get('line', 0)
                )
                
                writer.writerow({
                    'File': bug.get('file', ''),
                    'Method': method_name,
                    'Bug Type': bug.get('bug_type', ''),
                    'Description': bug.get('qualifier', ''),
                    'Start Line': bug.get('line', ''),
                    'End Line': bug.get('procedure_start_line', ''),
                    'Severity': bug.get('severity', ''),
                    'Method Code': method_code.replace('\n', '\\n')  # Escape newlines for CSV
                })

        print(f"Successfully converted {report_json} to {output_file}")
        return True

    except FileNotFoundError:
        print(f"Error: Input file '{report_json}' not found")
        return False
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{report_json}'")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def process_all_projects(projects_dir, output_dir):
    """
    Process all projects in the given directory
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get all subdirectories (projects)
    projects = [d for d in os.listdir(projects_dir) 
               if os.path.isdir(os.path.join(projects_dir, d))]

    if not projects:
        print(f"No projects found in {projects_dir}")
        return False

    success_count = 0
    for project in projects:
        project_path = os.path.join(projects_dir, project)
        if convert_json_to_csv(project_path, output_dir):
            success_count += 1

    print(f"\nProcessed {len(projects)} projects, {success_count} successful conversions")
    return success_count > 0

def main():
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python generate_bug_report.py <projects_directory> <output_directory>")
        print("Example: python generate_bug_report.py github-trends/java bug-reports")
        sys.exit(1)
    
    projects_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    # Process all projects
    if not process_all_projects(projects_dir, output_dir):
        sys.exit(1)

if __name__ == "__main__":
    main() 