# Polygon Merging (QGIS Plugin)

QGIS plugin for dissolving polygon features and connecting disconnected components into filled polygon outputs.

## Features

- Process selected polygon features, an entire layer, or groups selected by a name substring.
- Dissolve overlapping/touching polygons and remove internal shared boundaries.
- For disconnected components, find the nearest pair of exterior-ring vertices.
- Connect each pair with a bridge of **5 metres total width** (2.5 m buffer radius on each side of the straight connector).
- Bridge distances are calculated in a local UTM CRS, then results are transformed back to the source layer CRS. This also supports source layers stored in geographic coordinates.
- Remove interior holes from the final filled geometry.
- Output is a temporary **MultiPolygon** memory layer; original input data is not modified.

## Install

In QGIS, open Plugins > Manage and Install Plugins > Install from ZIP, then select the plugin ZIP.

## Name grouping

The name mode uses the Name field when present; otherwise it uses the first text field. Matching features are grouped by their complete field value. Each distinct matching value produces one output feature.

## Output styling

The output is a filled polygon layer. Apply a fill color such as orange and a red outline in Layer Styling to reproduce the intended appearance. Right-click the temporary layer and choose Make Permanent to save it.
