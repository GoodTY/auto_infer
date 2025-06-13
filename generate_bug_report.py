#!/usr/bin/env python3

import json
import sys
import os
from pathlib import Path
from datetime import datetime

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

def get_bug_trace(bug):
    """
    Extract bug trace from bug report
    """
    try:
        trace = bug.get('bug_trace', [])
        if not trace:
            return []
            
        # 버그 트레이스의 모든 라인 번호를 수집
        trace_lines = [entry.get('line_number', 0) for entry in trace]
        
        return [{
            'line_number': entry.get('line_number', 0),
            'description': entry.get('description', '')
        } for entry in trace]
    except Exception as e:
        print(f"Error extracting bug trace: {str(e)}")
        return []

def get_buggy_lines(bug, method_start_line, method_end_line):
    """
    Extract start and end lines of the bug from bug trace, ensuring they are within method bounds
    """
    if 'bug_trace' in bug and bug['bug_trace']:
        start_line = bug['bug_trace'][0].get('line_number', 0)
        end_line = bug['bug_trace'][-1].get('line_number', 0)
        
        # Ensure bug lines are within method bounds
        start_line = max(start_line, method_start_line)
        end_line = min(end_line, method_end_line)
        
        return start_line, end_line
    return method_start_line, method_start_line  # Default to method start if no trace

def get_method_code(file_path, method_name, bug_line):
    """
    Get the actual method code from the source file
    """
    try:
        if not os.path.exists(file_path):
            return "File not found"
            
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Find method start by looking for method declaration
        start_line = -1
        for i in range(len(lines)):
            if method_name in lines[i] and '(' in lines[i]:
                start_line = i
                break
                
        if start_line == -1:
            return "Method not found"
            
        # Extract method code
        method_code = []
        brace_count = 0
        end_line = start_line
        
        for i in range(start_line, len(lines)):
            line = lines[i]
            method_code.append(line)
            
            # Count braces to find method end
            brace_count += line.count('{') - line.count('}')
            if brace_count == 0 and i > start_line:
                end_line = i
                break
                
        # Verify bug line is within method
        if bug_line < start_line or bug_line > end_line:
            return f"Bug line {bug_line} is outside method range ({start_line}-{end_line})"
            
        return {
            'code': ''.join(method_code),
            'start_line': start_line + 1,  # Convert to 1-based index
            'end_line': end_line + 1,      # Convert to 1-based index
            'bug_line': bug_line
        }
        
    except Exception as e:
        return f"Error extracting code: {str(e)}"

def convert_json_to_json(project_path, output_dir):
    """
    Convert Infer JSON bug report to our JSON format
    """
    try:
        # Try to find report.json first
        report_json = os.path.join(project_path, "infer-out", "report.json")
        
        # If report.json doesn't exist, look for batch_summary_*.json in infer-results
        if not os.path.exists(report_json):
            infer_results_dir = os.path.join(os.path.dirname(project_path), "..", "infer-results")
            if os.path.exists(infer_results_dir):
                batch_files = [f for f in os.listdir(infer_results_dir) if f.startswith("batch_summary_")]
                if batch_files:
                    report_json = os.path.join(infer_results_dir, batch_files[0])
                    print(f"Using batch summary file: {report_json}")
                else:
                    print(f"Warning: No report.json or batch summary found for {project_path}")
                    return False
            else:
                print(f"Warning: No report.json found in {project_path}/infer-out")
                return False

        # Read JSON file
        with open(report_json, 'r', encoding='utf-8') as f:
            bug_reports = json.load(f)

        # If it's a batch summary file, extract the relevant project's bugs
        if "batch_summary" in report_json:
            project_name = os.path.basename(project_path)
            bug_reports = [bug for bug in bug_reports if bug.get('project') == project_path]
            if not bug_reports:
                print(f"No bugs found for project {project_name} in batch summary")
                return False

        # Get project name from directory name
        project_name = os.path.basename(project_path)
        
        # Create project-specific directory
        project_dir = os.path.join(output_dir, project_name)
        os.makedirs(project_dir, exist_ok=True)

        # Create output JSON file path
        output_file = os.path.join(project_dir, f"{project_name}_bugs.json")

        # Process each bug report
        processed_bugs = []
        for bug in bug_reports:
            # Skip bugs in test files
            file_path = bug.get('file', '')
            if 'test' in file_path.lower():
                continue
                
            method_name = extract_method_name(bug.get('procedure', ''))
            bug_line = bug.get('line', 0)
            
            # Get method code first to determine method bounds
            method_info = get_method_code(
                os.path.join(project_path, file_path),
                method_name,
                bug_line
            )
            
            if isinstance(method_info, str):  # Error occurred
                print(f"Warning: {method_info} in {file_path}")
                continue

            # Get bug trace
            bug_trace = get_bug_trace(bug)
            
            # Calculate relative bug lines
            method_start = method_info['start_line']
            method_end = method_info['end_line']
            
            # bug_start_line은 line_number 그대로 사용
            bug_start = bug_line
            
            # bug_end_line은 method_end_line보다 작거나 같은 bug_trace 라인들 중 가장 큰 값
            if bug_trace:
                trace_lines = [entry['line_number'] for entry in bug_trace]
                bug_end = max(line for line in trace_lines if line <= method_end)
            else:
                bug_end = bug_start
                
            processed_bug = {
                'project': project_name,
                'bug_id': f"{project_name}-{len(processed_bugs) + 1}",
                'file': file_path,
                'method': method_name,
                'bug_type': bug.get('bug_type', ''),
                'description': bug.get('qualifier', ''),
                'line_number': bug_line,
                'method_start_line': method_start,
                'method_end_line': method_end,
                'bug_start_line': bug_start,
                'bug_end_line': bug_end,
                'severity': bug.get('severity', ''),
                'method_code': method_info['code'],
                'bug_trace': bug_trace
            }
            processed_bugs.append(processed_bug)

        # Write to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_bugs, f, indent=2, ensure_ascii=False)

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
    # Delete output directory if it exists
    if os.path.exists(output_dir):
        print(f"Removing existing output directory: {output_dir}")
        import shutil
        shutil.rmtree(output_dir)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get all subdirectories (projects)
    projects = [d for d in os.listdir(projects_dir) 
               if os.path.isdir(os.path.join(projects_dir, d))]

    if not projects:
        print(f"No projects found in {projects_dir}")
        return False

    success_count = 0
    all_bugs = []
    
    for project in projects:
        project_path = os.path.join(projects_dir, project)
        if convert_json_to_json(project_path, output_dir):
            success_count += 1
            
            # Read the project's bugs and add to all_bugs
            project_bugs_file = os.path.join(output_dir, project, f"{project}_bugs.json")
            if os.path.exists(project_bugs_file):
                with open(project_bugs_file, 'r', encoding='utf-8') as f:
                    all_bugs.extend(json.load(f))

    # Save all bugs to a single file
    if all_bugs:
        all_bugs_file = os.path.join(output_dir, "all_bugs.json")
        with open(all_bugs_file, 'w', encoding='utf-8') as f:
            json.dump(all_bugs, f, indent=2, ensure_ascii=False)
        print(f"\nSaved all {len(all_bugs)} bugs to {all_bugs_file}")

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