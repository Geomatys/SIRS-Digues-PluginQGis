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

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QStandardItem
from qgis.core import QgsFeature, QgsVectorLayer, QgsField, QgsLineSymbol, QgsMarkerSymbol, QgsWkbTypes, QgsDefaultValue

from .couchdb_data import CouchdbData


class CouchdbBuilder(object):
    def __init__(self):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'configuration_label.json')) as labelFile:
            self.labels = json.load(labelFile)
        with open(os.path.join(__location__, 'configuration_layer_field.json')) as fieldFile:
            self.fields = json.load(fieldFile)

    def reset_from_labels_configuration(self):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'configuration_label.json')) as inFile:
            self.labels = json.load(inFile)

    def reset_from_layer_configuration(self):
        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        with open(os.path.join(__location__, 'configuration_layer_field.json')) as inFile:
            self.fields = json.load(inFile)

    def build_layer(self, className, geom, data: CouchdbData):
        crs = data.getCrs(className)
        fields = self.build_layer_fields(className)
        layer = QgsVectorLayer(QgsWkbTypes.displayString(geom.wkbType()) + "?crs=" + crs, className, "memory")

        if geom.wkbType() == QgsWkbTypes.Point:
            props = data.getStylePoint(className)
            symbol = QgsMarkerSymbol.createSimple(props)
        else:
            props = data.getStyleDefault(className)
            symbol = QgsLineSymbol.createSimple(props)
            symbol.setOpacity(0.5)
        layer.renderer().setSymbol(symbol)
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        return layer

    def build_layer_fields(self, className):
        target = []
        fields = self.fields[className]

        for title in fields:
            if "_attachments" in title:
                continue

            label = self.label_identification(className, title)

            if 'borneDebutId' in title or 'borneFinId' in title or 'tronconId' in title or 'prestationIds' in title:
                target.append(QgsField(label + ' libelle', QVariant.String))
                target.append(QgsField(label + ' designation', QVariant.String))
                continue

            if fields[title] == "str":
                target.append(QgsField(label, QVariant.String))
            elif fields[title] == "int":
                target.append(QgsField(label, QVariant.Int))
            elif fields[title] == "bool":
                target.append(QgsField(label, QVariant.Bool))
            elif fields[title] == "float":
                target.append(QgsField(label, QVariant.Double))
        return target

    def build_feature(self, positionable, formatGeom, layer, data: CouchdbData):
        classNameComplete = positionable["@class"]
        className = classNameComplete.split("fr.sirs.core.model.")[1]
        attrValue = self.build_field_value(positionable, className, data)
        feature = QgsFeature(layer.fields())

        for title in attrValue:
            label = self.label_identification(className, title)

            if 'borneDebutId' in title or 'borneFinId' in title or 'tronconId' in title or 'prestationIds' in title:
                label1 = label + ' libelle'
                label2 = label + ' designation'
                if ' - ' in attrValue[title]:
                    value1, value2 = attrValue[title].split(' - ')
                    if layer.fields().indexFromName(label1) != -1:
                        feature.setAttribute(label1, value1)
                    if layer.fields().indexFromName(label2) != -1:
                        feature.setAttribute(label2, value2)
                else:
                    if layer.fields().indexFromName(label1) != -1:
                        feature.setAttribute(label1, attrValue[title])
                    if layer.fields().indexFromName(label2) != -1:
                        feature.setAttribute(label2, attrValue[title])
                continue

            if layer.fields().indexFromName(label) != -1:
                if 'Borne de début: Amont/Aval' in label or 'Borne de fin: Amont/Aval' in label:
                    if attrValue[title]:
                        feature.setAttribute(label, "Amont")
                    else:
                        feature.setAttribute(label, "Aval")
                else:
                    feature.setAttribute(label, attrValue[title])

        feature.setGeometry(formatGeom)
        return feature

    def build_field_value(self, content, className, data: CouchdbData):
        value = {}
        pref = data.getAttributes(className)
        for attr in pref:
            if pref[attr]:
                if attr in content.keys():
                    if type(content[attr]) in [str, float, bool, int]:
                        value[attr] = content[attr]
                    elif type(content[attr]) == list or type(content[attr]) == dict:
                        self.build_field_value_generic(attr, content[attr], value)
                    else:
                        value[attr] = "Aucune donnée"
                else:
                    value[attr] = "Aucune donnée"
        return value

    def build_field_value_generic(self, name, obj, value):
        if type(obj) in [str, int, float, bool]:
            value[name] = obj
        elif type(obj) == list:
            l = len(obj)
            if name == "prestationIds":
                if l == 1:
                    self.build_field_value_generic(name + " actuelle:", obj[-1], value)
                elif l == 2:
                    self.build_field_value_generic(name + " actuelle:", obj[-1], value)
                    self.build_field_value_generic(name + " actuelle:" + " N-2", obj[-2], value)
                elif l >= 3:
                    self.build_field_value_generic(name + " actuelle:", obj[-1], value)
                    self.build_field_value_generic(name + " actuelle:" + " N-2", obj[-2], value)
                    self.build_field_value_generic(name + " actuelle:" + " N-3", obj[-3], value)
            else:
                self.build_field_value_generic(name + " actuelle:", obj[-1], value)
        elif type(obj) == dict:
            for it in obj:
                self.build_field_value_generic(name + " " + str(it), obj[it], value)
        else:
            value[name] = "Aucune donnée"

    def complete_model_from_positionable(self, name, obj, out, classname):
        if type(obj) is str:
            name = self.label_identification(classname, name)
            out.append([QStandardItem(name), QStandardItem(obj)])
        elif type(obj) in [int, float, bool]:
            name = self.label_identification(classname, name)
            out.append([QStandardItem(name), QStandardItem(str(obj))])
        elif type(obj) is list:
            l = len(obj)
            if name == "prestationIds":
                if l == 1:
                    self.complete_model_from_positionable(name + " actuelle:", obj[-1], out, classname)
                elif l == 2:
                    self.complete_model_from_positionable(name + " actuelle:", obj[-1], out)
                    self.complete_model_from_positionable(name + " actuelle:" + " N-2", obj[-2], out, classname)
                elif l >= 3:
                    self.complete_model_from_positionable(name + " actuelle:", obj[-1], out, classname)
                    self.complete_model_from_positionable(name + " actuelle:" + " N-2", obj[-2], out, classname)
                    self.complete_model_from_positionable(name + " actuelle:" + " N-3", obj[-3], out, classname)
            else:
                self.complete_model_from_positionable(name + " actuelle:", obj[-1], out, classname)
        elif type(obj) is dict:
            for it in obj:
                self.complete_model_from_positionable(name + " " + it, obj[it], out, classname)
        else:
            out.append([QStandardItem(name), QStandardItem("type inconnu")])

    def label_identification(self, className, title):
        icn = {
            "observations": "Observation",
            "photos": "Photo",
            "gestions": "Gestion",
            "proprietes": "Propriete",
            "pointsLeveDZ": "PointDZ",
            "mesures": "MesureMonteeEaux",
            "mesuresDZ": "MesureLigneEauPrZ"
        }
        fem = [
            "digueIds",
            "bergeIds",
            "crueSubmersionIds",
            "echelleLimnimetriqueIds",
            "ouvertureBatardableIds",
            "planifications",
            "voieDigueIds",
            "prestationIds",
            "voieAccesIds",
            "borneIds",
            "stationPompageIds",
            "photos",
            "observations",
            "ouvrageParticulierIds",
            "proprietes",
            "mesuresDZ",
            "mesures",
            "gestions",
            "prestationIds"
        ]
        mas = [
            "intervenantsIds",
            "reseauTelecomEnergieIds",
            "reseauHydrauliqueCielOuvertIds",
            "ouvrageTelecomEnergieIds",
            "articleIds",
            "ouvrageFranchissementIds",
            "ouvrageRevancheIds",
            "ouvrageHydrauliqueAssocieIds",
            "ouvrageVoirieIds",
            "levePositionIds",
            "desordreIds",
            "reseauHydrauliqueFermeIds",
            "evenementHydrauliqueIds",
            "seuilIds",
            "rapportEtudeIds",
            "pointsLeveDZ",
        ]

        if ' ' in title:
            if title == "prestationIds actuelle:":
                return "Prestation actuelle"
            if title == "prestationIds actuelle: N-2":
                return "Avant derniere Prestation"
            if title == "prestationIds actuelle: N-3":
                return "Prestation N-3"

            tab = title.split(' ')
            # Define the adjective matches
            for i in range(len(tab)):
                if tab[i] == "actuelle:":
                    if tab[i-1] in mas:
                        tab[i] = "actuel:"

            # Convert SIRS id into label
            if len(tab) == 3 or len(tab) == 5:
                attr = tab[-1]
                className = tab[-3]
                if className in icn:
                    className = icn[className]
                if className in self.labels:
                    if attr in self.labels[className]:
                        tab[-1] = self.labels[className][attr]
            if len(tab) == 2:
                attr = tab[0]
                if className in self.labels:
                    if attr in self.labels[className]:
                        tab[0] = self.labels[className][attr]
            if len(tab) == 3 or len(tab) == 5:
                attr = tab[0]
                if attr in icn:
                    tab[0] = icn[attr]
            if len(tab) == 5:
                attr = tab[2]
                if attr in icn:
                    tab[2] = icn[attr]

            # Remove 's' at the end of word
            if len(tab) == 2:
                if "actuel" in tab[1] and tab[0][-1] == 's':
                    tab[0] = tab[0][:-1]

            # Remove ':' at the end of actuel adjective
            if len(tab) == 2:
                if "actuel" in tab[1] and tab[1][-1] == ':':
                    tab[1] = tab[1][:-1]

            return ' '.join(tab)

        if className in self.labels:
            if title in self.labels[className]:
                title = self.labels[className][title]
        return title

    def get_label_from_attribute(self, className, attribute):
        if className in self.labels:
            if attribute in self.labels[className]:
                return self.labels[className][attribute]
            else:
                return attribute
        else:
            return attribute
