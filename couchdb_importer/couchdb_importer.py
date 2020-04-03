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
import os.path

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon, QStandardItem, QStandardItemModel
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsGeometry, QgsProject, QgsLineString, Qgis

# DO NOT DELETE. Initialize Qt resources from file resources.py.
from .resources import *
from .couchdb_importer_dialog import CouchdbImporterDialog
from .couchdb_connector import CouchdbConnector, CouchdbConnectorException
from .couchdb_data import CouchdbData
from .couchdb_layer import CouchdbBuilder
from .utils import Utils


class CouchdbImporter:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CouchdbImporter_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Couchdb Importer')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        # Couchdb mutable
        self.connector = None
        self.currentPositionableClass = ""
        self.loadedPositionable = []
        self.data = CouchdbData()
        self.provider = CouchdbBuilder()
        self.lengthParameter = 1  # unit meter
        self.projection = "projeté"
        self.alwaysSelectedAttribute = ["_id", "geometry", "@class", "libelle", "designation"]
        self.errorMsg = {'noproj': {}, 'noabs': {}, 'nogeom': {}, 'alreadyloaded': {}}

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CouchdbImporter', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/couchdb_importer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Import Couchdb Data'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Couchdb Importer'),
                action)
            self.iface.removeToolBarIcon(action)

    """
    /****************************************************************
    * Request Database
    ****************************************************************/  
    """

    def collect_data_from_user_selection(self):
        try:
            self.loadedPositionable.clear()
            lu = 75 / len(self.data)
            completed = 0

            for className in self.data.getClassName():
                if self.data.getSelected(className):
                    attributes = Utils.build_list_from_selection(self.data.getAttributes(className))
                    if self.data.getIds(className) == "all":
                        result = self.connector.request_database_from_class(className, attributes)
                    else:
                        ids = Utils.build_list_from_selection(self.data.getIds(className))
                        result = self.connector.request_database_from_class_and_ids(className, attributes, ids)
                    self.loadedPositionable.extend(result)
                completed = completed + lu
                self.dlg.progressBar.setValue(completed)
        except ConnectionRefusedError:
            self.basic_message("CouchdbConnectorException", "Impossible de se connecter, vérifier l'url ou l'ouverture de la base.", Qgis.Warning)
            raise CouchdbConnectorException("Impossible de se connecter à la base")

    def collect_data_from_layers_ids(self):
        try:
            self.connector = None
            http, addr = Utils.parse_url(self.dlg.url.text())
            self.connector = CouchdbConnector(http, addr, self.dlg.login.text(), self.dlg.password.text())
            ids = Utils.collect_ids_from_layers_filtered_by_positionable_class(self.data.getClassName())

            return self.connector.request_database_from_ids(self.dlg.database.currentText(), ids)
        except ConnectionRefusedError:
            self.basic_message("CouchdbConnectorException", "Impossible de se connecter, vérifier l'url ou l'ouverture de la base.", Qgis.Warning)
            raise CouchdbConnectorException("Impossible de se connecter à la base")

    """
    /****************************************************************
    * Utils
    ****************************************************************/  
    """

    def complete_data_with_ids(self):
        for className in self.data.getClassName():
            self.data.setIds(className, {})
        for pos in self.loadedPositionable:
            className = pos["@class"].split("fr.sirs.core.model.")[1]
            self.data.setIdValue(className, pos["_id"], True)

    def build_wkt(self, data):
        classNameComplete = data["@class"]
        className = classNameComplete.split("fr.sirs.core.model.")[1]

        if self.projection == "projeté":
            if "geometry" in data.keys():
                return data["geometry"]
            else:
                if className not in self.errorMsg['noproj']:
                    self.errorMsg['noproj'][className] = []
                self.errorMsg['noproj'][className].append(data["_id"])
                return None
        elif self.projection == "absolu":
            if "approximatePositionDebut" in data.keys() and "approximatePositionFin" in data.keys():
                a = data["approximatePositionDebut"]
                b = data["approximatePositionFin"]
                geomA = QgsGeometry.fromWkt(a)
                geomB = QgsGeometry.fromWkt(b)
                return QgsLineString(geomA, geomB).asWkt()
            else:
                if "geometry" in data.keys():
                    if className not in self.errorMsg['noabs']:
                        self.errorMsg['noabs'][className] = []
                    self.errorMsg['noabs'][className].append(data["_id"])
                    return data["geometry"]
                else:
                    if className not in self.errorMsg['nogeom']:
                        self.errorMsg['nogeom'][className] = []
                    self.errorMsg['nogeom'][className].append(data["_id"])
                    return None

    """
    /****************************************************************
    * Modify UI access field.
    ****************************************************************/  
    """

    def set_ui_access_connection(self):
        # enable connection param
        self.dlg.url.setEnabled(True)
        self.dlg.login.setEnabled(True)
        self.dlg.password.setEnabled(True)
        self.dlg.loginButton.setEnabled(True)
        self.dlg.resetConnectionButton.setEnabled(True)
        self.dlg.selectAllPositionableClass.setCheckable(False)
        self.dlg.selectAllAttribute.setCheckable(False)
        self.dlg.addLayers.setEnabled(False)
        self.dlg.updateLayers.setEnabled(False)
        # disable all other
        self.dlg.database.setEnabled(False)
        self.dlg.detailButton.setEnabled(False)
        self.dlg.resetDatabaseButton.setEnabled(False)
        self.dlg.positionableClass.setEnabled(False)
        self.dlg.attribute.setEnabled(False)
        self.dlg.positionable.setEnabled(False)
        self.dlg.detail.setEnabled(False)

    def set_ui_access_database(self):
        # enable database param
        self.dlg.resetConnectionButton.setEnabled(True)
        self.dlg.database.setEnabled(True)
        self.dlg.detailButton.setEnabled(True)
        self.dlg.resetDatabaseButton.setEnabled(True)
        self.dlg.positionableClass.setEnabled(True)
        self.dlg.attribute.setEnabled(True)
        self.dlg.selectAllPositionableClass.setCheckable(True)
        self.dlg.selectAllAttribute.setCheckable(True)
        self.dlg.addLayers.setEnabled(True)
        self.dlg.updateLayers.setEnabled(True)

        # disable all other
        self.dlg.url.setEnabled(False)
        self.dlg.login.setEnabled(False)
        self.dlg.password.setEnabled(False)
        self.dlg.loginButton.setEnabled(False)
        self.dlg.positionable.setEnabled(False)
        self.dlg.detail.setEnabled(False)

    def set_ui_access_detail(self):
        # enable database param
        self.dlg.resetConnectionButton.setEnabled(True)
        self.dlg.resetDatabaseButton.setEnabled(True)
        self.dlg.positionable.setEnabled(True)
        self.dlg.detail.setEnabled(True)
        self.dlg.addLayers.setEnabled(True)
        self.dlg.updateLayers.setEnabled(True)
        # disable all other
        self.dlg.database.setEnabled(False)
        self.dlg.detailButton.setEnabled(False)
        self.dlg.positionableClass.setEnabled(False)
        self.dlg.attribute.setEnabled(False)
        self.dlg.url.setEnabled(False)
        self.dlg.login.setEnabled(False)
        self.dlg.password.setEnabled(False)
        self.dlg.loginButton.setEnabled(False)
        self.dlg.selectAllPositionableClass.setCheckable(False)
        self.dlg.selectAllAttribute.setCheckable(True)

    """
    /****************************************************************
    * Build UI ListView
    ****************************************************************/  
    """

    def build_list_positionable_class(self):
        model = QStandardItemModel()
        for obj in self.data.getClassName():
            item = QStandardItem(obj)
            item.setCheckState(Qt.Checked)
            item.setCheckable(True)
            model.appendRow(item)
        model.itemChanged.connect(self.on_positionable_class_list_changed)
        self.dlg.positionableClass.setModel(model)

    def build_list_attribute(self):
        model = QStandardItemModel()
        for attr in self.data.getAttributes(self.currentPositionableClass):
            item = QStandardItem(attr)
            if attr in self.alwaysSelectedAttribute:
                item.setCheckable(False)
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckable(True)
                if self.data.getAttributes(self.currentPositionableClass)[attr]:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
            model.appendRow(item)
        model.itemChanged.connect(self.on_attribute_list_changed)
        self.dlg.attribute.setModel(model)

    def build_list_positionable(self):
        model = QStandardItemModel()
        lu = 25 / len(self.loadedPositionable)
        completed = 75
        for pos in self.loadedPositionable:
            name = Utils.build_row_name_positionable(pos)
            item = QStandardItem(name)
            item.setCheckable(True)
            item.setCheckState(Qt.Checked)
            model.appendRow(item)
            completed = completed + lu
            self.dlg.progressBar.setValue(completed)
        model.itemChanged.connect(self.on_positionable_list_changed)
        self.dlg.positionable.setModel(model)
        self.dlg.progressBar.setValue(0)

    def change_positionable_class(self, state):
        model = QStandardItemModel()
        for className in self.data.getClassName():
            self.data.setSelected(className, state)
            item = QStandardItem(className)
            item.setCheckable(True)
            if state:
                self.data.setIds(className, "all")
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            model.appendRow(item)
        model.itemChanged.connect(self.on_positionable_class_list_changed)
        self.dlg.positionableClass.setModel(model)

    def change_positionable(self, state):
        model = QStandardItemModel()
        for className in self.data.getClassName():
            for id in self.data.getIds(className):
                self.data.setIdValue(className, id, state)
        for pos in self.loadedPositionable:
            name = Utils.build_row_name_positionable(pos)
            item = QStandardItem(name)
            item.setCheckable(True)
            if state:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            model.appendRow(item)
        model.itemChanged.connect(self.on_positionable_list_changed)
        self.dlg.positionable.setModel(model)

    def change_attribute(self, state):
        model = QStandardItemModel()
        for attr in self.data.getAttributes(self.currentPositionableClass):
            item = QStandardItem(attr)
            if attr in self.alwaysSelectedAttribute:
                item.setCheckable(False)
                item.setCheckState(Qt.Checked)
                self.data.setAttributeValue(self.currentPositionableClass, attr, True)
            else:
                item.setCheckable(True)
                self.data.setAttributeValue(self.currentPositionableClass, attr, state)
                if state:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
            model.appendRow(item)
        model.itemChanged.connect(self.on_attribute_list_changed)
        self.dlg.attribute.setModel(model)

    """
    /****************************************************************
    * Action methods
    ****************************************************************/  
    """

    def on_login_click(self):
        try:
            http, addr = Utils.parse_url(self.dlg.url.text())
            self.connector = CouchdbConnector(http, addr, self.dlg.login.text(), self.dlg.password.text())
            fc = self.connector.getFilteredConnection()
            self.dlg.database.addItems([name for name in fc])
            self.build_list_positionable_class()
            self.set_ui_access_database()
        except ConnectionRefusedError:
            self.basic_message("CouchdbConnectorException", "Impossible de se connecter, vérifier l'url ou l'ouverture de la base.", Qgis.Warning)
            raise CouchdbConnectorException("Impossible de se connecter à la base")
        except ValueError:
            self.basic_message("CouchdbConnectorException", "Impossible de se connecter, vérifier l'url ou l'ouverture de la base.", Qgis.Warning)
            raise CouchdbConnectorException("Impossible de se connecter à la base")

    def on_detail_click(self):
        self.collect_data_from_user_selection()
        self.complete_data_with_ids()
        self.build_list_positionable()
        self.set_ui_access_detail()

    def on_positionable_class_click(self, item):
        model = self.dlg.positionableClass.model()
        model.blockSignals(True)
        self.currentPositionableClass = model.itemFromIndex(item).text()
        self.build_list_attribute()
        model.blockSignals(False)

    def on_positionable_click(self, item):
        model = self.dlg.positionable.model()
        rowName = model.itemFromIndex(item)
        id = str(rowName.text()).split(' - ')[-1]
        selected = None
        for pos in self.loadedPositionable:
            if pos["_id"] == id:
                selected = pos
                break
        if selected is None:
            model.blockSignals(False)
            return
        model = QStandardItemModel()
        listStandardItem = []
        for s in selected:
            Utils.complete_model_from_positionable(s, selected[s], listStandardItem)
        for row in listStandardItem:
            model.appendRow(row)
        self.dlg.detail.setModel(model)

    def on_select_all_positionable_class_click(self):
        if self.dlg.selectAllPositionableClass.checkState() == Qt.Checked:
            self.change_positionable_class(True)
        if self.dlg.selectAllPositionableClass.checkState() == Qt.Unchecked:
            self.change_positionable_class(False)

    def on_select_all_positionable_click(self):
        if self.dlg.selectAllPositionable.checkState() == Qt.Checked:
            self.change_positionable(True)
        if self.dlg.selectAllPositionable.checkState() == Qt.Unchecked:
            self.change_positionable(False)

    def on_select_all_attribute_click(self):
        if self.dlg.selectAllAttribute.checkState() == Qt.Checked:
            self.change_attribute(True)
        if self.dlg.selectAllAttribute.checkState() == Qt.Unchecked:
            self.change_attribute(False)

    def on_reset_connection_click(self):
        # reset database
        self.on_reset_database_click()
        # reset connection
        self.connector = None
        # reset url, login and password fields
        self.dlg.url.setText("")
        self.dlg.login.setText("")
        self.dlg.password.setText("")
        # reset database combobox
        self.dlg.database.clear()
        # reset positionable class list
        model = self.dlg.positionableClass.model()
        if model:
            model.removeRows(0, model.rowCount())
        # change access
        self.set_ui_access_connection()

    def on_reset_database_click(self):
        # reset list object
        self.loadedPositionable = []
        self.data.reset_from_configuration()
        # reset list ui
        modelPositionable = self.dlg.positionable.model()
        if modelPositionable:
            modelPositionable.removeRows(0, modelPositionable.rowCount())
        modelAttribute = self.dlg.attribute.model()
        if modelAttribute:
            modelAttribute.removeRows(0, modelAttribute.rowCount())
        modelDetail = self.dlg.detail.model()
        if modelDetail:
            modelDetail.removeRows(0, modelDetail.rowCount())
        # build list positionable class
        self.build_list_positionable_class()
        # change access
        self.set_ui_access_database()

    def on_attribute_list_changed(self, item):
        attributeSelected = str(item.text())
        state = True
        if item.checkState() == Qt.Checked:
            state = True
        if item.checkState() == Qt.Unchecked:
            state = False
        self.data.setAttributeValue(self.currentPositionableClass, attributeSelected, state)

    def on_positionable_list_changed(self, item):
        id = str(item.text()).split(' - ')[-1]
        className = str(item.text()).split(' - ')[0]
        if item.checkState() == Qt.Checked:
            self.data.setIdValue(className, id, True)
        if item.checkState() == Qt.Unchecked:
            self.data.setIdValue(className, id, False)

    def on_positionable_class_list_changed(self, item):
        if item.checkState() == Qt.Checked:
            self.data.setSelected(item.text(), True)
            self.data.setIds(item.text(), "all")
        if item.checkState() == Qt.Unchecked:
            self.data.setSelected(item.text(), False)

    def on_projection_click(self):
        if self.dlg.projete.isChecked():
            self.projection = "projeté"
        if self.dlg.absolu.isChecked():
            self.projection = "absolu"

    def on_update_layers_click(self):
        result = self.collect_data_from_layers_ids()
        rl = list(result)
        ln = len(rl)
        if ln == 0:
            self.simple_message(
                "Les Identifiants trouvés dans les couches ne trouvent pas de référence en base de donnée.", Qgis.Info)
            self.dlg.close()
            return
        self.update_layers(rl, ln)
        self.dlg.progressBar.setValue(0)
        self.display_messages()
        self.dlg.close()

    def on_add_layers_click(self):
        self.data.write_configuration()
        self.collect_data_from_user_selection()
        self.complete_data_with_ids()
        ids = Utils.collect_ids_from_layers_filtered_by_user_selection(self.data.getAllId())
        llp = len(self.loadedPositionable)
        if llp == 0:
            self.simple_message("Aucune vue sélectionné.", Qgis.Info)
            self.dlg.progressBar.setValue(0)
            self.dlg.close()
            return
        self.add_layers(ids, llp)
        self.dlg.progressBar.setValue(0)
        self.display_messages()
        self.dlg.close()

    """
    /****************************************************************
    * Build and add/update layers to Qgis
    ****************************************************************/  
    """

    def update_layers(self, loaded, ln):
        lu = 100 / ln
        completed = 0

        for data in loaded:
            id = data["_id"]
            classNameComplete = data["@class"]
            className = classNameComplete.split("fr.sirs.core.model.")[1]
            wkt = self.build_wkt(data)
            if wkt is None:
                continue
            geom = Utils.build_geometry(wkt, self.lengthParameter)
            if geom is None:
                self.simple_message("Type de geometrie inconnu", Qgis.Warning)
                continue
            typ = geom.wkbType()
            layer = Utils.filter_layers_by_name_and_geometry_type(className, typ)
            if layer.wkbType() != typ:
                msg = "Mise à jour impossible. Pour cette donnée, \
                le type de géométrie a changé et n'est plus celle de\
                 sa couche actuelle. Veuillez supprimer puis réimporter\
                  la caractéristique de la couche correspondant à cette donnée\
                   pour éffectuer sa mise à jour."
                self.basic_message(msg, "couche: " + layer.name() + "donnée: " + str(id), Qgis.Warning)
                continue

            provider = layer.dataProvider()
            features = layer.getFeatures()
            for feat in features:
                if feat['_id'] == id:
                    provider.deleteFeatures([feat.id()])
            feature = self.provider.build_feature(data, geom, layer, self.data)
            provider.addFeature(feature)
            layer.updateExtents()
            # progress bar
            completed = completed + lu
            self.dlg.progressBar.setValue(completed)

    def add_layers(self, ids, llp):
        root = QgsProject.instance().layerTreeRoot()
        lu = 25 / llp
        completed = 75
        allLayers = {}

        for data in self.loadedPositionable:
            id = data["_id"]
            classNameComplete = data["@class"]
            className = classNameComplete.split("fr.sirs.core.model.")[1]
            if id in ids:
                if className not in self.errorMsg['alreadyloaded']:
                    self.errorMsg['alreadyloaded'][className] = []
                self.errorMsg['alreadyloaded'][className].append(id)
                continue
            # build geometry
            wkt = self.build_wkt(data)
            if wkt is None:
                continue
            geom = Utils.build_geometry(wkt, self.lengthParameter)
            if geom is None:
                self.basic_message("Type de géométrie non reconnu", str(id), Qgis.Warning)
                continue
            typ = geom.wkbType()
            # is layer already exist
            currentLayer = Utils.filter_layers_by_name_and_geometry_type(className, typ)
            if currentLayer is None:
                # build layer if not exist
                if className not in allLayers:
                    allLayers[className] = {}
                if typ not in allLayers[className]:
                    allLayers[className][typ] = self.provider.build_layer(className, geom, self.data)
                layer = allLayers[className][typ]
            else:
                layer = currentLayer
            # build feature
            feature = self.provider.build_feature(data, geom, layer, self.data)
            # add the new feature to the layer
            provider = layer.dataProvider()
            provider.addFeature(feature)
            layer.updateExtents()
            # sort layers in correspond class
            group = root.findGroup(className)
            if group is None:
                group = root.addGroup(className)
            # progress bar
            completed = completed + lu
            self.dlg.progressBar.setValue(completed)
        # complete group
        for className in allLayers:
            group = root.findGroup(className)
            for type in allLayers[className]:
                QgsProject.instance().addMapLayer(allLayers[className][type], False)
                group.addLayer(allLayers[className][type])

    """
    /****************************************************************
    * Communicate with user
    ****************************************************************/  
    """

    def display_messages(self):
        if bool(self.errorMsg['noproj']):
            self.stacked_message("Aucune donnée projetée pour les objets", self.errorMsg['noproj'], Qgis.Warning)
        if bool(self.errorMsg['noabs']):
            self.stacked_message("Aucune position réelle trouvée: Utilisation des données projetées pour les objets", self.errorMsg['noabs'], Qgis.Warning)
        if bool(self.errorMsg['nogeom']):
            self.stacked_message("Aucune donnée de géométrie trouvée pour les objets", self.errorMsg['nogeom'], Qgis.Warning)
        if bool(self.errorMsg['alreadyloaded']):
            self.stacked_message("Les données suivantes sont déjà chargées. Clickez sur 'Mise à jour des couches' pour actualiser ces données", self.errorMsg['alreadyloaded'], Qgis.Info)
        # clear error message
        self.errorMsg = {'noproj': {}, 'noabs': {}, 'nogeom': {}, 'alreadyloaded': {}}

    def simple_message(self, msg, level):
        widget = self.iface.messageBar().createMessage(msg)
        self.iface.messageBar().pushWidget(widget, level, 5)

    def basic_message(self, msg1, msg2, level):
        widget = self.iface.messageBar().createMessage(msg1, msg2)
        self.iface.messageBar().pushWidget(widget, level, 5)

    def stacked_message(self, msg1, dictClassName, level):
        msg2 = ""
        for className in dictClassName:
            msg2 = msg2 + className.upper() + "(" + ", ".join(dictClassName[className]) + "), "
        widget = self.iface.messageBar().createMessage(msg1, msg2)
        self.iface.messageBar().pushWidget(widget, level, 5)

    """
    /****************************************************************
    * Running method
    ****************************************************************/  
    """

    def run(self):

        if self.first_start == True:
            self.first_start = False
            self.dlg = CouchdbImporterDialog()
            # load action
            self.dlg.loginButton.clicked.connect(self.on_login_click)
            self.dlg.detailButton.clicked.connect(self.on_detail_click)
            # select all action
            self.dlg.selectAllPositionableClass.stateChanged.connect(self.on_select_all_positionable_class_click)
            self.dlg.selectAllPositionable.stateChanged.connect(self.on_select_all_positionable_click)
            self.dlg.selectAllAttribute.stateChanged.connect(self.on_select_all_attribute_click)
            # reset action
            self.dlg.resetConnectionButton.clicked.connect(self.on_reset_connection_click)
            self.dlg.resetDatabaseButton.clicked.connect(self.on_reset_database_click)
            # detail action
            self.dlg.positionable.clicked.connect(self.on_positionable_click)
            self.dlg.positionableClass.clicked.connect(self.on_positionable_class_click)
            # display action
            self.dlg.absolu.clicked.connect(self.on_projection_click)
            self.dlg.projete.clicked.connect(self.on_projection_click)
            # add / update layers action
            self.dlg.addLayers.clicked.connect(self.on_add_layers_click)
            self.dlg.updateLayers.clicked.connect(self.on_update_layers_click)
            # initialize ui access and data
            self.on_reset_connection_click()
            # set default url connection
            self.dlg.url.setText("http://localhost:5984")
            # set default choice of projection
            self.dlg.projete.setChecked(True)
            # set progress bar value
            self.dlg.progressBar.setValue(0)

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        #result = self.dlg.exec_()
        # See if OK was pressed
        #if result:
        #    pass
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            # pass
