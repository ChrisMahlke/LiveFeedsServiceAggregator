"""
ServiceValidator

Validate item
---------------------------
- Requirements for check
Item ID

- Results
Success -   Item is accessible in ArcGIS Online
            Obtain meta-data (Title, Snippet)
            Validate service
            Validate layers
            Obtain usage statistics
            Obtain feature counts
Error   -   Item is either Private or Invalid
            Does not exist
            Validate service
            Validate layers
            Use meta-data from previous run (do not over-write data model)
            Use usage statistics from previous run (do not over-write data model)

Validate service
---------------------------
- Requirements for check
If the item it not accessible, the service url on file (config file) can be used

- Results
Success -   Record response
            Run checks against alfp results
            Validate layers
Error   -   Use feature counts from previous run (do not over-write data model)

Validate service layers
---------------------------
- Requirements for check
Service url on the item or on file must be accessible

- Results
Success -   Obtain feature counts
Error   -   Use feature counts from previous run (do not over-write data model)

Validate usage statistics
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
import arcgis
import json
import RequestUtils as RequestUtils


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
        """
        Validate an item's ID and retrieve its meta-data.  If the item is not accessible and it's already in the
        previous run then propagate the meta-data from the previous run.
        :param current_item: The current item ID
        :return: Dictionary
        """
        # the item ID
        item_id = current_item[0]
        # the item ID params from the config file and the content from the previous run (if it exist)
        item_content = current_item[1]
        # initialize the values
        title = item_content.get("title", "")
        snippet = item_content.get("snippet", "")
        service_url = item_content.get("service_url", "")
        validated_item_dict = {
            "title": title,
            "snippet": snippet,
            "service_url": service_url,
            "agolItem": None,
            "itemIsValid": False
        }
        try:
            agol_item = gis.content.get(item_id)
            if agol_item is None:
                # The item ID is invalid
                current_item[1].update(validated_item_dict)
                print(f"{item_id} is invalid.")
        except Exception as e:
            # The item ID is valid, however, not accessible
            current_item[1].update(validated_item_dict)
            print(f"{item_id} is inaccessible: {e}")
        else:
            # The item is a valid accessible item in ArcGIS Online
            # Fetch the item's title and snippet
            title = agol_item["title"]
            snippet = agol_item["snippet"]
            service_url = agol_item["url"]
            validated_item_dict.update({
                "title": title,
                "snippet": snippet,
                "service_url": service_url,
                "agolItem": agol_item,
                "itemIsValid": True
            })
            current_item[1].update(validated_item_dict)
            print(f"{item_id}")
        finally:
            return current_item[0], current_item[1]

    return dict(map(validate_item, data_model.items()))


def validate_services(data_model=None) -> dict:
    """
    Validate all the services on the input data model
    :param data_model:
    :return: Updated data model with the results of the validated services
    """
    if data_model is None:
        data_model = {}

    def validate_service(current_item):
        """
        Validate a single service
        :param current_item: Input item/service
        :return: Dictionary of results
        """
        item_id = current_item[0]
        item_content = current_item[1]
        item = item_content['agolItem']
        type_keywords = item['typeKeywords']
        require_token = requires_token("Requires Subscription", type_keywords)
        print(f"{item_id}\t{item_content['title']}")
        print(f"retry count threshold: {item_content['default_retry_count']}")
        print(f"timout threshold: {item_content['default_timeout']}")
        print(f"service url: {item_content['service_url']}")
        print(f"requires token: {require_token}")
        response = RequestUtils.check_request(path=item_content["service_url"],
                                              params={},
                                              try_json=True,
                                              add_token=require_token,
                                              retry_factor=item_content["default_retry_count"],
                                              timeout_factor=item_content["default_timeout"],
                                              token=item_content["token"],
                                              id=item_id)
        print("\n")
        return current_item[0], {**current_item[1], **{"serviceResponse": response}}

    return dict(map(validate_service, data_model.items()))


def validate_layers(data_model=None) -> dict:
    """
    Validate the layers of the service
    :param data_model:
    :return:
    """
    if data_model is None:
        data_model = {}

    def validate_service_layers(current_item):
        """
        :param current_item: The current item
        :return: Dictionary of validated layers
        """
        item_id = current_item[0]
        item_content = current_item[1]
        print(f"{item_id}")

        layers = []

        if item_content["itemIsValid"]:
            # item is valid
            try:
                for i, layer in enumerate(item_content["agolItem"].layers):
                    print(f" {layer.properties['name']}")
                    layers.append({
                        "id": item_id,
                        "layerId": layer.properties["id"],
                        "name": layer.properties["name"],
                        "success": True,
                        "token": item_content["token"],
                        "url": layer.url
                    })
            except Exception as e:
                print(f" The item {item_id} is either inaccessible or not valid: {e}")
                layers.append({
                    "id": item_id,
                    "layerId": "",
                    "success": False,
                    "message": e
                })
                layer_query_params = prepare_layer_query_params(layers)
                layers_are_valid = check_all_layers(layers)
                return current_item[0], {**current_item[1], **{"allLayersAreValid": layers_are_valid},
                                         **{"layers": layers},
                                         **{"layerQueryParams": layer_query_params}}
            else:
                layer_query_params = prepare_layer_query_params(layers)
                layers_are_valid = check_all_layers(layers)
                return current_item[0], {**current_item[1], **{"allLayersAreValid": layers_are_valid},
                                         **{"layers": layers},
                                         **{"layerQueryParams": layer_query_params}}
        else:
            # item is not valid or not accessible, use the url on file
            if item_content["serviceResponse"]["success"]:
                # check if we received a successful response from using the service url on file
                response = json.loads(item_content["serviceResponse"]["response"].content.decode('utf-8'))
                # Check if the response throws and error
                error = response.get("error")
                if error is None:
                    # There was no error returned in the response
                    for i, layer in enumerate(response["layers"]):
                        print(f" {layer['name']}")
                        layers.append({
                            "id": item_id,
                            "layerId": layer.properties["id"],
                            "name": layer["name"],
                            "success": True,
                            "token": current_item[1]["token"],
                            "url": item_content["service_url"] + "/" + str(layer["id"])
                        })
                    layer_query_params = prepare_layer_query_params(layers)
                    layers_are_valid = check_all_layers(layers)
                else:
                    # There was an error returned in the response
                    layers.append({
                        "id": item_id,
                        "success": False,
                        "message": f" The item {item_id} service url is having issues: {error['message']}"
                    })
                    layer_query_params = prepare_layer_query_params(layers)
                    layers_are_valid = check_all_layers(layers)
                return current_item[0], {**current_item[1], **{"allLayersAreValid": layers_are_valid},
                                         **{"layers": layers},
                                         **{"layerQueryParams": layer_query_params}}
            else:
                # we have a failed response
                print(f" The item {item_id} not inaccessible or not valid and the service url is not accessible.")
                layers.append({
                    "id": item_id,
                    "success": False,
                    "message": f" The item {item_id} is either inaccessible or not valid and the service url is not "
                               f"accessible. "
                })
                layer_query_params = prepare_layer_query_params(layers)
                layers_are_valid = check_all_layers(layers)
                return current_item[0], {**current_item[1], **{"allLayersAreValid": layers_are_valid},
                                         **{"layers": layers},
                                         **{"layerQueryParams": layer_query_params}}

    def prepare_layer_query_params(layers):
        """
        Build the layer query params for each layer
        :param layers:
        :return:
        """
        if layers is None:
            layers = []
        layer_data = []
        for layer in layers:
            item_id = layer["id"]
            if layer["success"]:
                layer_id = layer["layerId"]
                layer_name = layer["name"]
                layer_url = layer["url"]
                layer_data.append({
                    "id": item_id,
                    "layerId": layer_id,
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
                    "layerId": "",
                    "success": False
                })
        return layer_data

    def check_all_layers(layers):
        """
        Returns a True/False if all the layers were a success or not
        :param layers: All layer query results
        :return: Boolean value
        """
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
            return False

    return dict(map(validate_service_layers, data_model.items()))


def requires_token(x, ls) -> bool:
    """
    :param x: We ae checking for the string 'Requires Subscription'
    :param ls: An item's type keywords
    :return: bool
    """
    return x in ls

