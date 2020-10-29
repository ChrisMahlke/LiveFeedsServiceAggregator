""" """
import arcgis
import concurrent.futures
import dump as dump
import json
import re
import requests
import threading
from requests import Session
from RetryUtils import retry
from RetryUtils import get_retry_output
from urllib.parse import urlencode

VERSION = "1.0.0"

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
    if not re.match('(?:http|ftp|https)://', url):
        return 'https://{}'.format(url)
    return url


def check_request(path: str = "", params=None, **kwargs) -> dict:
    """ 
    Make a request and return a dictionary indicating
    success, failure, and the response object
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

    # default retry count if none is specified
    retries = 5
    # retry count
    if retry_factor:
        retries = int(retry_factor)

    # default timeout (in seconds) if none is specified
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
        session = requests.Session()
        current_session = retry(session, retries=retries, backoff_factor=0.2, id=item_id)
        response = current_session.get(url, timeout=timeout)
    except requests.exceptions.HTTPError as http_error:
        response_dict["error_message"].append(ERROR_CODES["HTTPError"])
        response_dict["error_message"].append(http_error)
    except requests.exceptions.ConnectionError as connection_error:
        response_dict["error_message"].append(ERROR_CODES["ConnectionError"])
        response_dict["error_message"].append(connection_error)
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
        return response_dict


def validate_service_urls(items=None) -> list:
    # The ThreadPoolExecutor manages a set of worker threads, passing tasks to
    # them as they become available for more work.
    if items is None:
        items = []
    print("Validating Services")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(items)) as executor:
        # map() is used to concurrently produce a set of results from an input iterable.
        generator = executor.map(_validate_service_url, items)
        return list(generator)


def _validate_service_url(item=None) -> dict:
    """ Check that the Item's url is valid """
    if item is None:
        item = {}
    response = check_request(path=item["queryParams"]["url"],
                             params=item["queryParams"]["params"],
                             try_json=item["queryParams"]["tryJson"],
                             add_token=item["queryParams"]["addToken"],
                             retry_factor=item["queryParams"]["retryFactor"],
                             timeout_factor=item["queryParams"]["timeoutFactor"],
                             token=item["queryParams"]["token"],
                             id=item["id"])
    print(f"{item['id']}")
    return {
        "itemResponse": item,
        "serviceResponse": response
    }


def check_layer_urls(input_items=None) -> list:
    """ 
    Check the layers of the service
    """
    if input_items is None:
        input_items = []
    if len(input_items) > 0:
        # The ThreadPoolExecutor manages a set of worker threads, passing tasks to
        # them as they become available for more work.
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(input_items)) as executor:
            # map() is used to concurrently produce a set of results from an input iterable.
            generator = executor.map(_check_layer_url, input_items)
            return list(generator)


def _check_layer_url(layer=None) -> dict:
    """ Check that the Item's url is valid """
    if layer is None:
        layer = {}
    response = {
        "id": layer["id"],
        "success": False
    }
    if layer["success"]:
        url = layer["url"]
        print(f"Checking layer: {layer['layerName']}")
        response = check_request(path=url,
                                 params=layer['params'],
                                 try_json=layer['try_json'],
                                 add_token=layer['add_token'],
                                 retry_factor=5,
                                 timeout_factor=5,
                                 id=layer["id"],
                                 token=layer['token'])
    return {
        "item": input,
        "response": response
    }


def validate_usage_details(items: list) -> list:
    """ Retrieve the usage details for all valid items """
    print("Validating Usage details")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(items)) as executor:
        generator = executor.map(_get_item_usage_details, items)
        results = list(generator)
        return results


def _get_item_usage_details(input_item=None) -> dict:
    """ Usage details show how many times the item has been used for the time period you select. """
    # Only check the items that are valid
    if input_item is None:
        input_item = {}
    item_response = input_item["itemResponse"]
    item_id = item_response["id"]
    if item_response["isItemValid"]["success"]:
        agol_item = item_response["agolItem"]
        try:
            usage = agol_item.usage(date_range=item_response["usageParams"]["usageDataRange"], as_df=False)
        except TypeError:
            print(f"ERROR: (TypeError) Unable to retrieve usage details on: {item_id}")
            return {
                "itemResponse": input_item["itemResponse"],
                "serviceResponse": input_item["serviceResponse"],
                "usageResponse": {
                    "usage": {
                        "data": []
                    },
                    "itemHasUsageDetails": {
                        "success": False,
                        "error": "ERROR: (TypeError) Unable to retrieve usage details on: {itemId}"
                    }
                }
            }
        except IndexError:
            print(f"ERROR: (IndexError) Unable to retrieve usage details on: {item_id}")
            return {
                "itemResponse": input_item["itemResponse"],
                "serviceResponse": input_item["serviceResponse"],
                "usageResponse": {
                    "usage": {
                        "data": []
                    },
                    "itemHasUsageDetails": {
                        "success": False,
                        "error": "ERROR: (Index) Unable to retrieve usage details on: {itemId}"
                    }
                }
            }
        else:
            print(f"Usage details retrieved on: {item_id}\t{agol_item['title']}")
            return {
                "itemResponse": input_item["itemResponse"],
                "serviceResponse": input_item["serviceResponse"],
                "usageResponse": {
                    "usage": usage,
                    "itemHasUsageDetails": {
                        "success": True
                    }
                }
            }
    else:
        print(f"Usage details NOT retrieved on: {item_id}")
        return {
            "itemResponse": input_item["itemResponse"],
            "serviceResponse": input_item["serviceResponse"],
            "usageResponse": {
                "usage": {
                    "data": []
                },
                "itemHasUsageDetails": {
                    "success": False,
                    "error": "Unable to retrieve usage details on: {itemId}"
                }
            }
        }


def get_alfp_content(input_items=None) -> list:
    """ """
    if input_items is None:
        input_items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(input_items)) as executor:
        # map() is used to concurrently produce a set of results from an input iterable.
        generator = executor.map(check_alfp_url, input_items)
        return list(generator)


def check_alfp_url(input_data=None) -> dict:
    """ """
    if input_data is None:
        input_data = {}
    response = check_request(path=input_data["url"],
                             params=input_data['params'],
                             try_json=input_data['try_json'],
                             add_token=input_data['add_token'],
                             retry_factor=input_data['retry_factor'],
                             timeout_factor=input_data['timeout_factor'],
                             token=input_data['token'],
                             id=input_data["id"])
    return {
        "id": input_data["id"],
        "response": response
    }


def get_all_feature_counts(input_layer_data=None) -> list:
    """ Iterate through the list of layers for each item and check the response """
    if input_layer_data is None:
        input_layer_data = []
    print("\n\n============ Getting Feature Counts")
    result_counts = []
    for layer in input_layer_data:
        # current item ID
        current_item_id = layer[0]["id"]
        # reset the total feature count for this service
        current_item_feature_count = 0
        # Query the list of layers of the current item in the iteration
        # and return the feature counts
        validated_layers = check_layer_urls(layer)
        if validated_layers is not None:
            for validatedLayer in validated_layers:
                if validatedLayer["response"]["success"]:
                    # print(f"Elapsed time: {validated_layer['response']['response'].elapsed}")
                    count_dict = json.loads(validatedLayer["response"]["response"].content.decode('utf-8'))
                    current_item_feature_count += count_dict["count"]
        print(f"currentItemFeatureCount: {current_item_id}\t{current_item_feature_count}\n")
        result_counts.append({
            "id": current_item_id,
            "featureCount": current_item_feature_count
        })
    return result_counts


def prepare_alfp_query_params(input_data=None) -> dict:
    if input_data is None:
        input_data = {}
    item_id = input_data["id"]
    return {
        "id": item_id,
        "url": f"https://livefeedsdev.s3.amazonaws.com/Heartbeat/{item_id}.json",
        "try_json": False,
        "add_token": False,
        "params": {},
        "token": "",
        "timeout_factor": 5,
        "retry_factor": 5
    }
