""" Utility methods for working with RSS """
from datetime import datetime, timedelta


def get_num_events(events_history=None):
    """
    Return the total number of events stored in the events history file.

    :param events_history:
    :return:
    """
    return len(events_history)


def get_num_events_ceiling(input_dict=None):
    """
    Return the maximum number of events permitted to be written in the events history file.

    :param input_dict:
    :return:
    """
    return int(input_dict.get("number_of_events_max", 0))


def get_rss_time_constrains(input_dict=None):
    """
    Get the time constraints.

    :param input_dict:
    :return:
    """
    return input_dict.get("rss_time_range", 0)


def is_event_in_time_range(time_to_check=None, time_limit=None) -> bool:
    """
    Check the event time to see if it falls within the range.

    :param time_to_check:
    :param time_limit: Time range in days "ago"
    :return:
    """
    time_now = datetime.now() - timedelta(days=0)
    target_time = datetime.fromtimestamp(time_to_check)
    diff = time_now - target_time
    if diff.days <= int(time_limit):
        return True
    return False
