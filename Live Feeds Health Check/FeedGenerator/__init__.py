"""
Very lightweight data serializer.
"""
import json
import xml.etree.ElementTree as Et

VERSION = "1.0.0"


class Feed:
    """ """

    def __init__(self, **kwargs):
        prop_defaults = {
            "rss": "2.0",
            "channel": "",
            "channelTitle": "",
            "channelLink": "",
            "channelDescription": "",
            "webmaster": "",
            "ttl": "",
            "pubDate": "",
            "item": "",
            "itemTitle": "",
            "itemLink": "",
            "itemDescription": ""
        }

        for (prop, default) in prop_defaults.items():
            setattr(self, prop, kwargs.get(prop, default))


class DataSerializer:
    """ """

    @staticmethod
    def serialize(feed, file_format):
        serializer = get_serializer(file_format)
        return serializer(feed)


def get_serializer(file_format):
    """ """
    if file_format == 'JSON':
        return _serialize_to_json
    elif file_format == 'XML':
        return _serialize_to_xml
    else:
        raise ValueError(file_format)


def _serialize_to_json():
    """ """
    payload = {}
    return json.dumps(payload)


def _serialize_to_xml(feed):
    """ Create the Element(s) hierarchy """
    # rss element
    rss_element = Et.Element('rss', attrib={
        'version': feed.rss
    })
    # channel
    channel_element = Et.SubElement(rss_element, 'channel')
    # title
    _create_element(feed.channelTitle, channel_element, "title")
    # link
    _create_element(feed.channelLink, channel_element, "link")
    # description
    _create_element(feed.channelDescription, channel_element, "description")
    # web master
    _create_element(feed.webmaster, channel_element, "webMaster")
    # ttl
    _create_element(feed.ttl, channel_element, "ttl")
    # ttl
    _create_element(feed.pubDate, channel_element, "pubDate")
    # item
    item_element = _create_element(feed.item, channel_element, "item")
    # item title
    _create_element(feed.itemTitle, item_element, "title")
    # link
    _create_element(feed.itemLink, item_element, "link")
    # item status
    _create_element(feed.itemDescription, item_element, "description")

    tree = Et.ElementTree(rss_element)
    return tree


def _create_element(feed_prop, target_ele, new_tag):
    """Create an element instance, and appends it to an existing parent."""
    ele = Et.SubElement(target_ele, new_tag)
    ele.text = feed_prop
    return ele
