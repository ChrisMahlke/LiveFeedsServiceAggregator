""" Methods related to updating the data model """

VERSION = "1.0.0"

import json
import math
import ItemHandler as ItemHandler
import RequestUtils as RequestUtils

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

def hydrateDataModel(inputConfig: list = []) -> dict:
    """ Hydrate the data model that will ultimately be saved to disk """
    for index, item in enumerate(inputConfig):
        itemId = item["id"]
        print(f"{itemId} added to input data model")
        yield {
            "id": itemId,
            "title": "",
            "featureCount": 0,
            "serviceResponse": {

            },
            "status": {
            },
            "trending": {
            }
        }

def updateDataModelWithFeatureCount(inputDataModel: dict = {}, totalFeatureCounts: list = []) -> dict:
    """ Update the data model with the feature counts """
    print(f"Updating input data model with total feature counts")
    for service in totalFeatureCounts:
        # current item ID
        itemID = service["id"]
        # total feature count
        totalFeatureCount = service["featureCount"]

        print(f"\n{itemID}")

        for index, ele in enumerate(inputDataModel):
            if ele["itemResponse"]["id"] == itemID:
                inputDataModel[index].update({
                    "layerResponse": {
                        "id" : itemID,
                        "featureCount": totalFeatureCount
                    }
                })
                print(f"Feature count: {totalFeatureCount}")
    return inputDataModel

def updateDataModelWithServiceResponses(inputData: list = []) -> dict:
    """ 
    Update the data model with the validated layers 
    """
    print(f"Updating input data model with service response data")
    for index, ele in enumerate(inputData):
        itemResponse = ele["itemResponse"]
        serviceResponse = ele["serviceResponse"]
        itemID = itemResponse["id"]
        elapsedTime = 0
        retryCount = 0
        response = None
        success = False
        errorMessage = None
        if serviceResponse["success"]:
            response = serviceResponse["response"]
            retryCount = serviceResponse["retryCount"]
            elapsedTime = response.elapsed.total_seconds()
            errorMessage = serviceResponse["error_message"]
            success = True
        else:
            response = serviceResponse["response"]
            retryCount = serviceResponse["retryCount"]
            errorMessage = serviceResponse["error_message"]

        print(f"\n{itemID}")
        print(f"success: {success}")
        print(f"elapsed time: {elapsedTime}")
        print(f"retry count: {retryCount}")
        print(f"error message: {errorMessage}")

        inputData[index].update({ 
            "serviceResponse" : {
                "ellapsedTime": elapsedTime,
                "retryCount": retryCount,
                "response": response,
                "success": success,
                "errorMessage": errorMessage
            }
        })
    return inputData

def updateDataModelWithUsageDetails(dataModel: dict = {}, inputData: list = []) -> dict:
    """ Update the data model with the usage details """
    print(f"\nUpdating input data model with usage data")
    for index, usage_detail in enumerate(inputData): 

        if usage_detail["usageResponse"]["itemHasUsageDetails"]["success"]:
            # current item ID
            itemID = usage_detail["itemResponse"]["id"]
            # usage data
            data = usage_detail["usageResponse"]["usage"]["data"]
            # default trending stats
            last_hour_count = 0
            last_n_hours_count = 0
            last_n_hours_average = 0
            trending = {
                "id": itemID,
                "code" : USAGE_TRENDING_CODES[0]["code"], 
                "counts": [],
                "percent_change" : 0
            }
            if len(data) > 0:
                # last hour count (we grab the last full hour)
                last_hour_count = int(data[0]["num"][-2][1])
                # TODO: Move to config
                # last n hours (currently 6 hours, exclude the last hour)
                last_n_hours = data[0]["num"][-7:-1]
                # last n hour count
                last_n_hours_count = 0
                # sum up the counts in each of the last n hours
                for hr in last_n_hours:
                    last_n_hours_count = last_n_hours_count + int(hr[1])
                # get the average over the last n hours
                last_n_hours_average = math.trunc(last_n_hours_count/6)
                # determine the trending code
                trending = _getTrending(itemID, last_hour_count, last_n_hours_count, last_n_hours_average)
                print(f"trending: {trending}")
        else:
            itemID = usage_detail["itemResponse"]["id"]
            trending = {
                "id": itemID,
                "code" : USAGE_TRENDING_CODES[0]["code"],
                "counts": [],
                "percent_change" : 0
            }

        print(f"\n{trending['id']}")
        print(f"{trending['code']}")
        print(f"{trending['counts']}")
        print(f"{trending['percent_change']}\n")

        inputData[index]["serviceResponse"].update({
            "trending": trending
        })
    return inputData

def updateDataModelWithAlfProcessorContent(data_model: dict = {}, inputData: list = []) -> dict:
    """ Retrieve status content from the ALF Processor and ingest into the data model """
    for input in inputData:
        itemID = input["id"]
        alfp = ItemHandler.getAlfProcessorContent(input)
        # reset status code and message to Normal
        status_code = 0
        status_details = ""
        # run timestamps
        lastRunTimestamp = 0
        lastUpdateTimestamp = 0
        # Check if the alfp JSON was returned
        if alfp["success"]:
            alfpContent = alfp["content"]
            alfpLastStatus = alfpContent["lastStatus"]
            alfpCode = alfpLastStatus["code"]
            alfpCodeDetails = alfpLastStatus["details"]
            alfpLastRunTimestamp = alfpContent["lastRunTimestamp"]
            alfpLastUpdateTimestamp = alfpContent["lastUpdateTimestamp"]
            alfpConsecutiveFailures = alfpContent["consecutiveFailures"]
            avgUpdateIntervalMins = alfpContent["avgUpdateIntervalMins"]
            avgFeedIntervalMins = alfpContent["avgFeedIntervalMins"]
            # alfp code
            #if alfpCode == 0:
            status_code = alfpCode
            status_details = alfpCodeDetails
            #else:
            print(f"ALF Processor Code: {status_code}")
            # alfp timestamps
            lastRunTimestamp = alfpLastRunTimestamp
            lastUpdateTimestamp = alfpLastUpdateTimestamp
        else:
            print(f"ERROR: The Feed state is not accessible for the item {itemID}. Falling back to only the results generated from testing the Service state.")

        print(f"\n{itemID}")
        print(f"\tconsecutive failure: {alfpConsecutiveFailures}")
        print(f"\taverage update interval: {avgUpdateIntervalMins}")
        print(f"\taverage feed interval: {avgFeedIntervalMins}")
        print(f"\tlast run timestamp: {lastRunTimestamp}")
        print(f"\tlast update timestamp: {lastUpdateTimestamp}")
        print(f"\tstatus code: {status_code}")
        print(f"\tstatus details: {status_details}")

        for index, model_ele in enumerate(data_model):
            if model_ele["itemResponse"]["id"] == itemID:
                data_model[index].update({ 
                    "alfpResponse" : {
                        "consecutiveFailures": alfpConsecutiveFailures,
                        "avgUpdateIntervalMins": avgUpdateIntervalMins,
                        "avgFeedIntervalMins": avgFeedIntervalMins,
                        "lastRunTimestamp": lastRunTimestamp,
                        "lastUpdateTimestamp": lastUpdateTimestamp,
                        "alf_status" : {
                            "code": status_code,
                            "details": status_details
                        }
                    }
                })
    return data_model

def _getTrending(itemID: str = "", last_hour_count: int = 0, last_n_hours_count: int = 0, last_n_hour_average: int = 0) -> dict:
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
    percentChange = 0
    increase = last_hour_count - last_n_hour_average
    if last_n_hour_average > 0:
        percentChange = (increase/last_n_hour_average) * 100

    print(f"\n{itemID}")
    print(f"Trending data")
    print(f"Last hour count: {last_hour_count}")
    print(f"Last n hour(s) count: {last_n_hours_count}")
    print(f"Last n hour average: {last_n_hour_average}")
    print(f"{last_hour_count} - {last_n_hour_average} = {increase}")
    print(f"Percent Change: ({increase}/{last_n_hour_average} x 100) = {percentChange}")

    tc = USAGE_TRENDING_CODES[0]["code"]
    if PERCENT_LOWER_BOUND <= percentChange <= PERCENT_UPPER_BOUND:
        tc = USAGE_TRENDING_CODES[0]["code"]
    elif percentChange > PERCENT_UPPER_BOUND:
        tc = USAGE_TRENDING_CODES[1]["code"]
    elif percentChange < PERCENT_LOWER_BOUND:
        tc = USAGE_TRENDING_CODES[2]["code"]
    return {
        "id": itemID,
        "code": tc,
        "counts": [last_hour_count, last_n_hour_average],
        "percent_change": percentChange
    }
