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
couchdb_dir = os.path.join(os.path.dirname(__file__), 'couchdb')
if couchdb_dir not in sys.path:
    sys.path.append(couchdb_dir)
import couchdb
from .utils import Utils


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

    def getAddress(self):
        return self.address

    def getConnection(self):
        return self.connection

    def request_database_from_ids(self, database, ids):
        query = Utils.build_query_only_id(ids)
        db = self.connection[database]
        return db.find(query)
