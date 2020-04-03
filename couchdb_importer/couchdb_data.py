# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CouchdbImporter
                                 A QGIS plugin
 This plugin allows importing vector data from the couchdb database.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-01-30
        git sha              : $Format:%H$
        copyright            : (C) 2020 by MaximeGavens/Geomatys
        email                : contact@geomatys.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import json


class CouchdbData(object):
    def __init__(self):
        self.data = {}
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'configuration.json')) as inFile:
            preference = json.load(inFile)
            for className in preference:
                self.data[className] = {
                    "selected": True,
                    "ids": "all",
                    "attributes": preference[className]["attributes"],
                    "style": preference[className]["style"],
                    "crs": preference[className]["crs"]
                }

    def __len__(self):
        return len(self.data)

    def getData(self):
        return self.data

    def getDataClass(self, name):
        return self.data[name]

    def getClassName(self):
        return self.data.keys()

    def getSelected(self, name):
        return self.data[name]["selected"]

    def getIds(self, name):
        return self.data[name]["ids"]

    def getListId(self, name):
        if type(self.data[name]["ids"]) == str:
            return None
        return self.data[name]["ids"].keys()

    def getListId(self):
        result = []
        for className in self.getClassName():
            if type(self.getIds(className)) == str:
                return None
            result.extend(self.data[className]["ids"].keys())
        return result

    def getAttributes(self, name):
        return self.data[name]["attributes"]

    def getStylePoint(self, name):
        return self.data[name]["style"]["point"]

    def getStyleDefault(self, name):
        return self.data[name]["style"]["default"]

    def getCrs(self, name):
        return self.data[name]["crs"]

    def setSelected(self, name, isSelected):
        self.data[name]["selected"] = isSelected

    def setIds(self, name, ids):
        self.data[name]["ids"] = ids

    def setAttributes(self, name, attributes):
        self.data[name]["attributes"] = attributes

    def setStyle(self, name, style):
        self.data[name]["style"] = style

    def setCrs(self, name, crs):
        self.data[name]["crs"] = crs

    def setAttributeValue(self, name, attribute, value):
        self.data[name]["attributes"][attribute] = value

    def setIdValue(self, name, id, isSelected):
        self.data[name]["ids"][id] = isSelected

    def reset_from_configuration(self):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'configuration.json')) as inFile:
            preference = json.load(inFile)
            for className in preference:
                self.data[className] = {
                    "selected": True,
                    "ids": "all",
                    "attributes": preference[className]["attributes"],
                    "style": preference[className]["style"],
                    "crs": preference[className]["crs"]
                }

    def write_configuration(self):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'configuration.json'), 'w') as outFile:
            configuration = {}
            for className in self.data:
                configuration[className] = {}
                configuration[className]["attributes"] = self.data[className]["attributes"]
                configuration[className]["style"] = self.data[className]["style"]
                configuration[className]["crs"] = self.data[className]["crs"]
            json.dump(configuration, outFile)
