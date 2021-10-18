# Couchdb Importer

Couchdb Importer is a QGIS plugin that allows users to build Vector layers
from Couchdb data.

Features:
  - Connecting to Couchdb database.
  - Add new features.
  - Update current features.
  - Support Point, LineString and Polygon geometry types.
  - Object properties are imported into attribute table of layers.

Usage:
  - Hit connection button to view all your database
  - Choose database
  - Choose class object
  - Choose attribute of class object
  - Choose one by one object
  - Choose projection type
  - Hit Add layer button to create QGIS layers
  - Hit Update layer button to update the current layers data.

# Installation
## Requirements
- QGIS version 3.4 or later

## Install manually from zip file in QGIS
You can import the zip package directly through Qgis plugin manager.
1. In QGIS, navigate to menu **Plugins** > **Manage and Install Plugins...** > **Install from ZIP**, then select the downloaded zip file.
2. Switch to tab **Installed**, make sure the plugin `Couchdb importer` is enabled.
3. Activate the plugin (with the checkbox).
4. You can see the Couchdb Importer icon at the QGIS action bar, if plugin is activated.

# New Objects
######TODO should pursue the same goal  but with java class of object<br />
You can integrate new objects from property files generate by SIRS, modulate some adjustments.
  - Add to the newModel folder, the property files of object to be integrated.
  - Run the script displayJsonEquivalentFromPropertyFiles.py from this folder, and use the option -a, -l or -p according to the configuration you want to watch as json format
  - Copy/paste the printing objects to the according file.
  - Launch the script updateStyles.py from the folder to update the defined style contained in the user_preference_correspondence.json
