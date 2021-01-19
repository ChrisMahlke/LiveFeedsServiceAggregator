""" 
This module is responsible for returning a status code and a set of details
related to the status code
"""


def get_status_code(status_code_key: str = "", input_config=None) -> dict:
    """
    Returns the status code and messaging
    :param status_code_key:
    :param input_config:
    :return:
    """
    # Legacy code from when the status file was an ini file
    if input_config is None:
        input_config = {}
    return {
        "code": status_code_key,
        "statusDetails": input_config.get(status_code_key)
    }


def update_rss_feed(previous_status_output=None, item=None, status_codes_data_model=None) -> bool:
    """
    Determine whether or not we need to update the feed.  The update is based on not the status, but rather the status
    comment.  An item's status code could have changed, however.

    :param previous_status_output: The output status file from the previous run
    :param item: The current status dict from the current item
    :param status_codes_data_model: The status codes model to reference in order to obtain the comments
    :return: Boolean indicating whether or not there was a change in the status
    """
    # item ID
    item_id = item["id"]
    # status code
    status_code = item["status"]["code"]
    # bool flag used to indicate whether or not there was an update since we last ran the script
    update = False
    # TODO Should have used a dict with item ID's as the keys
    for previous_status in previous_status_output:
        # item id on file (from the status file)
        previous_item_id = previous_status["id"]
        # status code on file
        previous_item_status_code = previous_status["status"]["code"]
        if item_id == previous_item_id:
            # compare the status codes from the current run to the previous run
            if status_code is not previous_item_status_code:
                # obtain comment from the previous and current status code
                # if the comments are the same, do not update the rss feed
                # if the comments are different, update the feed
                previous_status_comment = get_status_code(previous_item_status_code,
                                                          status_codes_data_model)["statusDetails"]["Comment"]
                current_status_comment = get_status_code(status_code,
                                                         status_codes_data_model)["statusDetails"]["Comment"]
                if previous_status_comment == current_status_comment:
                    print(f"Do not update RSS Feed for: {item_id}")
                else:
                    # If we reach this point, the status has changed since the previous run
                    print(f"Update RSS Feed for: {item_id}")
                    # comments are different, update the feed
                    update = True
    return update
