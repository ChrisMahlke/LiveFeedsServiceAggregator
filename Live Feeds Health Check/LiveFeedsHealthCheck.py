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
"""LiveFeedsHealthCheck"""

VERSION = "1.0.0"

try:
    import arcgis
    import arcpy
    import json
    import os

    import FileManager as FileManager
    import ItemHandler as ItemHandler
    import LoggingUtils as LoggingUtils
    import ModelUtils as ModelUtils
    import RequestUtils as RequestUtils
    import Serializer as Serializer
    import StatusManager as StatusManager
    import TimeUtils as TimeUtils

    from ConfigManager import ConfigManager
    from UserUtils import User
    from collections import defaultdict
except ImportError as e:
    print(f"Impoert Error: {e}")

if __name__ == "__main__":
    print("=================================================================")
    print(f"Setting up project and checking folders and directories")
    print("=================================================================")
    # get the current date and time
    timeUtilsResponse = TimeUtils.getCurrentTimestamp()
    timestamp = timeUtilsResponse["timestamp"]

    # The root directory of the script
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    print(f"Root Directory: {ROOT_DIR}")

    # Read in the input items data model
    configIniManager = ConfigManager(root=ROOT_DIR, fileName="config.ini")
    itemsDataModel = configIniManager.getConfigData(configType="items")
    if len(itemsDataModel) < 1:
        print(f"ERROR: Either there are no items in the config file, or the config file has not been loaded!")

    # Read in the status codes data model
    # statusCodesManager = ConfigManager(root=ROOT_DIR, fileName="statusCodes.ini")
    # statusCodesDataModel = statusCodesManager.getConfigData(configType="statusCodes")
    statusCodeConfigPath = ROOT_DIR + r"\statusCodes.json"
    statusCodeJsonExist = FileManager.checkFileExistByPathlib(path=statusCodeConfigPath)
    statusCodesDataModel = None
    if statusCodeJsonExist is False:
        print(f"ERROR: The status code file is not available or inaccessible!")
    else:
        statusCodesDataModel = FileManager.loadStatusConfigData(path=statusCodeConfigPath)

    # Create a new directory to hold the rss feeds (if it does not exist)
    rssDirPath = os.path.realpath(ROOT_DIR + r"\rss")
    FileManager.createNewFolder(rssDirPath)

    # Read in the previous status output file
    # output folder path for output file
    outputStatusDirPath = os.path.realpath(ROOT_DIR + r"\output")
    # Create a new directory if it does not exists
    FileManager.createNewFolder(outputStatusDirPath)
    # path to output file
    outputFilePath = outputStatusDirPath + r"\status.json"
    # Check file existence.
    fileExist = FileManager.checkFileExistByPathlib(path=outputFilePath)
    previousStatusCheckData = {}
    if fileExist:
        previousStatusCheckData = FileManager.getResponseTimeData(outputFilePath)

    print("\n=================================================================")
    print(f"Authenticate GIS profile")
    print("=================================================================")
    # TODO: Not the best way at all to get the profile property from the config file
    gisProfile = itemsDataModel[0]["profile"]
    # initialize GIS object
    GIS = arcgis.GIS(profile=gisProfile)
    # initialize User object
    USER = GIS.users.get(gisProfile)
    if USER is None:
        print("You are not signed in")
        # TODO: Exit script gracefully and notify Admin
    else:
        # get the installation properties and print to stdout
        INSTALL_INFO = arcpy.GetInstallInfo()
        USER_SYS = User(user=USER, installInfo=INSTALL_INFO)
        USER_SYS.greeting()

    print("\n=================================================================")
    print(f"Hydrating input data model")
    print("===================================================================")
    # create the in-memory data model with the current UTC time and an empy
    # list to hold the health and status of each Live Feed (or service)
    inputDataModel = {
        "statusPreparedOn" : timestamp,
        "items" : []
    }

    # Initialize the input data model with item ID's from the config file
    inputDataModel["items"] = list(ModelUtils.hydrateDataModel(inputConfig=itemsDataModel))

    print("\n=================================================================")
    print(f"Validating item meta-data")
    print("===================================================================")
    # Item validation
    validatedItems = ItemHandler.validateItems(gis=GIS, items=itemsDataModel)
    print(f"Item meta-data validation completed")

    print("\n=================================================================")
    print(f"Validating item service response data")
    print("===================================================================")
    # For each item check the item's service
    validatedServiceResponses = RequestUtils.validateServiceUrls(items=validatedItems)
    # update data model with validated services
    validatedServices = ModelUtils.updateDataModelWithServiceResponses(inputData=validatedServiceResponses)

    print("\n=================================================================")
    print(f"Validating item usage details")
    print("===================================================================")
    validatedUsageDetailsResponse = RequestUtils.validateUsageDetails(items=validatedServices)
    # UPDATE data model with usage details
    validatedUsageDetails = ModelUtils.updateDataModelWithUsageDetails(dataModel=inputDataModel, inputData=validatedUsageDetailsResponse)

    print("\n=================================================================")
    print(f"Retrieving layer data to derive feature counts")
    print("===================================================================")
    # Retrieve layer data for each service, this will be used to derive the
    # feature count for each service
    layerData = ItemHandler.validateServiceLayers(gis=GIS, items=validatedItems)
    # Prepare the layers for querying
    layerInputQueryParams = list(map(ItemHandler.prepareLayerQueryParams, layerData))
    # UPDATE data model with feature counts
    allFeatureCounts = RequestUtils.getAllFeatureCounts(inputLayerData=layerInputQueryParams)
    validatedLayers = ModelUtils.updateDataModelWithFeatureCount(inputDataModel=validatedUsageDetails, totalFeatureCounts=allFeatureCounts)

    print("\n=================================================================")
    print(f"Integrating ALF Processor results")
    print("===================================================================")
    # retrieve the alf statuses
    alfProcessorQueries = list(map(RequestUtils.prepareAlfProcessoerQueryParams, inputDataModel["items"]))
    alfProcessorResponse = RequestUtils.getAlfProcessorContent(alfProcessorQueries)

    inputDataModel = ModelUtils.updateDataModelWithAlfProcessorContent(data_model=validatedLayers, inputData=alfProcessorResponse)

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
        isLayersValid = ItemHandler.checkLayers(layers)

        # ID
        id = itemResponse["id"]
        # Item title and snippet
        title = ItemHandler.checkTitle(input=itemResponse, resultSet=previousStatusCheckData)
        snippet = ItemHandler.checkItemSummary(input=itemResponse, resultSet=previousStatusCheckData)
        # elapsed time
        elapsedTime = serviceResponse["ellapsedTime"]
        # retry count
        retryCount = serviceResponse["retryCount"]

        # Obtain the total elapsed time and counts
        # response time directory
        responseTimeDataDir = os.path.realpath(ROOT_DIR + r"\ResponseTimeData")
        # Create a new directory if it does not exists
        FileManager.createNewFolder(responseTimeDataDir)
        # path to output file
        responseTimeDataFilePath = os.path.join(responseTimeDataDir, id + "." + "json")
        # Check file existence.
        fileExist = FileManager.checkFileExistByPathlib(path=responseTimeDataFilePath)
        elapsedTimeCount = 1
        if (not fileExist):
            # If file does not exist then create it.
            FileManager.createNewFile(responseTimeDataFilePath)
            FileManager.setFilePermission(responseTimeDataFilePath)
            FileManager.save(data={
                "id" : id,
                "elapsed_sums": elapsedTime,
                "elapsed_count": 1
            }, path=responseTimeDataFilePath)
            elapsedTimeAverage = elapsedTime/elapsedTimeCount
        else:
            # Retreive the elapsed time DIVIDE by count
            responseTimeData = FileManager.getResponseTimeData(responseTimeDataFilePath)
            # total counts
            elapsedTimesCount = responseTimeData["elapsed_count"]
            # sum of all times
            elapsedTimesTotal = responseTimeData["elapsed_sums"]
            #calculated average
            elapsedTimeAverage = elapsedTimesTotal/elapsedTimesCount

            FileManager.updateResponseTimeData(path=responseTimeDataFilePath, inputData={
                "id": id,
                "elapsed_count": elapsedTimesCount + 1,
                "elapsed_sums": elapsedTimesTotal + elapsedTime
            })

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
        consecutiveFailuers = alfpResponse["consecutiveFailures"]

        print(f"\n\n{id}\t{title}")
        print(f"\t{id}\t{snippet}")
        print(f"\telapsed time  {elapsedTime}")
        print(f"\tretry count   {retryCount}")

        statusCode = StatusManager.getStatusCode("000", statusCodesDataModel)

        item_dict = {
            "id": id,
            "title": title,
            "snippet": snippet,
            "lastUpdateTime": feedLastUpdateTimestamp,
            "updateRate": avgUpdateIntervalInMins,
            "featureCount": layerResponse["featureCount"],
            "usage": {
                "trendingCode" : serviceResponse["trending"]["code"],
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
            p_currentTimeStamp = TimeUtils.convertFromUtcToDateTime(outputDataModel['statusPreparedOn'])
            p_feedLastUpdateTimestamp = TimeUtils.convertFromUtcToDateTime(feedLastUpdateTimestamp)
            p_lastUpdateTimestampDiff = TimeUtils.convertFromUtcToDateTime(lastUpdateTimestampDiff)
            print(f"\tRun time of script:\t\t{p_currentTimeStamp}")
            print(f"\tLast update of Feed:\t\t{p_feedLastUpdateTimestamp}")
            print(f"\tLast update timestamp delta:\t{p_lastUpdateTimestampDiff}")

            # If the Difference exceeds the average update interval by an interval of X, flag it
            lastUpdateTimestampDiffMinutes = lastUpdateTimestampDiff/60
            print(f"\tLast update timestamp delta:\t{lastUpdateTimestampDiffMinutes} seconds")
            # calculate the threshold
            avgUpdateIntThreshold = int(itemResponse["config"]["averageUpdateIntervalFactor"]) * avgUpdateIntervalInMins
            print(f"\tAverage update interval threshold: {avgUpdateIntThreshold}")
            if lastUpdateTimestampDiffMinutes > avgUpdateIntThreshold:
                item_dict["status"]["code"] = "001"

            # 002 Check
            lastRunTimestampDiffMinutes = lastRunTimestampDiff/60
            print(f"\tLast run timestamp delta:\t{lastRunTimestampDiffMinutes} seconds")
            # calculate the threshold
            avgFeedIntThreshold = int(itemResponse["config"]["averageFeedIntervalFactor"]) * avgFeedIntervalInMins
            print(f"\tAverage Feed Interval threshold: {avgFeedIntThreshold}")
            if lastRunTimestampDiffMinutes > avgFeedIntThreshold:
                item_dict["status"]["code"] = "002"
                    
            alfp_code = alfpResponse["alf_status"]["code"]
            print(f"\tALF Processor status code: {alfp_code}")
            print(f"Consecutive Failuers: {alfpResponse['consecutiveFailures']}")
            # 003 Check
            if alfp_code == 2:
                if alfpResponse["consecutiveFailures"] > int(itemResponse["config"]["consecutiveErrorsThreshold"]):
                    item_dict["status"]["code"] = "003"

            # 004 Check
            if alfp_code == 3:
                if alfpResponse["consecutiveFailures"] > int(itemResponse["config"]["consecutiveErrorsThreshold"]):
                    item_dict["status"]["code"] = "004"

            # 005 Check 
            if alfp_code == 1:
                if alfpResponse["consecutiveFailures"] > int(itemResponse["config"]["consecutiveErrorsThreshold"]):
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
            avg_elapsed_time_threshold = float(itemResponse["config"]["averageElapsedTimeFactor"]) * float(elapsedTimeAverage)
            if elapsedTime > avg_elapsed_time_threshold:
                print(f"\telapsed time threshold: {avg_elapsed_time_threshold}")
                item_dict["status"]["code"] = "101"
                
            statusCode = StatusManager.getStatusCode(item_dict["status"]["code"], statusCodesDataModel)
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
                        statusCode = StatusManager.getStatusCode("102", statusCodesDataModel)
                        item_dict["status"]["code"] = "102"
                        LoggingUtils.log_status_code_details(statusCode)

                    # 201 Check
                    if isLayersValid is not True:
                        statusCode = StatusManager.getStatusCode("201", statusCodesDataModel)
                        item_dict["status"]["code"] = "201"
                        LoggingUtils.log_status_code_details(statusCode)
                else:
                    # 500
                    if itemIsValid:
                        statusCode = StatusManager.getStatusCode("500", statusCodesDataModel)
                        item_dict["status"]["code"] = "500"
                        LoggingUtils.log_status_code_details(statusCode)
                    else:
                        print(f"Item | Fail")
            else:
                # If ALL of the Service states are False, we have reached
                # a critical failure in the system
                statusCode = StatusManager.getStatusCode("501", statusCodesDataModel)
                item_dict["status"]["code"] = "501"
                LoggingUtils.log_status_code_details(statusCode)
            
        # append to output data model
        outputDataModel["items"].append(item_dict)


        print(f"Process RSS Feed")
        # path to RSS output file
        rssFilePath = os.path.join(rssDirPath, id + "." + "rss")
        # Check if the file already exist
        rssFileExist = FileManager.checkFileExistByPathlib(path=rssFilePath)
        if rssFileExist:
            # If the file exist, check the status
            previousStatus = FileManager.getStatusFromFeed(rssFilePath)
            if previousStatus == statusCode["Description of Condition"]:
                print(f"RSS FEED status: {statusCode['Description of Condition']}")
            else:
                # If the new status is different than what is on file, update the feed
                FileManager.createNewFile(rssFilePath)
                FileManager.setFilePermission(rssFilePath)
                feed = Serializer.Feed(rss="2.0", 
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
                dataSerializer = Serializer.DataSerializer()
                elementTree = dataSerializer.serialize(feed, "XML")
                elementTree.write(rssFilePath, encoding="UTF-8", xml_declaration=True)
        else:
            # The RSS file does not already exists, create a new RSS file
            feed = Serializer.Feed(rss="2.0", 
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
            dataSerializer = Serializer.DataSerializer()
            elementTree = dataSerializer.serialize(feed, "XML")
            elementTree.write(rssFilePath, encoding="UTF-8", xml_declaration=True)
        

    print("\n=================================================================")
    print("Saving results")
    print(f"Output file path: {outputFilePath}")
    print("===================================================================")
    # If file do not exist then create it.
    if (not fileExist):
        FileManager.createNewFile(outputFilePath)
        FileManager.setFilePermission(outputFilePath)
    else:
        # open file
        print()
    FileManager.save(data=outputDataModel, path=outputFilePath)