"How many weeks has it been since Paul retired??"

from datetime import datetime


def weeks_without_paul(file):
    "How many weeks has it been since Paul retired??"
    pauls_retirement= datetime(2025,3,20)
    time_diff= datetime.now() - pauls_retirement
    weeks_without_paul= time_diff.days // 7

    # Write to file
    print(f"   - Weeks without Paul: {weeks_without_paul}\n")
    file.write(f"  - Weeks without Paul: {weeks_without_paul}\n")
