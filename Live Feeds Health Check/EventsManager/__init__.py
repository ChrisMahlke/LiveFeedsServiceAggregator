"""
Utility methods for working with storing events on file

* timestamp (chris)
The current time the script is running
Used to check the elapsed time between now and the last updated time of the feed
Used to check the elapsed time between now and the last run time of the feed

* lastUpdateTimestamp (paul)
10 digit Timestamp 'seconds since epoch' containing time of last Successful Run (and Service update)
NOT USED in RSS/Events History

* lastRunTimestamp (paul)
10 digit Timestamp 'seconds since epoch' containing time of last run (having a Success, a Failure, or a No Action flag ('No Data Updates'))
NOT USED in RSS/Events History

* lastBuildTime (chris)
time_utils_response["datetimeObj"].strftime("%a, %d %b %Y %H:%M:%S +0000")


"""
import json
import os
import pathlib
import stat
import FileManager as FileManager
from datetime import datetime, timedelta


def create_history_file(input_data=None, events_file=None):
    """Create a new history file and hydrate it.

    :param input_data: Input data
    :param events_file: Output file
    :return:
    """
    ct = datetime.now()
    ct_timestamp = datetime.timestamp(ct)
    dt_object = datetime.fromtimestamp(ct_timestamp)

    FileManager.create_new_file(file_path=events_file)
    FileManager.set_file_permission(file_path=events_file)
    FileManager.save(data={
        "id": input_data.get("id", ""),
        "history": [{
            "pubDate": dt_object.strftime("%a, %d %b %Y %H:%M:%S +0000"),
            "pubEventDate": input_data.get("timestamp", 0),
            "title": input_data.get("title", input_data.get("missing_item_title")),
            "snippet": input_data.get("snippet", input_data.get("missing_item_snippet")),
            "comments": input_data.get("comments", ""),
            "lastBuildTime": input_data.get("lastBuildTime", 0),
            "updateRate": input_data.get("avgUpdateIntervalMins", 0),
            "featureCount": input_data.get("featureCount", 0),
            "usage": input_data.get("usage"),
            "status": input_data.get("status")
        }],
    }, path=events_file)


def update_events_file(input_data=None, events_file=None):
    """
    Update the file.

    :param input_data:
    :param events_file:
    :return:
    """
    ct = datetime.now()
    ct_timestamp = datetime.timestamp(ct)
    dt_object = datetime.fromtimestamp(ct_timestamp)

    # JSON from events file
    status_history_json = FileManager.open_file(path=events_file)
    # history element
    history = status_history_json["history"]
    # number of events in the current item's history file
    n_events = _get_num_events(history)
    # maximum number of events permitted to be logged for this item
    n_max_events = _get_num_events_ceiling(input_data)
    # time constraints
    rss_time_range_in_days = _get_rss_time_constrains(input_data)

    # clean events file first
    history = _clean_history_file(input_data=input_data,
                                  events_history=history,
                                  max_days_ago=rss_time_range_in_days)

    # is the new event in the time range
    # event_in_time_range = _is_event_in_time_range(input_data.get("pubEventDate", 0),
    #                                              rss_time_range_in_days)

    # if n_events >= n_max_events:
    # number of events in the current item's history file
    #    _get_num_events(history)
    #    print("Remove the oldest event")
    #    print(f"{history[0]}")
    #    history.pop(0)
    # else:
    # print("\nUpdating events file")
    # append new status to list
    history.append({
        "pubDate": dt_object.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "pubEventDate": input_data.get("timestamp", 0),
        "title": input_data.get("title", input_data.get("missing_item_title")),
        "snippet": input_data.get("snippet", input_data.get("missing_item_snippet")),
        "comments": input_data.get("comments", ""),
        "lastBuildTime": input_data.get("lastBuildTime", 0),
        "updateRate": input_data.get("avgUpdateIntervalMins", 0),
        "featureCount": input_data.get("featureCount", 0),
        "usage": input_data.get("usage"),
        "status": input_data.get("status")
    })
    # update json
    status_history_json.update({
        "history": history
    })
    # write update to file
    FileManager.save(data=status_history_json, path=events_file)
    print(f"Events history file updated")
    print(f"Number of events: {_get_num_events(history)}")


def _clean_history_file(input_data=None, events_history=None, max_days_ago=None):
    events_in_range = []
    n_max_events = _get_num_events_ceiling(input_data)
    # iterate through and remove items that are expired or exceed max number alowed
    for index in range(len(events_history) - 1, -1, -1):
        event = events_history[index]
        if _is_event_in_time_range(event.get("pubEventDate", 0), max_days_ago):
            print("Event in range")
            if len(events_in_range) + 1 < n_max_events:
                events_in_range.insert(0, event)
            else:
                print(f"Event dropped, too many on hand: {event}")
        else:
            print(f"Event not in range: {event}")
    return events_in_range


def _get_num_events(events_history=None):
    """
    Return the total number of events stored in the events history file.

    :param events_history: The history json object
    :return: The number of events in the file
    """
    n_events = len(events_history)
    print(f"Number of events in file: {n_events}")
    return n_events


def _get_num_events_ceiling(input_dict=None):
    """
    Return the maximum number of events permitted to be written in the events history file.

    :param input_dict:
    :return:
    """
    n_max_events = int(input_dict.get("number_of_events_max", 0))
    print(f"Maximum number of events allowed: {n_max_events}")
    return n_max_events


def _get_rss_time_constrains(input_dict=None):
    """
    Get the time constraints.

    :param input_dict:
    :return:
    """
    n_days = input_dict.get("rss_time_range", 0)
    print(f"Time constraints: {n_days} days")
    return n_days


def _is_event_in_time_range(time_to_check=None, time_limit=None) -> bool:
    """
    Check the event time to see if it falls within the range.

    :param time_to_check:
    :param time_limit: Time range in days "ago"
    :return:
    """
    date_limit = datetime.now() - timedelta(days=int(time_limit))
    if datetime.fromtimestamp(time_to_check) < date_limit:
        return False
    return True
