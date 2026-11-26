# Polygon Merging (QGIS Plugin)

QGIS plugin for merging polygon features and automatically connecting disconnected polygon components.

## Features

- Merge selected polygon features.
- Merge all polygon features in a layer.
- Group features by a text field value containing a manually entered substring. Each distinct matching field value becomes one output feature.
- For disconnected components, find the nearest pair of exterior-ring vertices, create a minimum-tolerance bridge, and union the result.
- Original input layer is never edited or deleted.

## Install

1. Download the ZIP package from the latest successful GitHub Actions run or Releases.
2. In QGIS open Plugins > Manage and Install Plugins > Install from ZIP.
3. Select the downloaded ZIP and enable Polygon Merging.
4. Open it from the Plugins menu or toolbar.

## Geometry note

A mathematically zero-width line cannot reliably turn separate polygon components into one valid Polygon. The plugin therefore uses a tiny automatically derived coordinate tolerance for the bridge. It is not a fixed-width corridor parameter. For best metric interpretation, use a projected CRS with suitable linear units rather than EPSG:4326.

## Name grouping

The name mode uses the Name field when present; otherwise it uses the first text field. Features whose field value contains the entered substring are grouped by their complete field value. Each distinct matching value produces one output feature.

## Compatibility

Designed for QGIS 3.28+; target environment is QGIS 3.40.x. Output is a temporary memory layer; right-click it and choose Make Permanent to save it.
