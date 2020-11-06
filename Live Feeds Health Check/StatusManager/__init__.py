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


def update_rss_feed(previous_status_output=None, current_status=None, status_codes_data_model=None) -> bool:
    """
    Determine whether or not we need to update the feed.  The update is based on not the status, but rather the status
    comment.  An item's status code could have changed, however,
    :param previous_status_output: The output status file from the previous run
    :param current_status: The current status dict from the current item
    :param status_codes_data_model: The status codes model to reference in order to obtain the comments
    :return:
    """
    update = False
    for previous_status in previous_status_output:
        previous_item_id = previous_status["id"]
        previous_item_status_code = previous_status["status"]["code"]
        current_item_id = current_status["id"]
        current_item_status_code = current_status["status"]["code"]
        if current_item_id == previous_item_id:
            if current_item_status_code is not previous_item_status_code:
                # obtain comment from the previous and current status code
                # if the comments are the same, do not update the rss feed
                # if the comments are different, update the feed
                previous_status_comment = get_status_code(previous_item_status_code,
                                                          status_codes_data_model)["statusDetails"]["Comment"]
                current_status_comment = get_status_code(current_item_status_code,
                                                         status_codes_data_model)["statusDetails"]["Comment"]
                if previous_status_comment == current_status_comment:
                    print(f"Do not update RSS Feed for: {current_item_id}")
                else:
                    print(f"Update RSS Feed for: {current_item_id}")
                    # comments are different, update the feed
                    update = True
    return update
