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
    import LoggingUtils as LoggingUtils
    import QueryEngine as QueryEngine
    import ServiceValidator as ServiceValidator
    import StatusManager as StatusManager
    import TimeUtils as TimeUtils
    import version as version

    from ConfigManager import ConfigManager
    from UserUtils import User
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


def main():
    # Script version number
    print(f"\nRunning version: {version.version_str}")

    print("\n=================================================================")
    print(f"Loading ini file")
    print("=================================================================")
    # The root directory of the script
    root_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Project Root Directory: {root_dir}\n")

    # Load config ini file
    print("Loading input items from configuration file\n")
    # Routines for handling the loading and parsing of the config ini file
    #
    # A configuration file consists of sections, lead by a "[section]" header,
    # and followed by "name: value" entries, with continuations and such in
    # the style of RFC 822.
    config_ini_manager = ConfigManager(root=root_dir, file_name="config.ini")
    # Items we will analyze
    input_items = config_ini_manager.get_config_data(config_type="items")

    print("\n=================================================================")
    print(f"Authenticate GIS profile")
    print("=================================================================")
    # TODO: Not the best way at all to get the profile property from the config file
    gis_profile = input_items[0]["profile"]
    # initialize GIS object
    gis = arcgis.GIS(profile=gis_profile)
    # initialize User object
    user = gis.users.get(gis_profile)
    if user is None:
        print("You are not signed in")
        # TODO: Exit script gracefully and notify Admin(?)
        # TODO: If user is not signed in we cannot retrieve the statistics
    else:
        # Eye candy
        # Get the installation properties and print to stdout
        install_info = arcpy.GetInstallInfo()
        user_sys = User(user=user, install_info=install_info)
        user_sys.greeting()

    print("\n=================================================================")
    print(f"Hydrating input data model from config file parameters")
    print("=================================================================")
    # Data model
    data_model_dict = {}
    # Number of items we are working with (derived from the config ini)
    item_count = len(input_items)
    if item_count < 1:
        raise ItemCountNotInRangeError(item_count)
    else:
        print(f"There are {item_count} items")
        for input_item in input_items:
            print(f"{input_item['id']}")
            data_model_dict.update({
                input_item["id"]: {**input_item, **{"token": gis._con.token}}
            })

    print("\n=================================================================")
    print(f"Setting up project and checking folders and directories")
    print("=================================================================")
    # Load status codes
    print("Loading status codes configuration file")
    # TODO Move filename to config
    status_code_config_path = os.path.realpath(root_dir + r"\statusCodes.json")
    status_code_json_exist = FileManager.check_file_exist_by_pathlib(path=status_code_config_path)
    if status_code_json_exist is False:
        # TODO: At this point we really cannot move forward
        raise InputFileNotFoundError(status_code_config_path)
    else:
        status_codes_data_model = FileManager.open_file(path=status_code_config_path)

    # Load comments
    # TODO Move filename to config
    admin_comments_file_path = os.path.realpath(root_dir + r"\comments.json")
    admin_comments_file_exist = FileManager.check_file_exist_by_pathlib(path=admin_comments_file_path)
    if admin_comments_file_exist is False:
        # TODO: At this point we really cannot move forward
        raise InputFileNotFoundError(admin_comments_file_path)
    else:
        admin_comments_data_model = FileManager.open_file(path=admin_comments_file_path)

    # retrieve the alf statuses
    print("\nRetrieving and Processing Active Live Feed Processed files")
    alf_processor_queries = list(map(QueryEngine.prepare_alfp_query_params, data_model_dict.items()))
    alf_processor_response = QueryEngine.get_alfp_content(alf_processor_queries)
    alfp_content = list(map(QueryEngine.process_alfp_response, alf_processor_response))
    alfp_dict = {}
    for content in alfp_content:
        # check if there is alfp content was successfully retrieved
        if content["success"]:
            unique_item_key = content["id"]
            alfp_dict.update({
                unique_item_key: content["content"]
            })
        else:
            print(f"ERROR: No ALFP data on record for {content['id']}")

    # Read in the previous status output file
    print("\nLoading output from previous run")
    # TODO Move folder name to config
    output_status_dir_path = os.path.realpath(root_dir + r"\output")
    # Create a new directory if it does not exists
    FileManager.create_new_folder(output_status_dir_path)
    # path to output file
    # TODO Move filename to config
    output_file_path = os.path.realpath(output_status_dir_path + r"\status.json")
    # Check file existence
    file_exist = FileManager.check_file_exist_by_pathlib(path=output_file_path)
    if file_exist:
        # Previous status run output file
        previous_status_output = FileManager.open_file(output_file_path)["items"]
        # iterate through the items in the config file
        for key, value in data_model_dict.items():
            print(f"{key}")
            # iterate through the items in the status file
            for ele in previous_status_output:
                status_file_key = ele["id"]
                # if the item in the config file is also in the previous run, merge the output from the previous run
                if key == status_file_key:
                    merged_dict = {**ele, **value}
                    data_model_dict.update({
                        key: merged_dict
                    })

    # Historical "elapsed times" file directory
    # response time directory
    # TODO Move folder name to config
    response_time_data_dir = os.path.realpath(root_dir + r"\ResponseTimeData")
    # Create a new directory if it does not exists
    FileManager.create_new_folder(response_time_data_dir)

    # Create a new directory to hold the rss feeds (if it does not exist)
    print(f"Creating RSS output folder if it does not exist.")
    # TODO Move folder name to config
    rss_dir_path = os.path.realpath(root_dir + r"\rss")
    FileManager.create_new_folder(rss_dir_path)
    # Load RSS template
    # TODO Move filename to config
    rss_template_path = os.path.realpath(root_dir + r"\rss_template.xml")

    print("\n=================================================================")
    print(f"Current data and time")
    print("=================================================================")
    time_utils_response = TimeUtils.get_current_time_and_date()
    timestamp = time_utils_response["timestamp"]
    print(f"{time_utils_response['datetimeObj']}")

    print("\n=================================================================")
    print(f"Validating item's unique key and meta-data")
    print("=================================================================")
    data_model_dict = ServiceValidator.validate_items(gis=gis, data_model=data_model_dict)

    print("\n=================================================================")
    print(f"Validating services")
    print("=================================================================")
    data_model_dict = ServiceValidator.validate_services(data_model=data_model_dict)

    print("\n=================================================================")
    print(f"Validating layers")
    print("=================================================================")
    data_model_dict = ServiceValidator.validate_layers(data_model=data_model_dict)

    print("\n=================================================================")
    print(f"Retrieve usage statistics")
    print("=================================================================")
    data_model_dict = QueryEngine.get_usage_details(data_model=data_model_dict)

    print("\n=================================================================")
    print(f"Retrieve feature counts")
    print("=================================================================")
    data_model_dict = QueryEngine.get_feature_counts(data_model=data_model_dict)

    print("\n=================================================================")
    print(f"Analyze and process data")
    print("=================================================================")
    for key, value in data_model_dict.items():
        item_id = key
        agol_is_valid = True
        item_is_valid = value["itemIsValid"]
        service_response = value["serviceResponse"]
        service_is_valid = service_response["success"]
        layers_are_valid = value["allLayersAreValid"]

        print(f"{item_id}\t{value['title']}")
        print(f"ArcGIS Online accessible: {agol_is_valid}")
        print(f"Item valid: {item_is_valid}")
        print(f"Service valid: {service_is_valid}")
        print(f"All layers valid: {layers_are_valid}\n")

        print("-------- RETRY COUNT ---------")
        # Process Retry Count
        service_retry_count = QueryEngine.get_retry_count(service_response["retryCount"])
        print(f"Service Retry Count: {service_retry_count}")
        print("------------------------------\n")

        print("-------- ELAPSED TIME --------")
        # Retrieve the elapsed time of the query to the service (not the layers)
        service_elapsed_time = QueryEngine.get_service_elapsed_time(service_is_valid, service_response["response"])
        print(f"Service Elapsed Time: {service_elapsed_time}")
        # Retrieve the average elapsed time of layers for the current service (layers only)
        print(f"Layers Elapsed times (individual)")
        layers_elapsed_time = QueryEngine.get_layers_average_elapsed_time(layers_elapsed_times=value['serviceLayersElapsedTimes'])
        print(f"Layers Elapsed Time (average): {layers_elapsed_time}")
        # Sum up the elapsed time for the service and the layers divided by 2
        # We want the total elapsed time of the layers and the FS
        total_elapsed_time = (service_elapsed_time + layers_elapsed_time)/2
        print(f"Total Elapsed Time average: {total_elapsed_time}")
        print("------------------------------\n\n")

        # Obtain the total elapsed time and counts
        # path to output file
        # This file contains the:
        #   item id
        #   elapsed time
        #   elapsed sums
        response_time_data_file_path = os.path.join(response_time_data_dir, item_id + "." + "json")
        # Check file existence.
        response_time_data_file_path_exist = FileManager.check_file_exist_by_pathlib(path=response_time_data_file_path)

        exclude_save = TimeUtils.is_now_excluded(value["exclude_time_ranges"],
                                                 value["exclude_days"],
                                                 value["exclude_specific_dates"],
                                                 timestamp)
        print(f"Exclude response time data from save: {exclude_save}")

        # Does the file exist
        if not response_time_data_file_path_exist:
            # If file does not exist then create it.
            FileManager.create_new_file(response_time_data_file_path)
            FileManager.set_file_permission(response_time_data_file_path)
            if not exclude_save:
                FileManager.save(data={
                    "id": item_id,
                    "elapsed_sums": total_elapsed_time,
                    "elapsed_count": 1
                }, path=response_time_data_file_path)
            # since it's our first entry, the average is the current elapsed time
            elapsed_times_average = total_elapsed_time
        else:
            # Retrieve the elapsed time DIVIDE by count
            print(f"Retrieving response time data from existing json file: {item_id}.json")
            response_time_data = FileManager.get_response_time_data(response_time_data_file_path)
            # total counts
            elapsed_times_count = response_time_data["elapsed_count"]
            print(f"Elapsed count (on file before update): {elapsed_times_count}")
            # sum of all times
            elapsed_times_sum = response_time_data["elapsed_sums"]
            print(f"Elapsed sums (on file before update): {elapsed_times_sum}")
            # calculated average
            elapsed_times_average = elapsed_times_sum / elapsed_times_count
            print(f"Average from above values: {elapsed_times_average}")
            if not exclude_save:
                # update the response time data file
                FileManager.update_response_time_data(path=response_time_data_file_path, input_data={
                    "id": item_id,
                    "elapsed_count": elapsed_times_count + 1,
                    "elapsed_sums": elapsed_times_sum + total_elapsed_time
                })
        print(f"Elapsed average: {elapsed_times_average}")

        # retrieve alfp details
        alfp_data = alfp_dict.get(item_id)

        if alfp_data is not None:
            # 10 digit Timestamp 'seconds since epoch' containing time of last
            # Successful Run (and Service update)
            value.update({
                "lastUpdateTimestamp": alfp_data.get("lastUpdateTimestamp", 0)
            })
            # 10 digit Timestamp 'seconds since epoch' containing time of last
            # Failed run (or Service update failure)
            # feed_last_failure_timestamp = item["lastFailureTimestamp"]
            # 10 digit Timestamp 'seconds since epoch' containing time of last
            # run (having a Success, a Failure, or a No Action flag ('No Data
            # Updates')
            value.update({
                "lastRunTimestamp": alfp_data.get("lastRunTimestamp", 0)
            })
            # Average number of minutes between each successful run (or Service
            # update)
            value.update({
                "avgUpdateIntervalMins": alfp_data.get("avgUpdateIntervalMins", 0)
            })
            # Average number of minutes between each run
            value.update({
                "avgFeedIntervalMins": alfp_data.get("avgFeedIntervalMins", 0)
            })
            #
            value.update({
                "consecutiveFailures": alfp_data.get("consecutiveFailures", 0)
            })
            #
            value.update({
                "alfpLastStatus": alfp_data["lastStatus"]["code"]
            })
        else:
            value.update({
                "lastUpdateTimestamp": 0,
                "lastRunTimestamp": 0,
                "avgUpdateIntervalMins": 0,
                "avgFeedIntervalMins": 0,
                "consecutiveFailures": 0,
                "alfpLastStatus": 0
            })

        # initialize the status code
        status_code = StatusManager.get_status_code("000", status_codes_data_model)

        if all([agol_is_valid, item_is_valid, service_is_valid, layers_are_valid]):
            print("AGOL, Item, Service checks normal")

            # 001 Check
            print("\nCHECKING     001")
            # Check elapsed time between now and the last updated time of the feed
            last_update_timestamp_diff = timestamp - value.get("lastUpdateTimestamp", timestamp)
            # Check elapsed time between now and the last run time of the feed
            last_run_timestamp_diff = timestamp - value["lastRunTimestamp"]

            # If the Difference exceeds the average update interval by an interval of X, flag it
            last_update_timestamp_diff_minutes = last_update_timestamp_diff / 60
            print(f"Last update timestamp delta:\t{last_update_timestamp_diff_minutes} seconds")
            # Average number of minutes between each successful run (or Service update)
            avg_update_int_threshold = int(value["average_update_interval_factor"]) * value["avgUpdateIntervalMins"]
            print(f"Average update interval threshold: {avg_update_int_threshold}")
            if last_update_timestamp_diff_minutes > avg_update_int_threshold:
                status_code = StatusManager.get_status_code("001", status_codes_data_model)

            print("\nCHECKING     002")
            # 002 Check
            last_run_timestamp_diff_minutes = last_run_timestamp_diff / 60
            print(f"Last run timestamp delta:\t{last_run_timestamp_diff_minutes} seconds")
            # calculate the threshold (Average number of minutes between each run)
            avg_feed_int_threshold = int(value["average_feed_interval_factor"]) * value["avgFeedIntervalMins"]
            print(f"Average Feed Interval threshold: {avg_feed_int_threshold}")
            if last_run_timestamp_diff_minutes > avg_feed_int_threshold:
                status_code = StatusManager.get_status_code("002", status_codes_data_model)

            print("\nCHECKING     003")
            # 003 Check
            if value["alfpLastStatus"] == 2:
                if value["consecutiveFailures"] > int(value["consecutive_failures_threshold"]):
                    status_code = StatusManager.get_status_code("003", status_codes_data_model)

            print("\nCHECKING     004")
            # 004 Check
            if value["alfpLastStatus"] == 3:
                if value["consecutiveFailures"] > int(value["consecutive_failures_threshold"]):
                    status_code = StatusManager.get_status_code("004", status_codes_data_model)

            print("\nCHECKING     005")
            # 005 Check
            if value["alfpLastStatus"] == 1:
                if value["consecutiveFailures"] > int(value["consecutive_failures_threshold"]):
                    status_code = StatusManager.get_status_code("005", status_codes_data_model)

            print("\nCHECKING     006")
            # 006 Check
            if value["alfpLastStatus"] == -1:
                status_code = StatusManager.get_status_code("006", status_codes_data_model)

            print("\nCHECKING     100")
            # 100
            # Check retry count
            if service_retry_count > int(value["default_retry_count"]):
                status_code = StatusManager.get_status_code("100", status_codes_data_model)

            print("\nCHECKING     101")
            # 101
            # Check elapsed time
            avg_elapsed_time_threshold = float(value["average_elapsed_time_factor"]) * float(elapsed_times_average)
            if total_elapsed_time > avg_elapsed_time_threshold:
                status_code = StatusManager.get_status_code("101", status_codes_data_model)

            LoggingUtils.log_status_code_details(item_id, status_code)
        else:
            print("\nCHECKING     102, 201, 500, 501")
            # If we are at this point, then one or more of the Service states has failed
            #
            # The any() function returns True if any item in an iterable are true, otherwise it returns False.
            if any([agol_is_valid, item_is_valid, service_is_valid]):
                if service_is_valid:
                    print(f"Service | Success")
                    if item_is_valid:
                        print(f"Item | Success | AGOL must be down, then why is the item accessible?")
                    else:
                        # 102
                        status_code = StatusManager.get_status_code("102", status_codes_data_model)
                    # 201 Check
                    if layers_are_valid is not True:
                        status_code = StatusManager.get_status_code("201", status_codes_data_model)
                else:
                    # 500
                    if item_is_valid:
                        status_code = StatusManager.get_status_code("500", status_codes_data_model)
                    else:
                        print(f"Item | Fail")
                        # If ALL of the Service states are False, we have reached a critical failure in the system
                        status_code = StatusManager.get_status_code("501", status_codes_data_model)
            else:
                # If ALL of the Service states are False, we have reached a critical failure in the system
                status_code = StatusManager.get_status_code("501", status_codes_data_model)

            LoggingUtils.log_status_code_details(item_id, status_code)

        # update/add status code in the data model
        # Add the Admin comments (if any)
        # Add the last build time
        # Add the status code
        # Add the current run time of the script
        value.update({
            "comments": admin_comments_data_model.get(item_id, []),
            "lastBuildTime": time_utils_response["datetimeObj"].strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "status": status_code,
            "timestamp": timestamp
        })

        print(f"\nProcess RSS Feed")
        # path to RSS output file
        rss_file_path = os.path.join(rss_dir_path, item_id + "." + value["rss_file_extension"])
        # Check if the file already exist
        rss_file_exist = FileManager.check_file_exist_by_pathlib(path=rss_file_path)
        if rss_file_exist:
            # If the file exist, check the status/comments between the item's previous status/code comment, and the
            # current status/code comment
            update_current_feed = StatusManager.update_rss_feed(previous_status_output, value, status_codes_data_model)
            if update_current_feed:
                FileManager.create_new_file(rss_file_path)
                FileManager.set_file_permission(rss_file_path)
                FileManager.dict_to_xml(rss_template_path, value, rss_file_path)
        else:
            # The RSS file does not already exists, create a new RSS file
            FileManager.dict_to_xml(rss_template_path, value, rss_file_path)

    print("\n=================================================================")
    print("Saving results")
    print(f"Output file path: {output_file_path}")
    print("===================================================================")
    # output file
    output_file = {
        "statusPreparedOn": timestamp,
        "items": []
    }
    # hydrate output file
    for key, value in data_model_dict.items():
        output_file["items"].append({
            "id": key,
            "title": value.get("title", value.get("missing_item_title")),
            "snippet": value.get("snippet", value.get("missing_item_snippet")),
            "comments": value.get("comments", ""),
            "lastUpdateTime": value.get("lastUpdateTimestamp", 0),
            "updateRate": value.get("avgUpdateIntervalMins", 0),
            "featureCount": value.get("featureCount", 0),
            "usage": value.get("usage"),
            "status": {
                "code": value["status"]["code"]
            }
        })
    # Pretty print dictionary

    # If file do not exist then create it.
    # TODO Not correct
    if not file_exist:
        FileManager.create_new_file(output_file_path)
        FileManager.set_file_permission(output_file_path)
    else:
        # open file
        print()
    FileManager.save(data=output_file, path=output_file_path)

    print("Script completed...")


if __name__ == "__main__":
    main()
