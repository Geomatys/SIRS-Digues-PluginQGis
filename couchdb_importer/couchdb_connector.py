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
import sys
import requests
couchdb_dir = os.path.join(os.path.dirname(__file__), 'couchdb')
if couchdb_dir not in sys.path:
    sys.path.append(couchdb_dir)
import couchdb
from .utils import Utils
import logging
from functools import lru_cache


class CouchdbConnectorException(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return 'CouchdbConnectorException, {0} '.format(self.message)
        else:
            return 'CouchdbConnectorException has been raised'


class CouchdbConnector(object):
    def __init__(self, http, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.address = http + "://" + self.user + ":" + self.password + "@" + self.url + "/"
        self.connection = couchdb.Server(self.address)
        self.libelleRefId = {}

    def getAddress(self):
        return self.address

    def getConnection(self):
        return self.connection

    def getFilteredConnection(self):
        result = []
        for name in self.connection:
            if not Utils.is_str_start_by_underscore(name):
                r = requests.get(self.address + name)
                if r.status_code == 200:
                    result.append(name)
        return result

    def is_not_existing_specific_view(self, database):
        db = self.connection[database]

        result = db.get("_design/SpecQgis")
        return result is None

    def create_specific_view(self, database):
        db = self.connection[database]

        doc = Utils.create_specific_view()
        db.save(doc)

    def create_or_update_specific_view(self, database):
        if self.is_not_existing_specific_view(database):
            self.create_specific_view(database)

    def request_database(self, database, className=None, attributes=None, ids=None, single=None):
        if className is not None and attributes is not None and ids is None and single is None:
            result = self.request_by_class_and_attributes(database, className, attributes)
        elif className is not None and attributes is not None and ids is not None and single is None:
            result = self.request_by_class_attributes_and_ids(database, className, attributes, ids)
        elif className is None and attributes is None and ids is not None and single is None:
            result = self.request_by_multiple_id(database, ids)
        elif className is not None and attributes is None and ids is None and single is not None:
            result = self.request_by_class_and_id(database, className, single)
        elif className is None and attributes is None and ids is None and single is not None:
            result = self.request_by_id(database, single)
        else:
            raise CouchdbConnectorException("Requète inexistante.")
        return result

    def request_by_class_and_attributes(self, database, className, attributes):
        target = []
        db = self.connection[database]
        fullClassName = "fr.sirs.core.model." + className
        row = db.view('SpecQgis/byClass', key=fullClassName)

        for item in row:
            t = item.value
            Utils.filter_object_by_attributes(t, attributes)
            target.append(t)

        return target

    def request_by_class_attributes_and_ids(self, database, className, attributes, ids):
        target = []
        db = self.connection[database]
        fullClassName = "fr.sirs.core.model." + className

        for Id in ids:
            row = db.view('SpecQgis/byClassAndId', key=[fullClassName, Id])
            for item in row:
                t = item.value
                Utils.filter_object_by_attributes(t, attributes)
                target.append(t)

        return target

    def request_by_multiple_id(self, database, ids):
        target = []
        db = self.connection[database]

        for Id in ids:
            row = db.view('SpecQgis/byId', key=Id)
            for item in row:
                t = item.value
                target.append(t)

        return target

    def request_by_class(self, database, className):
        target = []
        db = self.connection[database]
        fullClassName = "fr.sirs.core.model." + className
        row = db.view('SpecQgis/byClass', key=fullClassName)

        for item in row:
            t = item.value
            target.append(t)
        return target

    def request_by_id(self, database, single_id):
        target = []
        db = self.connection[database]

        row = db.view('SpecQgis/byId', key=single_id)
        for item in row:
            t = item.value
            target.append(t)

        return target

    def request_by_class_and_id(self, database, className, single_id):
        target = []
        db = self.connection[database]
        fullClassName = "fr.sirs.core.model." + className

        row = db.view('SpecQgis/byClassAndId', key=[fullClassName, single_id])
        for item in row:
            t = item.value
            target.append(t)

        return target

    def get_and_save_label_from_id(self, database, Id, double):
        if database not in self.libelleRefId:
            self.libelleRefId[database] = {}
        if Id not in self.libelleRefId[database]:
            result = self.request_database(database, single=Id)
            result = list(result)
            if len(result) == 0:
                label = Id
            else:
                if double:
                    label = Utils.get_label_and_designation_reference(result[0])
                else:
                    label = Utils.get_label_reference(result[0])
            self.libelleRefId[database][Id] = label
        return self.libelleRefId[database][Id]

    @lru_cache(maxsize=None)
    def get_label_from_id(self, database, Id):
        """
        Care with the usage of this methods, it can cause memory saturation problems.
        """
        result = list(self.request_database(database, single=Id))
        return Id if len(result) == 0 else Utils.get_label_reference(result[0])

    @lru_cache(maxsize=None)
    def get_value_or_id_from_id(self, database, Id, attribute):
        """
        Care with the usage of this methods, it can cause memory saturation problems.
        """
        result = list(self.request_database(database, single=Id))
        if len(result) == 0:
            return Id
        else:
            return result[0][attribute] if attribute in result[0] else Id

    def replace_id_by_label_in_result(self, database, target):
        for elem in target:
            self.replace_id_by_label(database, elem)

    def replace_id_by_label(self, database, elem):
        if type(elem) == dict:
            for attr in elem:
                if attr[-2:] == 'Id' or attr in ['author', 'orientationPhoto', 'Author', 'Type', 'type']:
                    if elem[attr] is not None:
                        if attr in ['borneDebutId', 'borneFinId', 'tronconId']:
                            elem[attr] = self.get_and_save_label_from_id(database, elem[attr], True)
                        else:
                            elem[attr] = self.get_and_save_label_from_id(database, elem[attr], False)
                elif attr[-3:] == 'Ids' and type(elem[attr]) == list:
                    labelList = []
                    for val in elem[attr]:
                        label = val
                        if val is not None:
                            if attr == 'prestationIds':
                                label = self.get_and_save_label_from_id(database, val, True)
                            else:
                                label = self.get_and_save_label_from_id(database, val, False)
                        labelList.append(label)
                    elem[attr] = labelList
                elif type(elem[attr]) == list:
                    for elem2 in elem[attr]:
                        self.replace_id_by_label(database, elem2)
                elif type(elem[attr]) == dict:
                    self.replace_id_by_label(database, elem[attr])
        else:
            logging.warning(f" An attribute is not type dictionary or list of dictionaries")

