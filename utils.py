from datetime import datetime
import dateparser

def extract_and_convert_datetime(text):
    # Parse the input text using dateparser
    parsed_datetime = dateparser.parse(text, settings={'RELATIVE_BASE': datetime.now()})
    
    # Debugging: print the raw parsed datetime
    print(f"Parsed datetime (raw): {parsed_datetime}")
    
    # If a valid datetime is parsed, return the formatted date
    if parsed_datetime:
        return parsed_datetime.strftime('%Y-%m-%d %H:%M')
    else:
        return "No valid date or time found"

# Test cases with both absolute and relative dates
examples = [
    "The meeting is on January 1, 2024 at 3 PM.",
    "Let's catch up next Friday at 10:30 AM.",
    "It happened yesterday at 5 PM.",
    "We met on March 5th, 2023 at 14:30."
]

# Print the results
for text in examples:
    print(f"Input: {text}")
    print(f"Output: {extract_and_convert_datetime(text)}")
    print("---")
