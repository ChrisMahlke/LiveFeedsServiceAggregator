import concurrent.futures
import json
import RequestUtils as RequestUtils


def get_usage_details(data_model=None) -> dict:
    """
    Retrieve the item's usage statistics
    :param data_model: Input data model
    :return: Updated data model dictionary
    """
    if data_model is None:
        data_model = {}

    def get_usage_detail(current_item):
        """
        Get the usage detail for a single item
        :param current_item: The current item
        :return: A response from the usage query
        """
        item_id = current_item[0]
        item_content = current_item[1]
        print(f"{item_id}")
        try:
            agol_item = item_content["agolItem"]
            if agol_item is None:
                print(f"ERROR: Unable to retrieve usage details on: {item_id}.")
                response = {
                    "usage": {
                        "data": []
                    },
                    "itemHasUsageDetails": {
                        "success": False,
                        "error": f"ERROR: Unable to retrieve usage details on: {item_id}."
                    }
                }
                return current_item[0], {**current_item[1], **{"usageResponse": response}}
            else:
                usage = agol_item.usage(date_range=item_content["usage_data_range"], as_df=False)
        except (IndexError, KeyError, TypeError) as e:
            print(f"ERROR: Unable to retrieve usage details on: {item_id}. {e}")
            response = {
                "usage": {
                    "data": []
                },
                "itemHasUsageDetails": {
                    "success": False,
                    "error": f"ERROR: Unable to retrieve usage details on: {item_id}. {e}"
                }
            }
            return current_item[0], {**current_item[1], **{"usageResponse": response}}
        else:
            response = {
                "usage": usage,
                "itemHasUsageDetails": {
                    "success": True
                }
            }
            return current_item[0], {**current_item[1], **{"usageResponse": response}}

    return dict(map(get_usage_detail, data_model.items()))


def get_feature_counts(data_model=None) -> dict:
    """
    Get the sum of all "included" features in all the feature services in the input data model
    :param data_model: Input data model
    :return: Updated data model
    """
    if data_model is None:
        data_model = {}

    def get_feature_count(current_item):
        """
        Get the sum of all the "included" feature counts in the service
        :param current_item:
        :return:
        """
        item_content = current_item[1]
        layer_query_params = item_content["layerQueryParams"]
        # reset the total feature count for this service
        current_item_feature_count = 0
        # We check if the service is accessible, not the item
        if item_content["serviceResponse"]["success"]:
            for layer in layer_query_params:
                # Query the list of layers of the current item in the iteration
                # and return the feature counts
                validated_layer = check_layer_url(layer)
                if validated_layer is not None:
                    if validated_layer["success"]:
                        # print(f"Elapsed time: {validated_layer['response']['response'].elapsed}")
                        count_dict = json.loads(validated_layer["response"].content.decode('utf-8'))
                        try:
                            current_item_feature_count += count_dict["count"]
                        except KeyError as e:
                            print(f"There was an error with retrieving the count for the item {current_item[0]}")
        else:
            # The item is not valid or inaccessible, use the cached feature count
            if "featureCount" in item_content:
                current_item_feature_count = item_content["featureCount"]
        return current_item[0], {**current_item[1], **{"featureCount": current_item_feature_count}}

    def check_layer_url(layer=None) -> dict:
        """ Check that the Item's url is valid """
        if layer is None:
            layer = {}
        response = {
            "id": layer["id"],
            "success": False
        }
        if layer["success"]:
            url = layer["url"]
            response = RequestUtils.check_request(path=url,
                                                  params=layer['params'],
                                                  try_json=layer['try_json'],
                                                  add_token=layer['add_token'],
                                                  retry_factor=5,
                                                  timeout_factor=5,
                                                  id=layer["id"],
                                                  token=layer['token'])
        return response

    return dict(map(get_feature_count, data_model.items()))


def get_retry_count(value=None) -> int:
    """ Get the total number of retries """
    retry_count = 0
    # If the retry count is greater than 0
    if len(value) > 0:
        retry_count = value["retryCount"]
    return retry_count


def get_elapsed_time(service_is_valid=None, response=None) -> float:
    """ Get the elapsed time in seconds """
    elapsed_time = 0
    # If the service is valid we can get the elapsed time
    if service_is_valid:
        # get elapsed time in seconds
        elapsed_time = response.elapsed.total_seconds()
    return elapsed_time


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
    response = RequestUtils.check_request(path=input_data["url"],
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
