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


def validate_items(gis: arcgis.gis.GIS = None, data_model=None) -> dict:
    """
    Accepts a dict of items and retrieves the item in ArcGIS Online.
    If the item is accessible the title and snippet are updated to reflect any changes that occurred in AGOL

    Validation Rule:
    1) Is the item ID a valid ID
    2) Is the item accessible
    """
    if data_model is None:
        data_model = {}

    def validate_item(current_item):
        item_id = current_item[0]
        try:
            agol_item = gis.content.get(item_id)
            if agol_item is None:
                current_item[1].update({
                    "itemIsValid": False
                })
                print(f"ERROR\t{item_id} is invalid or item is inaccessible")
        except Exception as e:
            current_item[1].update({
                "itemIsValid": False
            })
            print(f"ERROR\t{item_id} is having an issue: {e}")
        else:
            # update the title and snippet in case it has changed in AGOL
            current_item[1].update({
                "title": agol_item["title"],
                "snippet": agol_item["snippet"],
                "service_url": agol_item["url"],
                "agolItem": agol_item,
                "itemIsValid": True
            })
        finally:
            return current_item[0], current_item[1]

    updated_data_model = dict(map(validate_item, data_model.items()))

    return updated_data_model


def validate_services(data_model=None) -> dict:
    """ """
    if data_model is None:
        data_model = {}

    def validate_service(current_item):
        item_id = current_item[0]
        params = current_item[1]
        response = _check_request(path=params["service_url"],
                                  params={},
                                  try_json=True,
                                  add_token=True,
                                  retry_factor=params["default_retry_count"],
                                  timeout_factor=params["default_timeout"],
                                  token=params["token"],
                                  id=item_id)
        return current_item[0], {**current_item[1], **{"serviceResponse": response}}

    updated_data_model = dict(map(validate_service, data_model.items()))

    return updated_data_model


def validate_layers(data_model=None) -> dict:
    """ """
    if data_model is None:
        data_model = {}

    def validate_service_layers(current_item):
        item_id = current_item["id"]
        if current_item["itemIsValid"]["success"]:
            layers = []
            exclusion_list_input = item["exclusion"].split(",")
            exclusion_list_input_results = []
            if isinstance(exclusion_list_input[0], str) and len(exclusion_list_input[0]) > 0:
                exclusion_list_input_results = list(map(int, exclusion_list_input))
            try:
                for i, layer in enumerate(current_item["agol_item"].layers):
                    if layer.properties["id"] not in exclusion_list_input_results:
                        print(f"\t{layer.properties['name']}")
                        layers.append({
                            "id": item_id,
                            "name": layer.properties['name'],
                            "success": True,
                            "token": current_item["token"],
                            "url": layer.url
                        })
            except Exception as e:
                print(f"\t{e}")
                layers.append({
                    "id": item_id,
                    "success": False,
                    "message": e
                })
                return layers
            else:
                return layers

    def prepare_layer_query_params(layers=None) -> list:
        # we need to check if the item's service is valid
        # the item can be accessible in ArcGIS Online, but the service url could be down

        # check the item's layers (if valid)
        # Same as above, the service URL could be accessible, but the layers
        # may not be accessible
        if layers is None:
            layers = []
        layer_data = []
        for layer in layers:
            item_id = layer["id"]
            if layer["success"]:
                layer_name = layer["name"]
                layer_url = layer["url"]
                layer_data.append({
                    "id": item_id,
                    "layerName": layer_name,
                    "url": layer_url + "/query",
                    "try_json": True,
                    "add_token": True,
                    "params": {
                        'where': '1=1',
                        'returnGeometry': 'false',
                        'returnCountOnly': 'true'
                    },
                    "success": True,
                    "token": layer["token"]
                })
            else:
                layer_data.append({
                    "id": item_id,
                    "success": False
                })
        return layer_data

    validated_layers = list(map(validate_service_layers, data_model.items()))
    print(validated_layers)
    layer_input_query_params = list(map(prepare_layer_query_params, validated_layers))
    print(layer_input_query_params)
    print()

    return updated_data_model




def process_alfp_response(alfp_response=None) -> dict:
    """ """
    if alfp_response is None:
        alfp_response = []
    if alfp_response["response"]["success"]:
        item_id = alfp_response["id"]
        if alfp_response["response"]["response"].status_code == 200:
            content = json.loads(alfp_response["response"]["response"].content.decode('utf-8'))
            return {
                "id": item_id,
                "content": content,
                "success": True
            }
        else:
            status_code = alfp_response["response"]["response"].status_code
            reason = alfp_response["response"]["response"].reason
            return {
                "id": item_id,
                "status_code": status_code,
                "reason": reason,
                "success": False
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
    response = _check_request(path=input_data["url"],
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


def _format_url(url):
    if not re.match('(?:http|ftp|https)://', url):
        return 'https://{}'.format(url)
    return url


def _check_request(path: str = "", params=None, **kwargs) -> dict:
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
        print(f"URL: {url}")
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
