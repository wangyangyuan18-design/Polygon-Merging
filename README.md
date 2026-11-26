# Polygon Merging (QGIS Plugin)

QGIS plugin that creates clean exterior outline linework from polygon features.

## Features

- Process selected polygon features.
- Process all polygon features in a layer.
- Group features by a text field value containing a manually entered substring. Each distinct matching field value becomes one output feature.
- Dissolve overlapping/touching polygons and remove internal shared boundaries.
- Extract exterior rings only; interior holes are omitted.
- Connect disconnected components by finding the nearest pair of exterior-ring vertices and adding one straight two-vertex line segment.
- No buffer, corridor width, rounded caps, or synthetic arc vertices are generated.
- Original input layer is never edited or deleted.

## Output

The result is a temporary **MultiLineString** memory layer, not a filled polygon. Each output feature contains the exterior boundary linework and straight connector segments for its group. Use the layer's line symbology to display the outline; no polygon fill is involved.

## Install

1. Download the ZIP package from the latest successful GitHub Actions run or Releases.
2. In QGIS open Plugins > Manage and Install Plugins > Install from ZIP.
3. Select the downloaded ZIP and enable Polygon Merging.
4. Open it from the Plugins menu or toolbar.

## Name grouping

The name mode uses the Name field when present; otherwise it uses the first text field. Features whose field value contains the entered substring are grouped by their complete field value. Each distinct matching value produces one output feature.

## Compatibility

Designed for QGIS 3.28+; target environment is QGIS 3.40.x. Output is a temporary memory layer; right-click it and choose Make Permanent to save it.
