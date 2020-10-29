import arcgis
import json


def validate_items(gis: arcgis.gis.GIS = None, items=None) -> list:
    """ 
    Accepts a list of item Ids and retrieves the item in ArcGIS Online
    as well as the item's layers and returns a list of the item's
    service URL and layer URLs

    Validation Rule:
    1) Is the item accessible
    2) Is the item's ID valid
    """
    if items is None:
        items = []

    def apply(item):
        # item ID on file
        item_id = item["id"]
        # Item's service url stored on file
        config_item_url = item["service_url"]

        print(f"\nValidating Item: {item_id}")

        result = {
            "id": item_id,
            "agolItem": None,
            "config": {
                "averageUpdateIntervalFactor": item["average_update_interval_factor"],
                "averageFeedIntervalFactor": item["average_feed_interval_factor"],
                "averageElapsedTimeFactor": item["average_elapsed_time_factor"],
                "consecutiveErrorsThreshold": item["consecutive_failures_threshold"]
            },
            "queryParams": {
                "url": config_item_url,
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
            agol_item = gis.content.get(item_id)
            if agol_item is None:
                print(f"ERROR\t{item_id} is invalid or item is inaccessible")
                result["isItemValid"].update({
                    "success": False,
                    "error": {
                        "code": 0,
                        "message": "Item ID is invalid or item is inaccessible"
                    }
                })
                return result
        except Exception as e:
            print(f"ERROR\t{item_id} is having an issue: {e}")
            result["isItemValid"].update({
                "success": False,
                "error": {
                    "code": 1,
                    "message": e
                }
            })
            return result
        else:
            print(f"SUCCESS\t{item_id}")
            print(f"title: {agol_item['title']}")
            print(f"snippet: {agol_item['snippet']}")
            print(f"owner: {agol_item['owner']}")
            print(f"access: {agol_item['access']}")
            # the item is a valid ArcGIS Online item
            if config_item_url == agol_item["url"]:
                config_item_url = agol_item["url"]
            else:
                print(f"WARNING: {item_id}")
                print(f"There is a discrepancy between the item's service URL and the item's URL on file")
                print(f"Item URL\t{item['url']}")
                print(f"Config URL\t{config_item_url}")
            # return a dict that contains the item from AGOL and query params
            # that will be used when we query the item's url
            result["agolItem"] = agol_item
            result["queryParams"]["url"] = config_item_url
            result["isItemValid"].update({
                "success": True
            })
            return result

    return list(map(apply, items))


def validate_service_layers(gis: arcgis.gis.GIS = None, items=None) -> list:
    """ Validate the item service's layers """
    if items is None:
        items = []
    print("\n\n============ Validating layer details")

    def apply(item):
        item_id = item["id"]
        print(f"{item_id}")
        agol_item = item["agolItem"]
        layers = []
        exclusion_list_input = item["exclusionParams"].split(",")
        exclusion_list_input_results = []
        if isinstance(exclusion_list_input[0], str) and len(exclusion_list_input[0]) > 0:
            exclusion_list_input_results = list(map(int, exclusion_list_input))
        try:
            for i, layer in enumerate(agol_item.layers):
                if layer.properties["id"] not in exclusion_list_input_results:
                    print(f"\t{layer.properties['name']}")
                    layers.append({
                        "id": item_id,
                        "name": layer.properties['name'],
                        "success": True,
                        "token": gis._con.token,
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

    return list(map(apply, items))


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


def get_alfp_content(alfp_response=None) -> dict:
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


def check_layers(layers):
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


def check_title(input_data=None, result_set=None) -> str:
    """
    We need to return the item's title from AGOL. However, it the item        
    title is not accessible, we return the title from the previous successful
    run that is on file
    """
    if result_set is None:
        result_set = {}
    if input_data is None:
        input_data = {}
    title = ""
    if input_data["agolItem"] is None:
        for ele in result_set["items"]:
            if ele["id"] == input_data["id"]:
                title = ele["title"]
    else:
        title = input_data["agolItem"].title
    return title


def check_summary(input_data=None, result_set=None) -> str:
    """
    We need to return the item's snippet from AGOL. However, it the item        
    snippet is not accessible, we return the snippet from the previous 
    successful run that is on file
    """
    if result_set is None:
        result_set = {}
    if input_data is None:
        input_data = {}
    snippet = ""
    if input_data["agolItem"] is None:
        for ele in result_set["items"]:
            if ele["id"] == input_data["id"]:
                snippet = ele["snippet"]
    else:
        snippet = input_data["agolItem"].snippet
    return snippet
