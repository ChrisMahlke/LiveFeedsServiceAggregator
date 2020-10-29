VERSION = "1.0.0"

import arcgis
import json

def validateItems(gis: arcgis.gis.GIS = None, items: list = []) -> list:
    """ 
    Accepts a list of item Ids and retrieves the item in ArcGIS Online
    as well as the item's layers and returns a list of the item's
    service URL and layer URLs

    Validation Rule:
    1) Is the item accessible
    2) Is the item's ID valid
    """
    def apply(item):
        # item ID on file
        itemId = item["id"]
        # Item's service url stored on file
        configItemTitle = item["item_title"]
        configItemSnippet = item["item_snippet"]
        configItemUrl = item["service_url"]

        print(f"\nValidating Item: {itemId}")

        result = {
            "id": itemId,
            "agolItem": None,
            "config": {
                "averageUpdateIntervalFactor": item["average_update_interval_factor"],
                "averageFeedIntervalFactor": item["average_feed_interval_factor"],
                "averageElapsedTimeFactor": item["average_elapsed_time_factor"],
                "consecutiveErrorsThreshold": item["consecutive_failures_threshold"]
            },
            "queryParams": {
                "url": configItemUrl,
                "params": {},
                "addToken": True,
                "retryFactor": item["default_retry_count"],
                "timeoutFactor": item["default_timeout"],
                "tryJson": True,
                "token": gis._con.token
            },
            "usageParams": {
                "usageDataRange": item["usage_data_range"]
            },
            "exclusionParams": item["exclusion"],
            "isItemValid": {}
        }

        try:
            agolItem = gis.content.get(itemId)
            if agolItem is None:
                print(f"ERROR\t{itemId} is invalid or item is inaccessible")
                result["isItemValid"].update({
                    "success": False,
                    "error": {
                        "code": 0,
                        "message": "Item ID is invalid or item is inaccessible"
                    }
                })
                return result
        except Exception as e:
            print(f"ERROR\t{itemId} is having an issue: {e}")
            result["isItemValid"].update({
                "success": False,
                "error": {
                    "code": 1,
                    "message": e
                }
            })
            return result
        else:
            print(f"SUCCESS\t{itemId}")
            print(f"title: {agolItem['title']}")
            print(f"snippet: {agolItem['snippet']}")
            print(f"owner: {agolItem['owner']}")
            print(f"access: {agolItem['access']}")
            # the item is a valid ArcGIS Online item
            if configItemUrl == agolItem["url"]:
                configItemUrl = agolItem["url"]
            else:
                print(f"WARNING: {itemId}")
                print(f"There is a discrepency between the item's service URL and the item's URL on file")
                print(f"Item URL\t{item['url']}")
                print(f"Config URL\t{configItemUrl}")
            # return a dict that contains the item from AGOL and query params
            # that will be used when we query the item's url
            result["agolItem"] = agolItem
            result["queryParams"]["url"] = configItemUrl
            result["isItemValid"].update({
                "success": True
            })
            return result
    return list(map(apply, items))

def validateServiceLayers(gis: arcgis.gis.GIS = None, items: list = []) -> list:
    """ Validate the item service's layers """
    print("\n\n============ Validating layer details")
    def apply(item):
        print(f"{item['id']}")
        agolItem = item["agolItem"]
        layers = []
        exclusionListInput = item["exclusionParams"].split(",")
        exclusionListInputResults = []
        if isinstance(exclusionListInput[0], str) and len(exclusionListInput[0]) > 0:
            exclusionListInputResults = list(map(int, exclusionListInput))
        try:
            for i, layer in enumerate(agolItem.layers):
                if i not in exclusionListInputResults:
                    print(f"\t{layer.properties['name']}")
                    layers.append({
                        "id": item["id"],
                        "name" : layer.properties['name'],
                        "success": True,
                        "token": gis._con.token,
                        "url" : layer.url
                    })
        except Exception as e:
            print(f"\t{e}")
            layers.append({
                "id": item["id"],
                "success": False,
                "message": e
            })
            return layers
        else:
            return layers

    return list(map(apply, items))

def prepareLayerQueryParams(layers: list = []) -> list:
    # we need to check if the item's service is valid
    # the item can be accessbile in AGOL, but the service url could be down
    
    # check the item's layers (if valid)
    # Same as above, the service URL could be accessible, but the layers
    # may not be accessible
    layerData = []
    for layer in layers:
        itemId = layer["id"]
        if layer["success"]:
            layerName = layer["name"]
            layerUrl = layer["url"]
            layerData.append({
                "id": itemId,
                "layerName": layerName,
                "url": layerUrl + "/query",
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
            layerData.append({
                "id": itemId,
                "success": False
            })
    return layerData

def getAlfProcessorContent(alfp_response: dict = []) -> dict:
    """ """
    if alfp_response["response"]["success"]:
        itemID = alfp_response["id"]
        print(f"{itemID}")
        if alfp_response["response"]["response"].status_code == 200:
            content = json.loads(alfp_response["response"]["response"].content.decode('utf-8'))
            return {
                "id": itemID,
                "content": content,
                "success": True
            }
        else:
            status_code = alfp_response["response"]["response"].status_code
            reason = alfp_response["response"]["response"].reason
            return {
                "id": itemID,
                "status_code": status_code,
                "reason": reason,
                "success": False
            }

def checkLayers(layers):
    layer_check_list = []
    for layer in layers:
        if layer["success"]:
            layer_check_list.append(True)
        else:
            layer_check_list.append(False)
    if len(layer_check_list) > 0:
        if all(layer_check_list):
            return True
        else:
            return False
    else:
        return false

def checkTitle(input: dict = {}, resultSet: dict = {}) -> str:
    """
    We need to return the item's title from AGOL. However, it the item        
    title is not accessible, we return the title from the previous successful
    run that is on file
    """
    title = ""
    if input["agolItem"] is None:
        for ele in resultSet["items"]:
            if ele["id"] == input["id"]:
                title = ele["title"]
    else:
        title = input["agolItem"].title
    return title

def checkItemSummary(input: dict = {}, resultSet: dict = {}) -> str:
    """
    We need to return the item's snippet from AGOL. However, it the item        
    snippet is not accessible, we return the snippet from the previous 
    successful run that is on file
    """
    snippet = ""
    if input["agolItem"] is None:
        for ele in resultSet["items"]:
            if ele["id"] == input["id"]:
                snippet = ele["snippet"]
    else:
        snippet = input["agolItem"].snippet
    return snippet
