#!/usr/bin/env python3

# Copyright 2020, Esri.  All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is  distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
"""
LiveFeedsHealthCheck

1) Authenticate GIS profile
2) Setup
3) Validation and Health check
4) Process results
5) Create/Update RSS files
6) Save output

"""

try:
    import arcgis
    import arcpy
    import json
    import os

    import FileManager as FileManager
    import ItemHandler as ItemHandler
    import LoggingUtils as LoggingUtils
    import ModelUtils as ModelUtils
    import QueryEngine as QueryEngine
    import RequestUtils as RequestUtils
    import FeedGenerator as FeedGenerator
    import ServiceValidator as ServiceValidator
    import StatusManager as StatusManager
    import TimeUtils as TimeUtils
    import version as version

    from ConfigManager import ConfigManager
    from UserUtils import User
    from collections import defaultdict
except ImportError as e:
    print(f"Import Error: {e}")


class ItemCountNotInRangeError(Exception):
    """Exception raised for errors when the input item count is 0

        Attributes:
            item_count -- input item count which caused the error
            message -- explanation of the error
    """

    def __init__(self, num_items, message="No items found!"):
        self.num_items = num_items
        self.message = message

    def __str__(self):
        return f"\nItem count: {self.num_items} \nThere are not items in the config file!"


class InputFileNotFoundError(Exception):
    """Exception raised for errors in the input file is not found.

        Attributes:
            file -- input file
            message -- explanation of the error
    """

    def __init__(self, input_file, message="The file is not found"):
        self.input_file = input_file
        self.message = message

    def __str__(self):
        return f"\nThe file {self.input_file} was not found or does not exist!"


if __name__ == "__main__":
    print(f"\nRunning version: {version.version_str}")

    print("\n=================================================================")
    print(f"Authenticate GIS profile")
    print("=================================================================")
    # TODO: Not the best way at all to get the profile property from the config file
    gisProfile = "cmahlke_developer"
    # initialize GIS object
    GIS = arcgis.GIS(profile=gisProfile)
    # initialize User object
    USER = GIS.users.get(gisProfile)
    if USER is None:
        print("You are not signed in")
        # TODO: Exit script gracefully and notify Admin(?)
    else:
        # get the installation properties and print to stdout
        INSTALL_INFO = arcpy.GetInstallInfo()
        USER_SYS = User(user=USER, install_info=INSTALL_INFO)
        USER_SYS.greeting()

    print("\n=================================================================")
    print(f"Setting up project and checking folders and directories")
    print("=================================================================")
    # The root directory of the script
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"Project Root Directory: {ROOT_DIR}\n")

    # Load config ini file
    print("\nLoading input items from configuration file")
    configIniManager = ConfigManager(root=ROOT_DIR, file_name="config.ini")
    input_items = configIniManager.get_config_data(config_type="items")
    item_count = len(input_items)
    data_model_dict = {}
    if item_count < 1:
        raise ItemCountNotInRangeError(item_count)
    else:
        for input_item in input_items:
            data_model_dict.update({
                input_item["id"]: {**input_item, **{"token": GIS._con.token}}
            })

    # Read in the status codes
    print("\nLoading status codes")
    statusCodeConfigPath = os.path.realpath(ROOT_DIR + r"\statusCodes.json")
    statusCodeJsonExist = FileManager.check_file_exist_by_pathlib(path=statusCodeConfigPath)
    statusCodesDataModel = None
    if statusCodeJsonExist is False:
        raise InputFileNotFoundError(statusCodeConfigPath)
    else:
        statusCodesDataModel = FileManager.open_file(path=statusCodeConfigPath)

    # retrieve the alf statuses
    print("\nRetrieving and Processing Active Live Feed Processed files")
    alfProcessorQueries = list(map(QueryEngine.prepare_alfp_query_params, input_items))
    alfProcessorResponse = QueryEngine.get_alfp_content(alfProcessorQueries)
    alfpContent = list(map(QueryEngine.process_alfp_response, alfProcessorResponse))
    alfpDict = {}
    for content in alfpContent:
        unique_item_key = content["id"]
        try:
            alfpDict.update({
                unique_item_key: content["content"]
            })
        except KeyError:
            print(f"{unique_item_key} is unknown.")

    # Read in the previous status output file
    print("\nLoading output from previous run")
    outputStatusDirPath = os.path.realpath(ROOT_DIR + r"\output")
    # Create a new directory if it does not exists
    FileManager.create_new_folder(outputStatusDirPath)
    # path to output file
    outputFilePath = os.path.realpath(outputStatusDirPath + r"\status.json")
    # Check file existence
    fileExist = FileManager.check_file_exist_by_pathlib(path=outputFilePath)
    if fileExist:
        # iterate through the items in the config file
        for key, value in data_model_dict.items():
            # iterate through the items in the status file
            for ele in FileManager.open_file(outputFilePath)["items"]:
                status_file_key = ele["id"]
                if key == status_file_key:
                    merged_dict = {**ele, **value}
                    data_model_dict.update({
                        key: merged_dict
                    })

    print("\n===================================================================")
    print(f"Validating item meta-data")
    print("===================================================================")
    data_model_dict = ServiceValidator.validate_items(gis=GIS, data_model=data_model_dict)

    print("\n===================================================================")
    print(f"Validating services")
    print("===================================================================")
    data_model_dict = ServiceValidator.validate_services(data_model=data_model_dict)

    print("\n===================================================================")
    print(f"Validating layers")
    print("===================================================================")
    data_model_dict = ServiceValidator.validate_layers(data_model=data_model_dict)

    print("\n===================================================================")
    print(f"Retrieve usage statistics")
    print("===================================================================")
    data_model_dict = QueryEngine.get_usage_details(data_model=data_model_dict)

    print("\n===================================================================")
    print(f"Retrieve feature counts")
    print("===================================================================")
    data_model_dict = QueryEngine.get_feature_counts(data_model=data_model_dict)

    print("\n=================================================================")
    print(f"Current data and time")
    print("===================================================================")
    timeUtilsResponse = TimeUtils.get_current_time_and_date()
    timestamp = timeUtilsResponse["timestamp"]

    for key, value in data_model_dict.items():
        item_id = key
        agol_is_valid = True
        item_is_valid = value["itemIsValid"]
        service_is_valid = value["serviceResponse"]["success"]
        layers_are_valid = value["allLayersAreValid"]

        # Process Retry Count
        retry_count = 0
        if len(value["serviceResponse"]["retryCount"]) > 0:
            retry_count = value["serviceResponse"]["retryCount"]["retryCount"]
        print(f"Retry count: {retry_count}")

        # Process Elapsed Time
        elapsed_time = 0
        # elapsed time
        if service_is_valid:
            # get elapsed time in seconds
            elapsed_time = value["serviceResponse"]["response"].elapsed.total_seconds()
        print(f"Elapsed time: {elapsed_time}")
        # Obtain the total elapsed time and counts
        # response time directory
        response_time_data_dir = os.path.realpath(ROOT_DIR + r"\ResponseTimeData")
        # Create a new directory if it does not exists
        FileManager.create_new_folder(response_time_data_dir)
        # path to output file
        response_time_data_file_path = os.path.join(response_time_data_dir, item_id + "." + "json")
        # Check file existence.
        response_time_data_file_path_exist = FileManager.check_file_exist_by_pathlib(path=response_time_data_file_path)
        if not response_time_data_file_path_exist:
            # If file does not exist then create it.
            FileManager.create_new_file(response_time_data_file_path)
            FileManager.set_file_permission(response_time_data_file_path)
            FileManager.save(data={
                "id": item_id,
                "elapsed_sums": elapsed_time,
                "elapsed_count": 1
            }, path=response_time_data_file_path)
            # since it's our first entry, the average is the current elapsed time
            elapsedTimeAverage = elapsed_time
        else:
            # Retrieve the elapsed time DIVIDE by count
            response_time_data = FileManager.get_response_time_data(response_time_data_file_path)
            # total counts
            elapsed_times_count = response_time_data["elapsed_count"]
            # sum of all times
            elapsed_times_sum = response_time_data["elapsed_sums"]
            # calculated average
            elapsed_times_average = elapsed_times_sum / elapsed_times_count

            FileManager.update_response_time_data(path=response_time_data_file_path, input_data={
                "id": item_id,
                "elapsed_count": elapsed_times_count + 1,
                "elapsed_sums": elapsed_times_sum + elapsed_time
            })

        alfp_data = alfpDict.get(item_id)
        if alfp_data is None:
            print("Error")
        else:
            print("Success")
        # 10 digit Timestamp 'seconds since epoch' containing time of last
        # Successful Run (and Service update)
        #feedLastUpdateTimestamp = alfp_data["lastUpdateTimestamp"]
        # 10 digit Timestamp 'seconds since epoch' containing time of last
        # Failed run (or Service update failure)
        # feed_last_failure_timestamp = item["lastFailureTimestamp"]
        # 10 digit Timestamp 'seconds since epoch' containing time of last
        # run (having a Success, a Failure, or a No Action flag ('No Data
        # Updates')
        #feedLastRunTimestamp = alfp_data["lastRunTimestamp"]
        # Average number of minutes between each successful run (or Service
        # update)
        #avgUpdateIntervalInMins = alfp_data["avgUpdateIntervalMins"]
        # Average number of minutes between each run
        #avgFeedIntervalInMins = alfp_data["avgFeedIntervalMins"]
        #
        #consecutive_failures_count = alfp_data["consecutiveFailures"]
        #
        #consecutive_failures_threshold = int(value["consecutive_failures_threshold"])
        #
        #alfp_code = alfp_data["lastStatus"]["code"]

        statusCode = StatusManager.get_status_code("000", statusCodesDataModel)

        if all([agol_is_valid, item_is_valid, service_is_valid, layers_are_valid]):
            print("\tAGOL, Item, Service checks normal")

            # 001 Check
            # Check elapsed time between now and the last updated time of the feed
            lastUpdateTimestampDiff = timestamp - alfp_data["lastUpdateTimestamp"]
            # Check elapsed time between now and the last run time of the feed
            lastRunTimestampDiff = timestamp - alfp_data["lastRunTimestamp"]

            # debugging and logging
            p_currentTimeStamp = TimeUtils.convert_from_utc_to_datetime(timestamp)
            p_feedLastUpdateTimestamp = TimeUtils.convert_from_utc_to_datetime(alfp_data["lastUpdateTimestamp"])
            p_lastUpdateTimestampDiff = TimeUtils.convert_from_utc_to_datetime(lastUpdateTimestampDiff)
            print(f"Run time of script:\t\t{p_currentTimeStamp}")
            print(f"Last update of Feed:\t\t{p_feedLastUpdateTimestamp}")
            print(f"Last update timestamp delta:\t{p_lastUpdateTimestampDiff}")

            # If the Difference exceeds the average update interval by an interval of X, flag it
            lastUpdateTimestampDiffMinutes = lastUpdateTimestampDiff / 60
            print(f"Last update timestamp delta:\t{lastUpdateTimestampDiffMinutes} seconds")
            # calculate the threshold
            avgUpdateIntThreshold = int(value["average_update_interval_factor"]) * alfp_data["avgUpdateIntervalMins"]
            print(f"Average update interval threshold: {avgUpdateIntThreshold}")
            if lastUpdateTimestampDiffMinutes > avgUpdateIntThreshold:
                #value["status"]["code"] = "001"
                statusCode = StatusManager.get_status_code("001", statusCodesDataModel)

            # 002 Check
            lastRunTimestampDiffMinutes = lastRunTimestampDiff / 60
            print(f"Last run timestamp delta:\t{lastRunTimestampDiffMinutes} seconds")
            # calculate the threshold
            avgFeedIntThreshold = int(value["average_feed_interval_factor"]) * alfp_data["avgFeedIntervalMins"]
            print(f"Average Feed Interval threshold: {avgFeedIntThreshold}")
            if lastRunTimestampDiffMinutes > avgFeedIntThreshold:
                #item_dict["status"]["code"] = "002"
                statusCode = StatusManager.get_status_code("002", statusCodesDataModel)

            # 003 Check
            if alfp_data["lastStatus"]["code"] == 2:
                if alfp_data["consecutiveFailures"] > int(value["consecutive_failures_threshold"]):
                    #item_dict["status"]["code"] = "003"
                    statusCode = StatusManager.get_status_code("003", statusCodesDataModel)

            # 004 Check
            if alfp_data["lastStatus"]["code"] == 3:
                if alfp_data["consecutiveFailures"] > int(value["consecutive_failures_threshold"]):
                    #item_dict["status"]["code"] = "004"
                    statusCode = StatusManager.get_status_code("004", statusCodesDataModel)

            # 005 Check
            if alfp_data["lastStatus"]["code"] == 1:
                if alfp_data["consecutiveFailures"] > int(value["consecutive_failures_threshold"]):
                    #item_dict["status"]["code"] = "005"
                    statusCode = StatusManager.get_status_code("005", statusCodesDataModel)

            # 006 Check
            if alfp_data["lastStatus"]["code"] == -1:
                #item_dict["status"]["code"] = "006"
                statusCode = StatusManager.get_status_code("006", statusCodesDataModel)

            # 100
            # Check retry count
            if retry_count > int(itemResponse["config"]["default_retry_count"]):
                #item_dict["status"]["code"] = "100"
                statusCode = StatusManager.get_status_code("100", statusCodesDataModel)

            # 101
            # Check elapsed time
            avg_elapsed_time_threshold = float(value["average_elapsed_time_factor"]) * float(elapsedTimeAverage)
            if elapsedTime > avg_elapsed_time_threshold:
                print(f"\telapsed time threshold: {avg_elapsed_time_threshold}")
                #item_dict["status"]["code"] = "101"
                statusCode = StatusManager.get_status_code("101", statusCodesDataModel)

            #statusCode = StatusManager.get_status_code(item_dict["status"]["code"], statusCodesDataModel)
            LoggingUtils.log_status_code_details(statusCode)

        else:
            # If we are at this point, then one or more of the Service
            # states has failed
            #
            # The any() function returns True if any item in an iterable
            # are true, otherwise it returns False.
            if any([agol_is_valid, item_is_valid, service_is_valid]):

                if service_is_valid:
                    print(f"Service | Success")
                    if item_is_valid:
                        print(f"Item | Success | AGOL must be down, then why is the item accessible?")
                    else:
                        # 102
                        statusCode = StatusManager.get_status_code("102", statusCodesDataModel)
                        #item_dict["status"]["code"] = "102"
                        LoggingUtils.log_status_code_details(statusCode)

                    # 201 Check
                    if layers_are_valid is not True:
                        statusCode = StatusManager.get_status_code("201", statusCodesDataModel)
                        #item_dict["status"]["code"] = "201"
                        LoggingUtils.log_status_code_details(statusCode)
                else:
                    # 500
                    if item_is_valid:
                        statusCode = StatusManager.get_status_code("500", statusCodesDataModel)
                        #item_dict["status"]["code"] = "500"
                        LoggingUtils.log_status_code_details(statusCode)
                    else:
                        print(f"Item | Fail")
                        # If ALL of the Service states are False, we have reached
                        # a critical failure in the system
                        statusCode = StatusManager.get_status_code("501", statusCodesDataModel)
                        #item_dict["status"]["code"] = "501"
                        LoggingUtils.log_status_code_details(statusCode)
            else:
                # If ALL of the Service states are False, we have reached
                # a critical failure in the system
                statusCode = StatusManager.get_status_code("501", statusCodesDataModel)
                #item_dict["status"]["code"] = "501"
                LoggingUtils.log_status_code_details(statusCode)
        print()



















    # Create a new directory to hold the rss feeds (if it does not exist)
    rssDirPath = os.path.realpath(ROOT_DIR + r"\rss")
    FileManager.create_new_folder(rssDirPath)

    print("\n=================================================================")
    print(f"Process input data model")
    print("===================================================================")
    outputDataModel = {
        "statusPreparedOn": timestamp,
        "items": []
    }

    for i, ele in enumerate(inputDataModel):
        itemResponse = ele["itemResponse"]
        serviceResponse = ele["serviceResponse"]
        usageResponse = ele["usageResponse"]
        layerResponse = ele["layerResponse"]
        alfpResponse = ele["alfpResponse"]

        # If we are signed in to the GIS with a token, AGOL is responding to requests
        agolIsValid = True
        # is the item accessible
        itemIsValid = itemResponse["isItemValid"]["success"]
        # is the service accessible
        serviceIsValid = serviceResponse["success"]
        # layers
        layers = layerData[i]
        isLayersValid = ItemHandler.check_layers(layers)

        # ID
        item_id = itemResponse["id"]
        # Item title and snippet
        title = ItemHandler.check_title(input_data=itemResponse, result_set=previousStatusCheckData)
        snippet = ItemHandler.check_summary(input_data=itemResponse, result_set=previousStatusCheckData)
        # elapsed time
        elapsedTime = serviceResponse["elapsedTime"]
        # retry count
        retryCount = serviceResponse["retryCount"]

        # Obtain the total elapsed time and counts
        # response time directory
        responseTimeDataDir = os.path.realpath(ROOT_DIR + r"\ResponseTimeData")
        # Create a new directory if it does not exists
        FileManager.create_new_folder(responseTimeDataDir)
        # path to output file
        responseTimeDataFilePath = os.path.join(responseTimeDataDir, item_id + "." + "json")
        # Check file existence.
        fileExist = FileManager.check_file_exist_by_pathlib(path=responseTimeDataFilePath)
        elapsedTimeCount = 1
        if not fileExist:
            # If file does not exist then create it.
            FileManager.create_new_file(responseTimeDataFilePath)
            FileManager.set_file_permission(responseTimeDataFilePath)
            FileManager.save(data={
                "id": item_id,
                "elapsed_sums": elapsedTime,
                "elapsed_count": 1
            }, path=responseTimeDataFilePath)
            elapsedTimeAverage = elapsedTime / elapsedTimeCount
        else:
            # Retrieve the elapsed time DIVIDE by count
            responseTimeData = FileManager.get_response_time_data(responseTimeDataFilePath)
            # total counts
            elapsedTimesCount = responseTimeData["elapsed_count"]
            # sum of all times
            elapsedTimesTotal = responseTimeData["elapsed_sums"]
            # calculated average
            elapsedTimeAverage = elapsedTimesTotal / elapsedTimesCount

            FileManager.update_response_time_data(path=responseTimeDataFilePath, input_data={
                "id": item_id,
                "elapsed_count": elapsedTimesCount + 1,
                "elapsed_sums": elapsedTimesTotal + elapsedTime
            })

        if alfpResponse["success"]:
            # 10 digit Timestamp 'seconds since epoch' containing time of last
            # Successful Run (and Service update)
            feedLastUpdateTimestamp = alfpResponse["lastUpdateTimestamp"]
            # 10 digit Timestamp 'seconds since epoch' containing time of last
            # Failed run (or Service update failure)
            # feed_last_failure_timestamp = item["lastFailureTimestamp"]
            # 10 digit Timestamp 'seconds since epoch' containing time of last
            # run (having a Success, a Failure, or a No Action flag ('No Data
            # Updates')
            feedLastRunTimestamp = alfpResponse["lastRunTimestamp"]
            # Average number of minutes between each successful run (or Service
            # update)
            avgUpdateIntervalInMins = alfpResponse["avgUpdateIntervalMins"]
            # Average number of minutes between each run
            avgFeedIntervalInMins = alfpResponse["avgFeedIntervalMins"]
            #
            consecutive_failures_count = alfpResponse["consecutiveFailures"]
            #
            consecutive_failures_threshold = int(itemResponse["config"]["consecutiveErrorsThreshold"])
            #
            alfp_code = alfpResponse["alf_status"]["code"]

            print(f"\n\n{item_id}\t{title}")
            print(f"\t{item_id}\t{snippet}")
            print(f"\telapsed time  {elapsedTime}")
            print(f"\tretry count   {retryCount}")

            statusCode = StatusManager.get_status_code("000", statusCodesDataModel)

            item_dict = {
                "id": item_id,
                "title": title,
                "snippet": snippet,
                "lastUpdateTime": feedLastUpdateTimestamp,
                "updateRate": avgUpdateIntervalInMins,
                "featureCount": layerResponse["featureCount"],
                "usage": {
                    "trendingCode": serviceResponse["trending"]["code"],
                    "percentChange": serviceResponse["trending"]["percent_change"],
                    "usageCounts": serviceResponse["trending"]["counts"]
                },
                "status": {
                    "code": "000"
                }
            }
        else:
            item_dict = {
                "id": item_id,
                "title": title,
                "snippet": snippet,
                "lastUpdateTime": 0,
                "updateRate": 0,
                "featureCount": layerResponse["featureCount"],
                "usage": {
                    "trendingCode": serviceResponse["trending"]["code"],
                    "percentChange": serviceResponse["trending"]["percent_change"],
                    "usageCounts": serviceResponse["trending"]["counts"]
                },
                "status": {
                    "code": "000"
                }
            }

        # The all() function returns True if all items in an iterable are
        # True, otherwise it returns False.
        if all([agolIsValid, itemIsValid, serviceIsValid, isLayersValid]):
            print("\tAGOL, Item, Service checks normal")

            # 001 Check
            # Check elapsed time between now and the last updated time of the feed
            lastUpdateTimestampDiff = outputDataModel["statusPreparedOn"] - feedLastUpdateTimestamp
            lastRunTimestampDiff = outputDataModel["statusPreparedOn"] - feedLastRunTimestamp

            # debugging and logging
            p_currentTimeStamp = TimeUtils.convert_from_utc_to_datetime(outputDataModel['statusPreparedOn'])
            p_feedLastUpdateTimestamp = TimeUtils.convert_from_utc_to_datetime(feedLastUpdateTimestamp)
            p_lastUpdateTimestampDiff = TimeUtils.convert_from_utc_to_datetime(lastUpdateTimestampDiff)
            print(f"Run time of script:\t\t{p_currentTimeStamp}")
            print(f"Last update of Feed:\t\t{p_feedLastUpdateTimestamp}")
            print(f"Last update timestamp delta:\t{p_lastUpdateTimestampDiff}")

            # If the Difference exceeds the average update interval by an interval of X, flag it
            lastUpdateTimestampDiffMinutes = lastUpdateTimestampDiff / 60
            print(f"Last update timestamp delta:\t{lastUpdateTimestampDiffMinutes} seconds")
            # calculate the threshold
            avgUpdateIntThreshold = int(itemResponse["config"]["averageUpdateIntervalFactor"]) * avgUpdateIntervalInMins
            print(f"Average update interval threshold: {avgUpdateIntThreshold}")
            if lastUpdateTimestampDiffMinutes > avgUpdateIntThreshold:
                item_dict["status"]["code"] = "001"

            # 002 Check
            lastRunTimestampDiffMinutes = lastRunTimestampDiff / 60
            print(f"Last run timestamp delta:\t{lastRunTimestampDiffMinutes} seconds")
            # calculate the threshold
            avgFeedIntThreshold = int(itemResponse["config"]["averageFeedIntervalFactor"]) * avgFeedIntervalInMins
            print(f"Average Feed Interval threshold: {avgFeedIntThreshold}")
            if lastRunTimestampDiffMinutes > avgFeedIntThreshold:
                item_dict["status"]["code"] = "002"

            print(f"ALF Processor status code: {alfp_code}")
            print(f"Consecutive Failures: {consecutive_failures_count}")

            # 003 Check
            if alfp_code == 2:
                if consecutive_failures_count > consecutive_failures_threshold:
                    item_dict["status"]["code"] = "003"

            # 004 Check
            if alfp_code == 3:
                if consecutive_failures_count > consecutive_failures_threshold:
                    item_dict["status"]["code"] = "004"

            # 005 Check 
            if alfp_code == 1:
                if consecutive_failures_count > consecutive_failures_threshold:
                    item_dict["status"]["code"] = "005"

            # 006 Check
            if alfp_code == -1:
                item_dict["status"]["code"] = "006"

            # 100
            # Check retry count
            if "retryCount" in retryCount:
                if retryCount["retryCount"] > int(itemResponse["config"]["default_retry_count"]):
                    item_dict["status"]["code"] = "100"

            # 101
            # Check elapsed time
            avg_elapsed_time_threshold = float(itemResponse["config"]["averageElapsedTimeFactor"]) * float(
                elapsedTimeAverage)
            if elapsedTime > avg_elapsed_time_threshold:
                print(f"\telapsed time threshold: {avg_elapsed_time_threshold}")
                item_dict["status"]["code"] = "101"

            statusCode = StatusManager.get_status_code(item_dict["status"]["code"], statusCodesDataModel)
            LoggingUtils.log_status_code_details(statusCode)

        else:
            # If we are at this point, then one or more of the Service 
            # states has failed
            #
            # The any() function returns True if any item in an iterable
            # are true, otherwise it returns False.
            if any([agolIsValid, itemIsValid, serviceIsValid]):

                if serviceIsValid:
                    print(f"Service | Success")
                    if itemIsValid:
                        print(f"Item | Success | AGOL must be down, then why is the item accessible?")
                    else:
                        # 102
                        statusCode = StatusManager.get_status_code("102", statusCodesDataModel)
                        item_dict["status"]["code"] = "102"
                        LoggingUtils.log_status_code_details(statusCode)

                    # 201 Check
                    if isLayersValid is not True:
                        statusCode = StatusManager.get_status_code("201", statusCodesDataModel)
                        item_dict["status"]["code"] = "201"
                        LoggingUtils.log_status_code_details(statusCode)
                else:
                    # 500
                    if itemIsValid:
                        statusCode = StatusManager.get_status_code("500", statusCodesDataModel)
                        item_dict["status"]["code"] = "500"
                        LoggingUtils.log_status_code_details(statusCode)
                    else:
                        print(f"Item | Fail")
                        # If ALL of the Service states are False, we have reached
                        # a critical failure in the system
                        statusCode = StatusManager.get_status_code("501", statusCodesDataModel)
                        item_dict["status"]["code"] = "501"
                        LoggingUtils.log_status_code_details(statusCode)
            else:
                # If ALL of the Service states are False, we have reached
                # a critical failure in the system
                statusCode = StatusManager.get_status_code("501", statusCodesDataModel)
                item_dict["status"]["code"] = "501"
                LoggingUtils.log_status_code_details(statusCode)

        # append to output data model
        outputDataModel["items"].append(item_dict)

        print(f"Process RSS Feed")
        # TODO Clean!
        # path to RSS output file
        rssFilePath = os.path.join(rssDirPath, item_id + "." + "rss")
        # Check if the file already exist
        rssFileExist = FileManager.check_file_exist_by_pathlib(path=rssFilePath)
        if rssFileExist:
            # If the file exist, check the status
            previousStatus = FileManager.get_status_from_feed(rssFilePath)
            if previousStatus == statusCode["Description of Condition"]:
                print(f"RSS FEED status: {statusCode['Description of Condition']}")
            else:
                # If the new status is different than what is on file, update the feed
                FileManager.create_new_file(rssFilePath)
                FileManager.set_file_permission(rssFilePath)
                feed = FeedGenerator.Feed(rss="2.0",
                                          channel="",
                                          channelTitle=title + " - ArcGIS Living Atlas of the World, Esri",
                                          channelLink="https://www.arcgis.com",
                                          channelDescription=snippet,
                                          webmaster="livingatlas_admins@esri.com",
                                          ttl="",
                                          pubDate=timeUtilsResponse["datetimeObj"].strftime("%m/%d/%Y, %H:%M:%S"),
                                          item="",
                                          itemTitle=title + " - ArcGIS Living Atlas of the World, Esri",
                                          itemLink="https://www.esri.com",
                                          itemDescription=statusCode["Description of Condition"])
                dataSerializer = FeedGenerator.DataSerializer()
                elementTree = dataSerializer.serialize(feed, "XML")
                elementTree.write(rssFilePath, encoding="UTF-8", xml_declaration=True)
        else:
            # The RSS file does not already exists, create a new RSS file
            feed = FeedGenerator.Feed(rss="2.0",
                                      channel="",
                                      channelTitle=title + " - ArcGIS Living Atlas of the World, Esri",
                                      channelLink="https://www.arcgis.com",
                                      channelDescription=snippet,
                                      webmaster="livingatlas_admins@esri.com",
                                      ttl="",
                                      pubDate=timeUtilsResponse["datetimeObj"].strftime("%m/%d/%Y, %H:%M:%S"),
                                      item="",
                                      itemTitle=title + " - ArcGIS Living Atlas of the World, Esri",
                                      itemLink="https://www.esri.com",
                                      itemDescription=statusCode["Description of Condition"])
            dataSerializer = FeedGenerator.DataSerializer()
            elementTree = dataSerializer.serialize(feed, "XML")
            elementTree.write(rssFilePath, encoding="UTF-8", xml_declaration=True)

    print("\n=================================================================")
    print("Saving results")
    print(f"Output file path: {outputFilePath}")
    print("===================================================================")
    # If file do not exist then create it.
    if not fileExist:
        FileManager.create_new_file(outputFilePath)
        FileManager.set_file_permission(outputFilePath)
    else:
        # open file
        print()
    FileManager.save(data=outputDataModel, path=outputFilePath)
