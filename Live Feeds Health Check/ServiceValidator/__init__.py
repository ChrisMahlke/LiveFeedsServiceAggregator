import arcgis
import concurrent.futures
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
        item_id = current_item[0]
        try:
            agol_item = gis.content.get(item_id)
            if agol_item is None:
                current_item[1].update({
                    "itemIsValid": False
                })
                print(f"ERROR\t{item_id} is invalid or item is inaccessible")
        except Exception as e:
            current_item[1].update({
                "itemIsValid": False
            })
            print(f"ERROR\t{item_id} is having an issue: {e}")
        else:
            # update the title and snippet in case it has changed in AGOL
            current_item[1].update({
                "title": agol_item["title"],
                "snippet": agol_item["snippet"],
                "service_url": agol_item["url"],
                "agolItem": agol_item,
                "itemIsValid": True
            })
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
        if item_content["itemIsValid"]:
            service_url = item_content["agolItem"]["url"]
        else:
            service_url = item_content["service_url"]
        response = RequestUtils.check_request(path=service_url,
                                              params={},
                                              try_json=True,
                                              add_token=True,
                                              retry_factor=item_content["default_retry_count"],
                                              timeout_factor=item_content["default_timeout"],
                                              token=item_content["token"],
                                              id=item_id)
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
        # TODO ???
        exclusion_list_input = current_item[1]["exclusion"].split(",")
        exclusion_list_input_results = []
        if isinstance(exclusion_list_input[0], str) and len(exclusion_list_input[0]) > 0:
            exclusion_list_input_results = list(map(int, exclusion_list_input))

        layers = []

        if item_content["itemIsValid"]:
            # item is valid
            try:
                for i, layer in enumerate(item_content["agolItem"].layers):
                    if layer.properties["id"] not in exclusion_list_input_results:
                        print(f"\t{layer.properties['name']}")
                        layers.append({
                            "id": item_id,
                            "name": layer.properties["name"],
                            "success": True,
                            "token": item_content["token"],
                            "url": layer.url
                        })
            except Exception as e:
                print(f"\tThe item {item_id} is either inaccessible or not valid: {e}")
                layers.append({
                    "id": item_id,
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
                # we have a successful response from using the service url on file
                response = json.loads(item_content["serviceResponse"]["response"].content.decode('utf-8'))
                for i, layer in enumerate(response["layers"]):
                    if layer["id"] not in exclusion_list_input_results:
                        print(f"\t{layer['name']}")
                        layers.append({
                            "id": item_id,
                            "name": layer["name"],
                            "success": True,
                            "token": current_item[1]["token"],
                            "url": item_content["service_url"] + "/" + str(layer["id"])
                        })
                layer_query_params = prepare_layer_query_params(layers)
                layers_are_valid = check_all_layers(layers)
                return current_item[0], {**current_item[1], **{"allLayersAreValid": layers_are_valid},
                                         **{"layers": layers},
                                         **{"layerQueryParams": layer_query_params}}
            else:
                # we have a failed response
                print(f"\tThe item {item_id} not inaccessible or not valid and the service url is not accessible.")
                layers.append({
                    "id": item_id,
                    "success": False,
                    "message": f"\tThe item {item_id} is either inaccessible or not valid and the service url is not "
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

        try:
            agol_item = item_content["agolItem"]
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
                        current_item_feature_count += count_dict["count"]
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
