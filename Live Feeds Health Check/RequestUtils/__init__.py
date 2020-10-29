""" """

VERSION = "1.0.0"

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

def formaturl(url):
    if not re.match('(?:http|ftp|https)://', url):
        return 'https://{}'.format(url)
    return url

def check_request(path: str = "", params: dict = {}, **kwargs) -> dict:
    """ 
    Make a request and return a dictionary indicating
    success, failure, and the response object
    """
    path = formaturl(path)

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

    response = {}
    response_dict = {}
    response_dict.setdefault("error_message", [])
    response_dict.setdefault("success", False)
    response_dict.setdefault("response", {})
    response_dict.setdefault("retryCount", {})

    try:
        session = requests.Session()
        current_session = retry(session, retries=retries, backoff_factor=0.2, id=item_id)
        response = current_session.get(url, timeout=timeout)    
    except requests.exceptions.HTTPError as errh:
        response_dict["error_message"].append(ERROR_CODES["HTTPError"])
        response_dict["error_message"].append(errh)
    except requests.exceptions.ConnectionError as errc:
        response_dict["error_message"].append(ERROR_CODES["ConnectionError"])
        response_dict["error_message"].append(errc)
    except requests.exceptions.Timeout as errt:
        response_dict["error_message"].append(ERROR_CODES["Timeout"])
        response_dict["error_message"].append(errt)
    except requests.exceptions.RequestException as err:
        response_dict["error_message"].append(ERROR_CODES["RequestException"])
        response_dict["error_message"].append(err)
    except requests.exceptions.InvalidURL as ivurl:
        response_dict["error_message"].append(ERROR_CODES["InvalidURL"])
        response_dict["error_message"].append(ivurl)
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

def validateServiceUrls(items: list = []) -> list:
    # The ThreadPoolExecutor manages a set of worker threads, passing tasks to
    # them as they become available for more work.
    print("Validating Services")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(items)) as executor:
        # map() is uesed to concurrently produce a set of results from an input iterable.
        generator = executor.map(_validateServiceUrl, items)
        return list(generator)

def _validateServiceUrl(item: dict = {}) -> dict:
    """ Check that the Item's url is valid """
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

def check_layer_urls(input_items: list = []) -> list:
    """ 
    Check the layers of the service
    """
    if len(input_items) > 0:
        # The ThreadPoolExecutor manages a set of worker threads, passing tasks to
        # them as they become available for more work.
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(input_items)) as executor:
            # map() is uesed to concurrently produce a set of results from an input iterable.
            generator = executor.map(_check_layer_url, input_items)
            return list(generator)

def _check_layer_url(layer: dict = {}) -> dict:
    """ Check that the Item's url is valid """
    url = ""
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

def validateUsageDetails(items: list) -> list:
    """ Retrieve the usage details for all valid items """
    print("Validating Usage details")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(items)) as executor:
        generator = executor.map(_getItemUsageDetails, items)
        results = list(generator)
        return results

def _getItemUsageDetails(input_item: dict = {}) -> dict:
    """ Usage details show how many times the item has been used for the time period you select. """
    # Only check the items that are valid
    itemResponse = input_item["itemResponse"]
    itemId = itemResponse["id"]
    if itemResponse["isItemValid"]["success"]:
        agolItem = itemResponse["agolItem"]
        usage_details = {}
        try:
            usage = agolItem.usage(date_range=itemResponse["usageParams"]["usageDataRange"], as_df=False)
        except TypeError:
            print(f"ERROR: (TypeError) Unable to retrieve usage details on: {itemId}")
            return {
                "itemResponse": input_item["itemResponse"],
                "serviceResponse": input_item["serviceResponse"],
                "usageResponse" : {
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
            print(f"ERROR: (IndexError) Unable to retrieve usage details on: {itemId}")
            return {
                "itemResponse": input_item["itemResponse"],
                "serviceResponse": input_item["serviceResponse"],
                "usageResponse" : {
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
            print(f"Usage details retrieved on: {itemId}\t{agolItem['title']}")
            return {
                "itemResponse": input_item["itemResponse"],
                "serviceResponse": input_item["serviceResponse"],
                "usageResponse" : {
                    "usage": usage,
                    "itemHasUsageDetails": {
                        "success": True
                    }
                }
            }
    else:
        print(f"Usage details NOT retrieved on: {itemId}")
        return {
            "itemResponse": input_item["itemResponse"],
            "serviceResponse": input_item["serviceResponse"],
            "usageResponse" : {
                "usage": {
                    "data": []
                },
                "itemHasUsageDetails": {
                    "success": False,
                    "error": "Unable to retrieve usage details on: {itemId}"
                }
            }
        }

def getAlfProcessorContent(input_items: list = []) -> list:
    """ """
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(input_items)) as executor:
        # map() is uesed to concurrently produce a set of results from an input iterable.
        generator = executor.map(checkAlfProcessorUrl, input_items)
        return list(generator)

def checkAlfProcessorUrl(input: dict = {}) -> dict:
    """ """
    response = check_request(path=input["url"], 
                             params=input['params'], 
                             try_json=input['try_json'], 
                             add_token=input['add_token'], 
                             retry_factor=input['retry_factor'], 
                             timeout_factor=input['timeout_factor'],
                             token=input['token'],
                             id=input["id"])
    return {
        "id": input["id"],
        "response": response
    }

def getAllFeatureCounts(inputLayerData: list = []) -> dict:
    """ Iterate through the list of layers for each item and check the response """
    print("\n\n============ Getting Feature Counts")
    resultCounts = []
    for layer in inputLayerData:
        # current item ID
        currentItemID = layer[0]["id"]
        # reset the total feature count for this service
        currentItemFeatureCount = 0
        # Query the list of layers of the current item in the iteration
        # and return the feature counts
        validatedLayers = check_layer_urls(layer)
        if validatedLayers is not None:
            for validatedLayer in validatedLayers:
                if validatedLayer["response"]["success"]:
                    #print(f"Elapsed time: {validated_layer['response']['response'].elapsed}")
                    countDict = json.loads(validatedLayer["response"]["response"].content.decode('utf-8'))
                    currentItemFeatureCount += countDict["count"]
        print(f"currentItemFeatureCount: {currentItemID}\t{currentItemFeatureCount}\n")
        resultCounts.append({
            "id": currentItemID,
            "featureCount": currentItemFeatureCount
        })
    return resultCounts

def prepareAlfProcessoerQueryParams(input: dict = {}) -> dict:
    itemID = input["id"]
    return {
        "id": itemID,
        "url": f"https://livefeedsdev.s3.amazonaws.com/Heartbeat/{itemID}.json",
        "try_json": False,
        "add_token": False,
        "params": {},
        "token": "",
        "timeout_factor": 5,
        "retry_factor": 5
    }