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


def _format_url(url):
    """
    Format a url's protocol
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

