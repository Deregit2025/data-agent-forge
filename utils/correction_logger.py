import os
import datetime

def log_correction(failed_query: str, what_was_wrong: str, correct_approach: str, log_file_path: str = '../kb/corrections/corrections_log.md') -> bool:
    """
    Called by the Agent Driver when a systemic failure occurs that requires a new rule.
    Appends a formatted string to the corrections_log.md file matching the KB v3 requirement.
    
    Args:
        failed_query: The exact user query or SQL statement that failed.
        what_was_wrong: Diagnosis of why the failure occurred (e.g. wrong column name).
        correct_approach: Explicit instruction to avoid the failure next time.
        log_file_path: Relative or absolute path to the corrections log file.
    
    Returns:
        bool: True if logged successfully.
    """
    
    # Resolve absolute path based on this location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(base_dir, log_file_path)
    
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Format according to the challenge requirements: [query that failed] -> [what was wrong] -> [correct approach]
    formatted_log = f"\n- **[{timestamp}]** `[{failed_query}]` → `[{what_was_wrong}]` → `[{correct_approach}]`"
    
    try:
        with open(target_path, 'a') as f:
            f.write(formatted_log)
        print(f"✅ Successfully wrote correction entry to {target_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to write to corrections log: {e}")
        return False

if __name__ == "__main__":
    # Test the logger
    log_correction(
        failed_query="SELECT _id FROM business",
        what_was_wrong="Joined on MongoDB internal _id instead of string business_id",
        correct_approach="Always use business_id as a string when joining businessinfo_database against DuckDB's business_ref"
    )