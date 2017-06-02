#!/usr/bin/python

import xml.etree.ElementTree as ET

class XspfBase(object):
    NS = "http://xspf.org/ns/0/"

    def _addAttributesToXml(self, parent, attrs):
        for attr in attrs:
            value = getattr(self, attr)
            if value:
                el = ET.SubElement(parent, "{{{0}}}{1}".format(self.NS, attr))
                el.text = value

    def _addDictionaryElements(self, parent, name, values):
        # Sort keys so we have a stable order of items for testing.
        # Alternative would be SortedDict, but is >=2.7
        for k in sorted(values.keys()):
            el = ET.SubElement(parent, "{{{0}}}{1}".format(self.NS, name))
            el.set("rel", k)
            el.text = values[k]

# Avoid namespace prefixes, VLC doesn't like it
if hasattr(ET, 'register_namespace'):
    ET.register_namespace('', XspfBase.NS)

# in-place prettyprint formatter
# From http://effbot.org/zone/element-lib.htm
def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class Xspf(XspfBase):
    def __init__(self, obj={}, **kwargs):
        self.version = "1"

        self._title = ""
        self._creator = ""
        self._info = ""
        self._annotation = ""
        self._location = ""
        self._identifier = ""
        self._image = ""
        self._date = ""
        self._license = ""
        self._attributions = []
        self._link = {}
        self._meta = {}

        self._trackList = []

        if len(obj):
            if "playlist" in obj:
                obj = obj["playlist"]
            for k, v in list(obj.items()):
                setattr(self, k, v)

        if len(kwargs):
            for k, v in list(kwargs.items()):
                setattr(self, k, v)

    @property
    def title(self):
        """A human-readable title for the playlist. Optional"""
        return self._title
    @title.setter
    def title(self, title):
        self._title = title

    @property
    def creator(self):
        """Human-readable name of the entity (author, authors, group, company, etc)
           that authored the playlist. Optional"""
        return self._creator
    @creator.setter
    def creator(self, creator):
        self._creator = creator

    @property
    def annotation(self):
        """A human-readable comment on the playlist. This is character data,
           not HTML, and it may not contain markup. Optional"""
        return self._annotation
    @annotation.setter
    def annotation(self, annotation):
        self._annotation = annotation

    @property
    def info(self):
        """URI of a web page to find out more about this playlist. Optional"""
        return self._info
    @info.setter
    def info(self, info):
        self._info = info

    @property
    def location(self):
        """Source URI for this playlist. Optional"""
        return self._location
    @location.setter
    def location(self, location):
        self._location = location

    @property
    def identifier(self):
        """Canonical ID for this playlist. Likely to be a hash or other
           location-independent name. Optional"""
        return self._identifier
    @identifier.setter
    def identifier(self, identifier):
        self._identifier = identifier

    @property
    def image(self):
        """URI of an image to display in the absence of a trackList/image
           element. Optional"""
        return self._image
    @image.setter
    def image(self, image):
        self._image = image

    @property
    def date(self):
        """Creation date (not last-modified date) of the playlist. Optional"""
        return self._date
    @date.setter
    def date(self, date):
        self._date = date

    @property
    def license(self):
        """URI of a resource that describes the license under which this
           playlist was released. Optional"""
        return self._license
    @license.setter
    def license(self, license):
        self._license = license

    @property
    def meta(self):
        return self._meta

    def add_meta(self, key, value):
        """Add a meta element to the playlist."""
        self._meta[key] = value

    def del_meta(self, key):
        """Remove a meta element."""
        del self._meta[key]

    def add_link(self, key, value):
        """Add a link element to the playlist."""
        self._link[key] = value

    def del_link(self, key):
        """Remove a link element."""
        del self._link[key]

    def add_attribution(self, location, identifier):
        self.attrbutions.append((location, identifier))

    def truncate_attributions(self, numattributions):
        self.attrbutions = self.attributions[-numattributions:]

    # Todo: Attribution, Link, Meta, Extension

    def add_extension(self, application):
        pass

    def make_extension_element(self, namespace, name, attributes, value):
        pass

    def remove_extension(self, application):
        pass

    @property
    def track(self):
        return self._trackList
    @track.setter
    def track(self, track):
        self.add_track(track)

    def add_track(self, track={}, **kwargs):
        if isinstance(track, list):
            for t in track:
                self.add_track(t)
        elif isinstance(track, Track):
            self._trackList.append(track)
        elif isinstance(track, dict) and len(track) > 0:
            self._trackList.append(Track(track))
        elif len(kwargs) > 0:
            self._trackList.append(Track(kwargs))

    def add_tracks(self, tracks):
        for t in tracks:
            self.add_track(t)

    def toXml(self, encoding="utf-8", pretty_print=True):
        root = ET.Element("{{{0}}}playlist".format(self.NS))
        root.set("version", self.version)

        self._addAttributesToXml(root, ["title", "info", "creator", "annotation",
                                         "location", "identifier", "image", "date", "license"])

        self._addDictionaryElements(root, "link", self._link)
        self._addDictionaryElements(root, "meta", self._meta)

        if len(self._trackList):
            track_list = ET.SubElement(root, "{{{0}}}trackList".format(self.NS))
            for track in self._trackList:
                track_list = track.getXmlObject(track_list)
        if pretty_print:
            indent(root)
        return ET.tostring(root, encoding)

class Track(XspfBase):
    def __init__(self, obj={}, **kwargs):
        self._location = ""
        self._identifier = ""
        self._title = ""
        self._creator = ""
        self._annotation = ""
        self._info = ""
        self._image = ""
        self._album = ""
        self._trackNum = ""
        self._duration = ""
        self._link = {}
        self._meta = {}

        if len(obj):
            for k, v in list(obj.items()):
                setattr(self, k, v)

        if len(kwargs):
            for k, v in list(kwargs.items()):
                setattr(self, k, v)

    @property
    def location(self):
        """URI of resource to be rendered. Probably an audio resource, but MAY be any type of
           resource with a well-known duration. Zero or more"""
        return self._location
    @location.setter
    def location(self, location):
        self._location = location

    @property
    def identifier(self):
        """ID for this resource. Likely to be a hash or other location-independent name,
           such as a MusicBrainz identifier.  MUST be a legal URI. Zero or more"""
        return self._identifier
    @identifier.setter
    def identifier(self, identifier):
        self._identifier = identifier

    @property
    def title(self):
        """Human-readable name of the track that authored the resource which defines the
           duration of track rendering. Optional"""
        return self._title
    @title.setter
    def title(self, title):
        self._title = title

    @property
    def creator(self):
        """Human-readable name of the entity (author, authors, group, company, etc) that authored
           the resource which defines the duration of track rendering."""
        return self._creator
    @creator.setter
    def creator(self, creator):
        self._creator = creator

    @property
    def annotation(self):
        """A human-readable comment on the track. This is character data, not HTML,
           and it may not contain markup."""
        return self._annotation
    @annotation.setter
    def annotation(self, annotation):
        self._annotation = annotation

    @property
    def info(self):
        """URI of a place where this resource can be bought or more info can be found. Optional"""
        return self._info
    @info.setter
    def info(self, info):
        self._info = info

    @property
    def image(self):
        """URI of an image to display for the duration of the track. Optional"""
        return self._image
    @image.setter
    def image(self, image):
        self._image = image

    @property
    def album(self):
        """Human-readable name of the collection from which the resource which defines
           the duration of track rendering comes. Optional"""
        return self._album
    @album.setter
    def album(self, album):
        self._album = album

    @property
    def trackNum(self):
        """Integer with value greater than zero giving the ordinal position of the media
           on the album. Optional"""
        return self._trackNum
    @trackNum.setter
    def trackNum(self, trackNum):
        self._trackNum = trackNum

    @property
    def duration(self):
        """The time to render a resource, in milliseconds. Optional"""
        return self._duration
    @duration.setter
    def duration(self, duration):
        self._duration = duration

    @property
    def meta(self):
        return self._meta

    def add_meta(self, key, value):
        """Add a meta element to the playlist."""
        self._meta[key] = value

    def del_meta(self, key):
        """Remove a meta element."""
        del self._meta[key]

    def add_link(self, key, value):
        """Add a link element to the playlist."""
        self._link[key] = value

    def del_link(self, key):
        """Remove a link element."""
        del self._link[key]

    # Todo: Link, Meta, Extension

    def getXmlObject(self, parent):
        track = ET.SubElement(parent, "{{{0}}}track".format(self.NS))

        self._addAttributesToXml(track, ["location", "identifier", "title", "creator",
                                        "annotation", "info", "image", "album",
                                        "trackNum", "duration"])

        self._addDictionaryElements(track, "link", self._link)
        self._addDictionaryElements(track, "meta", self._meta)

        return parent

Spiff = Xspf
