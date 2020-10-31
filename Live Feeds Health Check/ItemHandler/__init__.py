import arcgis
import json


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
