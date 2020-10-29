"""
Very lightweight data serializer.
"""

VERSION = "1.0.0"

import json
import xml.etree.ElementTree as et

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
    def serialize(self, feed, format):
        serializer = get_serializer(format)
        return serializer(feed)


def get_serializer(format):
    """ """
    if format == 'JSON':
        return _serialize_to_json
    elif format == 'XML':
        return _serialize_to_xml
    else:
        raise ValueError(format)


def _serialize_to_json(feed):
    """ """
    payload = {}
    return json.dumps(payload)


def _serialize_to_xml(feed):
    """ Create the Element(s) heirarchy"""
    # rss element
    rssElement = et.Element('rss', attrib={
        'version': feed.rss
    })
    # channel
    channelElement = et.SubElement(rssElement, 'channel')
    # title
    _createElement(feed.channelTitle, channelElement, "title")
    # link
    _createElement(feed.channelLink, channelElement, "link")
    # description
    _createElement(feed.channelDescription, channelElement, "description")
    # web master
    _createElement(feed.webmaster, channelElement, "webMaster")
    # ttl
    _createElement(feed.ttl, channelElement, "ttl")
    # ttl
    _createElement(feed.pubDate, channelElement, "pubDate")
    # item
    itemElement = _createElement(feed.item, channelElement, "item")
    # item title
    _createElement(feed.itemTitle, itemElement, "title")
    # link
    _createElement(feed.itemLink, itemElement, "link")
    # item status
    _createElement(feed.itemDescription, itemElement, "description")

    #return et.tostring(rssElement, encoding="unicode", method="xml")
    tree = et.ElementTree(rssElement)
    return tree

def _createElement(feedProp, targetEle, newTag):
    """Create an element instance, and appends it to an existing parent."""
    ele = et.SubElement(targetEle, newTag)
    ele.text = feedProp
    return ele

