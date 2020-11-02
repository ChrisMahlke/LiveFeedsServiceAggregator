""" """
import json


def print_data(input_data):
    print(json.dumps(input_data, sort_keys=True, indent=4))


def log_portal_success(url):
    print(f"Successfully accessed: {url}")


def log_portal_error(url, err):
    print(f"There was an issue accessing: {url}\n{err}")


def log_validating_new_item(item):
    print(f"\nValidating Item ID\t{item['id']}")


def log_item_success(item):
    print(f"SUCCESS\t{item['id']}\t{item['title']}")


def log_item_fail(item):
    print(f"ERROR\t{item['id']}")


def log_status_code_details(item_id, status):
    print("\n----- Status -----")
    print(f"{item_id}")
    print(f"Code: {status['code']}")
    print(f"Service State: {status['statusDetails']['Service State']}")
    print(f"Feed State: {status['statusDetails']['Feed State']}")
    print(f"Description of Condition: {status['statusDetails']['Description of Condition']}")
    print(f"Status: {status['statusDetails']['Status']}")
    print(f"Comment: {status['statusDetails']['Comment']}")
    print(f"Notes: {status['statusDetails']['Definition/Notes']}\n")
