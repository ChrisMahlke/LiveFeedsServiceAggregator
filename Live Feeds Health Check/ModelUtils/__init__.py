""" Methods related to updating the data model """

import math
import ItemHandler as ItemHandler

VERSION = "1.0.0"

PERCENT_UPPER_BOUND = 5
PERCENT_LOWER_BOUND = -5

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


def hydrate_data_model(input_config=None) -> dict:
    """ Hydrate the data model that will ultimately be saved to disk """
    if input_config is None:
        input_config = []
    for index, item in enumerate(input_config):
        item_id = item["id"]
        print(f"{item_id} added to input data model")
        yield {
            "id": item_id,
            "title": "",
            "featureCount": 0,
            "serviceResponse": {

            },
            "status": {
            },
            "trending": {
            }
        }


def update_data_model_feature_counts(input_data_model=None, total_feature_counts=None) -> list:
    """ Update the data model with the feature counts """
    if total_feature_counts is None:
        total_feature_counts = []
    if input_data_model is None:
        input_data_model = []
    print(f"Updating input data model with total feature counts")
    for service in total_feature_counts:
        # current item ID
        item_id = service["id"]
        # total feature count
        total_feature_count = service["featureCount"]

        print(f"\n{item_id}")

        for index, ele in enumerate(input_data_model):
            if ele["itemResponse"]["id"] == item_id:
                input_data_model[index].update({
                    "layerResponse": {
                        "id": item_id,
                        "featureCount": total_feature_count
                    }
                })
                print(f"Feature count: {total_feature_count}")
    return input_data_model


def update_data_model_service_responses(input_data=None) -> list:
    """ 
    Update the data model with the validated layers 
    """
    if input_data is None:
        input_data = []
    print(f"Updating input data model with service response data")
    for index, ele in enumerate(input_data):
        item_response = ele["itemResponse"]
        service_response = ele["serviceResponse"]
        item_id = item_response["id"]
        elapsed_time = 0
        success = False
        if service_response["success"]:
            response = service_response["response"]
            retry_count = service_response["retryCount"]
            elapsed_time = response.elapsed.total_seconds()
            error_message = service_response["error_message"]
            success = True
        else:
            response = service_response["response"]
            retry_count = service_response["retryCount"]
            error_message = service_response["error_message"]

        print(f"\n{item_id}")
        print(f"success: {success}")
        print(f"elapsed time: {elapsed_time}")
        print(f"retry count: {retry_count}")
        print(f"error message: {error_message}")

        input_data[index].update({
            "serviceResponse": {
                "elapsedTime": elapsed_time,
                "retryCount": retry_count,
                "response": response,
                "success": success,
                "errorMessage": error_message
            }
        })
    return input_data


def update_data_model_usage_details(input_data=None) -> list:
    """ Update the data model with the usage details """
    if input_data is None:
        input_data = []
    print(f"\nUpdating input data model with usage data")
    for index, usage_detail in enumerate(input_data):
        # current item ID
        item_id = usage_detail["itemResponse"]["id"]
        if usage_detail["usageResponse"]["itemHasUsageDetails"]["success"]:
            # usage data
            data = usage_detail["usageResponse"]["usage"]["data"]
            trending = {
                "id": item_id,
                "code": USAGE_TRENDING_CODES[0]["code"],
                "counts": [],
                "percent_change": 0
            }
            if len(data) > 0:
                # last hour count
                last_hour_count = int(data[0]["num"][-2][1])
                # TODO: Move to config
                # last n hours (currently 6 hours)
                last_n_hours = data[0]["num"][-7:-1]
                # last n hour count
                last_n_hours_count = 0
                for hr in last_n_hours:
                    last_n_hours_count = last_n_hours_count + int(hr[1])
                # get the average over the last n hours
                last_n_hours_average = math.trunc(last_n_hours_count/6)
                # determine the trending code
                trending = _get_trending(item_id, last_hour_count, last_n_hours_count, last_n_hours_average)
                print(f"trending: {trending}")
        else:
            trending = {
                "id": item_id,
                "code": USAGE_TRENDING_CODES[0]["code"],
                "counts": [],
                "percent_change": 0
            }

        print(f"\n{trending['id']}")
        print(f"{trending['code']}")
        print(f"{trending['counts']}")
        print(f"{trending['percent_change']}\n")

        input_data[index]["serviceResponse"].update({
            "trending": trending
        })
    return input_data


def update_data_model_alfp_content(data_model=None, input_data=None) -> dict:
    """ Retrieve status content from the ALF Processor and ingest into the data model """
    if input_data is None:
        input_data = []
    if data_model is None:
        data_model = {}
    for _input in input_data:
        item_id = _input["id"]
        alfp = ItemHandler.get_alfp_content(_input)
        # reset status code and message to Normal
        status_code = 0
        status_details = ""
        # Check if the alfp JSON was returned
        if alfp["success"]:
            alfp_content = alfp["content"]
            alfp_last_status = alfp_content["lastStatus"]
            alfp_code = alfp_last_status["code"]
            alfp_code_details = alfp_last_status["details"]
            alfp_last_run_timestamp = alfp_content["lastRunTimestamp"]
            alfp_last_update_timestamp = alfp_content["lastUpdateTimestamp"]
            alfp_consecutive_failures = alfp_content["consecutiveFailures"]
            avg_update_interval_mins = alfp_content["avgUpdateIntervalMins"]
            avg_feed_interval_mins = alfp_content["avgFeedIntervalMins"]
            # alfp code
            # if alfp_code == 0:
            status_code = alfp_code
            status_details = alfp_code_details
            #else:
            print(f"ALF Processor Code: {alfp_code}")
            # alfp timestamps
            last_run_timestamp = alfp_last_run_timestamp
            last_update_timestamp = alfp_last_update_timestamp

            print(f"\n{item_id}")
            print(f"\tconsecutive failure: {alfp_consecutive_failures}")
            print(f"\taverage update interval: {avg_update_interval_mins}")
            print(f"\taverage feed interval: {avg_feed_interval_mins}")
            print(f"\tlast run timestamp: {last_run_timestamp}")
            print(f"\tlast update timestamp: {last_update_timestamp}")
            print(f"\tstatus code: {status_code}")
            print(f"\tstatus details: {status_details}")

            for index, model_ele in enumerate(data_model):
                if model_ele["itemResponse"]["id"] == item_id:
                    data_model[index].update({
                        "alfpResponse": {
                            "consecutiveFailures": alfp_consecutive_failures,
                            "avgUpdateIntervalMins": avg_update_interval_mins,
                            "avgFeedIntervalMins": avg_feed_interval_mins,
                            "lastRunTimestamp": last_run_timestamp,
                            "lastUpdateTimestamp": last_update_timestamp,
                            "alf_status": {
                                "code": status_code,
                                "details": status_details
                            }
                        }
                    })
        else:
            print(f"ERROR: The Feed state is not accessible for the item {item_id}. Falling back to only the results "
                  f"generated from testing the Service state.")

    return data_model


def _get_trending(item_id: str = "", last_hour_count: int = 0, last_n_hours_count: int = 0, last_n_hour_average: int = 0) -> dict:
    """ 
    Returns a dictionary indicating the trending values 

    args
    - itemID    The unique item ID
    - last_hour_count   The number of requests in the last hour
    - last_n_hours_count    The number of requests over the last n hours
    - last_n_hour_average   The average number of requests over the last n hours

    returns
    - dictionary

    """
    # Increase = New Number - Original Number
    # %increase = Increase ÷ Original Number × 100
    percent_change = 0
    increase = last_hour_count - last_n_hour_average
    if last_n_hour_average > 0:
        percent_change = (increase/last_n_hour_average) * 100

    print(f"\n{item_id}")
    print(f"Trending data")
    print(f"Last hour count: {last_hour_count}")
    print(f"Last n hour(s) count: {last_n_hours_count}")
    print(f"Last n hour average: {last_n_hour_average}")
    print(f"{last_hour_count} - {last_n_hour_average} = {increase}")
    print(f"Percent Change: ({increase}/{last_n_hour_average} x 100) = {percent_change}")

    tc = USAGE_TRENDING_CODES[0]["code"]
    if PERCENT_LOWER_BOUND <= percent_change <= PERCENT_UPPER_BOUND:
        tc = USAGE_TRENDING_CODES[0]["code"]
    elif percent_change > PERCENT_UPPER_BOUND:
        tc = USAGE_TRENDING_CODES[1]["code"]
    elif percent_change < PERCENT_LOWER_BOUND:
        tc = USAGE_TRENDING_CODES[2]["code"]

    return {
        "id": item_id,
        "code": tc,
        "counts": [last_hour_count, last_n_hour_average],
        "percent_change": percent_change
    }
