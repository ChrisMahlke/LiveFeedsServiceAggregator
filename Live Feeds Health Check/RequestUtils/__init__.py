""" """
import arcgis
import dump as dump
import json
import re
import requests
import threading
from requests import Session
from RetryUtils import retry
from RetryUtils import get_retry_output
from urllib.parse import urlencode


# debugging flag
DEBUG = False

# TODO: Remove strings
ERROR_CODES = {
    "HTTPError": {
        "message": "An HTTP error occurred"
    },
    "ConnectionError": {
        "message": "A Connection error occurred"
    },
    "Timeout": {
        "message": "The request timed out"
    },
    "RequestException": {
        "message": "There was an ambiguous exception that occurred while handling your request"
    },
    "InvalidURL": {
        "message": "The URL provided was somehow invalid"
    }
}


def _format_url(url):
    """
    Format a urls protocol
    :param url:
    :return:
    """
    if not re.match('(?:http|ftp|https)://', url):
        return 'https://{}'.format(url)
    return url


def check_request(path: str = "", params=None, **kwargs) -> dict:
    """
    Make a request and return a dictionary indicating success, failure, and the response object
    :param path:
    :param params:
    :param kwargs:
    :return:
    """
    if params is None:
        params = {}
    path = _format_url(path)

    item_id = kwargs.pop("id", False)
    try_json = kwargs.pop("try_json", False)
    add_token = kwargs.pop('add_token', False)
    retry_factor = kwargs.pop('retry_factor', False)
    timeout_factor = kwargs.pop('timeout_factor', False)
    token = kwargs.pop('token', False)

    # default retry count if none is specified in the config file
    retries = 5
    # retry count
    if retry_factor:
        retries = int(retry_factor)

    # default timeout (in seconds) if none is specified in the config file
    timeout = 5
    # timeout (in seconds)
    if timeout_factor:
        timeout = int(timeout_factor)

    if try_json:
        params['f'] = 'json'

    if add_token:
        params['token'] = token

    if try_json or add_token:
        base_url = path + "?"
    else:
        base_url = path
    url = base_url + urlencode(params)

    response_dict = {}
    response_dict.setdefault("error_message", [])
    response_dict.setdefault("success", False)
    response_dict.setdefault("response", {})
    response_dict.setdefault("retryCount", {})

    try:
        print(f"\nChecking URL: {url}")
        print(f"--- parameters (RequestUtils) ---")
        print(f"retry: {retries}")
        print(f"timeout: {timeout}\n")
        # The Session object allows you to persist certain parameters across requests.
        # It also persists cookies across all requests made from the Session instance
        session = requests.Session()
        current_session = retry(session, retries=retries, backoff_factor=0.2, id=item_id, timeout=timeout)
        response = current_session.get(url, timeout=timeout)
    except requests.exceptions.HTTPError as http_error:
        response_dict["error_message"].append(ERROR_CODES["HTTPError"])
        response_dict["error_message"].append(http_error)
    #except requests.exceptions.ConnectionError as connection_error:
    #    response_dict["error_message"].append(ERROR_CODES["ConnectionError"])
    #    response_dict["error_message"].append(connection_error)
    except requests.exceptions.Timeout as timeout_error:
        response_dict["error_message"].append(ERROR_CODES["Timeout"])
        response_dict["error_message"].append(timeout_error)
    except requests.exceptions.RequestException as request_exception_error:
        response_dict["error_message"].append(ERROR_CODES["RequestException"])
        response_dict["error_message"].append(request_exception_error)
    except requests.exceptions.InvalidURL as invalid_url_error:
        response_dict["error_message"].append(ERROR_CODES["InvalidURL"])
        response_dict["error_message"].append(invalid_url_error)
    else:
        response_dict["success"] = True
        response_dict["response"] = response
        if DEBUG:
            data = dump.dump_response(response)
            print(data.decode('utf-8'))
            print("------------------------------------------------------------------\n")
    finally:
        tmp_retry_output = get_retry_output()
        retry_count = {}
        for rc in tmp_retry_output:
            if rc["id"] == item_id:
                retry_count = rc
        response_dict["retryCount"] = retry_count
        if DEBUG:
            print(f"URL {response_dict}")

        # print error messages that were captured from above
        if len(response_dict['error_message']) > 0:
            print(f"ERRORS: {response_dict['error_message']}")
        return response_dict
