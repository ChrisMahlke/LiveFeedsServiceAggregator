""" """

VERSION = "1.0.0"

import json

def print_data(input_data):
    print(json.dumps(input_data, sort_keys=True, indent=4))

def log_portal_success(url):
    print(f"Successfulyl accessed: {url}")

def log_portal_error(url, err):
    print(f"There was an issue accessing: {url}\n{err}")

def log_validating_new_item(item):
    print(f"\nValidating Item ID\t{item['id']}")

def log_item_success(item):
    print(f"SUCCESS\t{item['id']}\t{item['title']}")

def log_item_fail(item):
    print(f"ERROR\t{item['id']}")

def log_status_code_details(status):
    print("\t----- Status -----")
    print(f"\tService State: {status['Service State']}")
    print(f"\tFeed State: {status['Feed State']}")
    print(f"\tDescription of Condition: {status['Description of Condition']}")
    print(f"\tStatus: {status['Status']}")
    print(f"\tComment: {status['Comment']}")
    print(f"\tNotes: {status['Definition/Notes']}")