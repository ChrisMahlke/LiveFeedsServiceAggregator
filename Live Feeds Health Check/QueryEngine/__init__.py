"""
Obtain usage statistics
---------------------------
- Requirements for check
Item must be accessible

- Results
Success -   Obtain usage statistics
Error   -   Use usage statistics from previous run (do not over-write data model)

Obtain feature counts
---------------------------
- Requirements for check
Service and Layers must be accessible

- Results
Success -   Obtain feature counts
Error   -   Use feature counts from previous run (do not over-write data model)
"""
import concurrent.futures
import json
import math
import RequestUtils as RequestUtils


def get_usage_details(data_model=None) -> dict:
    """
    Retrieve the item's usage statistics
    :param data_model: Input data model
    :return: Updated data model dictionary
    """
    if data_model is None:
        data_model = {}

    USAGE_TRENDING_CODES = [
        {
            "code": 0,
            "description": "No Change"
        },
        {
            "code": 1,
            "description": "Up"
        },
        {
            "code": -1,
            "description": "Down"
        }
    ]

    def get_trending(last_hour_count: int = 0,
                     last_n_hours_count: int = 0,
                     last_n_hour_average: int = 0,
                     lower_bounds=None,
                     upper_bounds=None) -> dict:
        """
        Returns a dictionary indicating the trending values
        :param last_hour_count: The number of requests in the last hour
        :param last_n_hours_count: The number of requests over the last n hours
        :param last_n_hour_average: The average number of requests over the last n hours
        :param lower_bounds: The lower bounds
        :param upper_bounds: The upper bounds
        :return: Dictionary
        """
        # Increase = New Number - Original Number
        # %increase = Increase ÷ Original Number × 100
        percent_change = 0
        increase = last_hour_count - last_n_hour_average
        if last_n_hour_average > 0:
            percent_change = (increase / last_n_hour_average) * 100

        print(f"Trending data")
        print(f"Last hour count: {last_hour_count}")
        print(f"Last n hour(s) count: {last_n_hours_count}")
        print(f"Last n hour average: {last_n_hour_average}")
        print(f"{last_hour_count} - {last_n_hour_average} = {increase}")
        print(f"Percent Change: ({increase}/{last_n_hour_average} x 100) = {percent_change}")

        tc = USAGE_TRENDING_CODES[0]["code"]
        if lower_bounds <= percent_change <= upper_bounds:
            tc = USAGE_TRENDING_CODES[0]["code"]
        elif percent_change > upper_bounds:
            tc = USAGE_TRENDING_CODES[1]["code"]
        elif percent_change < lower_bounds:
            tc = USAGE_TRENDING_CODES[2]["code"]
        return {
            "trendingCode": tc,
            "percentChange": percent_change,
            "usageCounts": [last_hour_count, last_n_hour_average]
        }

    def get_usage_detail(current_item):
        """
        Get the usage detail for a single item
        :param current_item: The current item
        :return: A response from the usage query
        """
        item_id = current_item[0]
        item_content = current_item[1]
        print(f"{item_id}")
        response = {
            "trendingCode": 0,
            "percentChange": 0,
            "usageCounts": [0, 0]
        }
        try:
            agol_item = item_content["agolItem"]
            if agol_item is not None:
                usage_data = agol_item.usage(date_range=item_content["usage_data_range"], as_df=False)
                if len(usage_data["data"]) > 0:
                    # last hour count (we grab the last full hour)
                    last_hour_count = int(usage_data["data"][0]["num"][-2][1])
                    # TODO: Move to config
                    # last n hours (currently 6 hours, exclude the last hour)
                    last_n_hours = usage_data["data"][0]["num"][-7:-1]
                    # last n hour count
                    last_n_hours_count = 0
                    # sum up the counts in each of the last n hours
                    for hr in last_n_hours:
                        last_n_hours_count = last_n_hours_count + int(hr[1])
                    # get the average over the last n hours
                    last_n_hours_average = math.trunc(last_n_hours_count / 6)
                    # determine the trending code
                    response = get_trending(last_hour_count,
                                            last_n_hours_count,
                                            last_n_hours_average,
                                            int(item_content["percent_lower_bound"]),
                                            int(item_content["percent_upper_bound"]))
            else:
                print(f"ERROR: Unable to retrieve usage details on: {item_id}.")
                return current_item[0], {**current_item[1], **{"usage": response}}
        except (IndexError, KeyError, TypeError) as e:
            print(f"ERROR: Unable to retrieve usage details on: {item_id}. {e}")
            return current_item[0], {**current_item[1], **{"usage": response}}
        else:
            return current_item[0], {**current_item[1], **{"usage": response}}

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
        item_id = current_item[0]
        item_content = current_item[1]
        layer_query_params = item_content["layerQueryParams"]
        # reset the total feature count for this service
        current_item_feature_count = 0
        #
        elapsed_times = []
        # We check if the service is accessible, not the item
        if item_content["serviceResponse"]["success"]:
            exclusion_list_input = item_content["exclusion"].split(",")
            exclusion_list_input_results = []
            if isinstance(exclusion_list_input[0], str) and \
                    len(exclusion_list_input[0]) > 0 and \
                    len(exclusion_list_input) > 0:
                exclusion_list_input_results = list(map(int, exclusion_list_input))

            for layer in layer_query_params:
                if "layerId" in layer:
                    # Query the list of layers of the current item in the iteration
                    # and return the feature counts
                    validated_layer = check_layer_url(layer)
                    if validated_layer is not None:
                        if validated_layer["success"]:
                            print(f"Success\t{current_item[0]}\t{layer['layerName']}")
                            if layer["layerId"] not in exclusion_list_input_results:
                                count_dict = json.loads(validated_layer["response"].content.decode('utf-8'))
                                if "count" in count_dict:
                                    print(f"Feature count: {count_dict['count']}")
                                    current_item_feature_count += count_dict["count"]
                            else:
                                print(f"Feature count: EXCLUDED")
                            print(f"Elapsed time: {validated_layer['response'].elapsed.total_seconds()}")
                            elapsed_times.append({
                                "item": current_item[0],
                                "elapsedTime": validated_layer['response'].elapsed.total_seconds(),
                                "layerName": layer['layerName']
                            })
                        else:
                            print(f"Error\t{current_item[0]}\t{layer['layerName']}")
                    else:
                        # TODO Return elapsed time and error message
                        print(f"")
        else:
            # The service is not valid or inaccessible, use the cached feature count
            if "featureCount" in item_content:
                current_item_feature_count = item_content["featureCount"]
        return current_item[0], {
            **current_item[1],
            **{"featureCount": current_item_feature_count},
            **{"serviceLayersElapsedTimes": elapsed_times}
        }

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


def get_service_elapsed_time(service_is_valid=None, response=None) -> float:
    """
    Get the elapsed time in seconds.

    The amount of time elapsed between sending the request and the arrival of the response (as a timedelta). This
    property specifically measures the time taken between sending the first byte of the request and finishing parsing
    the headers. It is therefore unaffected by consuming the response content or the value of the stream keyword
    argument.

    :param service_is_valid: If the service is not valid, return 0 (which is impossible)
    :param response: The response object
    :return: The response time in seconds
    """
    elapsed_time = 0
    # If the service is valid we can get the elapsed time
    if service_is_valid:
        # get elapsed time in seconds
        elapsed_time = response.elapsed.total_seconds()
    return elapsed_time


def get_layers_average_elapsed_time(layers_elapsed_times=None) -> float:
    """
    Sum up the elapsed times of all the layers in the service.

    :param layers_elapsed_times: A dict containing the elapsed times and layer names for a service
    :return: The average (float) of the elapsed times
    """
    elapsed_time_average = 0
    total_elapsed_time = 0
    num_elapsed_times = len(layers_elapsed_times)
    if num_elapsed_times > 0:
        for layers_elapsed_time in layers_elapsed_times:
            layer_name = layers_elapsed_time['layerName']
            layer_elapsed_time = layers_elapsed_time['elapsedTime']
            print(f"\t{layer_name} ({layer_elapsed_time})")
            total_elapsed_time = total_elapsed_time + layer_elapsed_time
        elapsed_time_average = total_elapsed_time/num_elapsed_times
    return elapsed_time_average


def process_alfp_response(alfp_response=None) -> dict:
    """

    :param alfp_response:
    :return:
    """
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
    """

    :param input_items:
    :return:
    """
    if input_items is None:
        input_items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(input_items)) as executor:
        # map() is used to concurrently produce a set of results from an input iterable.
        generator = executor.map(check_alfp_url, input_items)
        return list(generator)


def check_alfp_url(input_data=None) -> dict:
    """

    :param input_data:
    :return:
    """
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
    item_id = input_data[0]
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
