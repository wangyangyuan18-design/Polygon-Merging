# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import QAction, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QRadioButton, QButtonGroup, QLineEdit, QPushButton, QMessageBox, QProgressBar, QCheckBox
from qgis.core import QgsProject, QgsWkbTypes, QgsVectorLayer, QgsFeature, QgsField, QgsGeometry, QgsPointXY
from qgis.PyQt.QtCore import QVariant
import math


class PolygonMergingPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None

    def initGui(self):
        self.action = QAction("Polygon Merging", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Polygon Merging", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu("&Polygon Merging", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        layers = [lyr for lyr in QgsProject.instance().mapLayers().values()
                  if isinstance(lyr, QgsVectorLayer) and lyr.isValid()
                  and lyr.geometryType() == QgsWkbTypes.PolygonGeometry]
        if not layers:
            QMessageBox.warning(self.iface.mainWindow(), "Polygon Merging", "当前工程没有可用的多边形图层。")
            return
        MergeDialog(self.iface, layers).exec_()


class MergeDialog(QDialog):
    def __init__(self, iface, layers):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.layers = layers
        self.setWindowTitle("Polygon Merging - 外轮廓连接")
        self.setMinimumWidth(480)
        root = QVBoxLayout(self)
        root.addWidget(QLabel("输入多边形图层"))
        self.layer_combo = QComboBox()
        for layer in layers:
            self.layer_combo.addItem(layer.name(), layer.id())
        root.addWidget(self.layer_combo)

        root.addWidget(QLabel("处理范围"))
        self.scope_group = QButtonGroup(self)
        self.rb_selected = QRadioButton("仅处理选中要素")
        self.rb_all = QRadioButton("处理整个图层")
        self.rb_name = QRadioButton("按名称包含内容分组处理（每组输出一个整体）")
        self.rb_selected.setChecked(True)
        for i, rb in enumerate((self.rb_selected, self.rb_all, self.rb_name)):
            self.scope_group.addButton(rb, i)
            root.addWidget(rb)

        row = QHBoxLayout()
        row.addWidget(QLabel("名称包含："))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：KIM-HB")
        row.addWidget(self.name_edit)
        root.addLayout(row)
        note = QLabel("输出为纯外轮廓线：不填充多边形。分离区域之间直接连接最近的两个外环顶点（单条直线），不生成缓冲区、圆弧或内部边线。")
        note.setWordWrap(True)
        root.addWidget(note)

        self.keep_source = QCheckBox("保留原始图层（不修改源数据）")
        self.keep_source.setChecked(True)
        self.keep_source.setEnabled(False)
        root.addWidget(self.keep_source)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        root.addWidget(self.progress)
        buttons = QHBoxLayout()
        self.run_btn = QPushButton("开始处理")
        close_btn = QPushButton("关闭")
        buttons.addStretch(1)
        buttons.addWidget(self.run_btn)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)
        self.run_btn.clicked.connect(self.process)
        close_btn.clicked.connect(self.reject)
        self.rb_name.toggled.connect(self.name_edit.setEnabled)
        self.name_edit.setEnabled(False)

    def process(self):
        layer = QgsProject.instance().mapLayer(self.layer_combo.currentData())
        if not layer or not layer.isValid():
            QMessageBox.warning(self, "提示", "输入图层无效。")
            return
        mode = self.scope_group.checkedId()
        if mode == 0:
            feats = list(layer.getSelectedFeatures())
            if not feats:
                QMessageBox.warning(self, "提示", "当前没有选中任何要素。")
                return
            groups = [("Selected", feats)]
        elif mode == 1:
            groups = [("All", list(layer.getFeatures()))]
        else:
            needle = self.name_edit.text().strip()
            if not needle:
                QMessageBox.warning(self, "提示", "请输入名称包含内容。")
                return
            fields = layer.fields()
            names = [f.name() for f in fields]
            field_name = next((n for n in ("Name", "NAME", "name") if n in names), None)
            if field_name is None:
                field_name = next((f.name() for f in fields if f.type() == QVariant.String), None)
            if field_name is None:
                QMessageBox.warning(self, "提示", "没有可用于名称匹配的文本字段。")
                return
            idx = fields.indexFromName(field_name)
            buckets = {}
            for feat in layer.getFeatures():
                val = feat.attribute(idx)
                if val is not None and needle.casefold() in str(val).casefold():
                    buckets.setdefault(str(val), []).append(feat)
            if not buckets:
                QMessageBox.information(self, "结果", "没有找到名称包含该内容的要素。")
                return
            groups = sorted(buckets.items(), key=lambda x: x[0].casefold())

        self.run_btn.setEnabled(False)
        self.progress.setValue(0)
        try:
            out = QgsVectorLayer("MultiLineString?crs=" + layer.crs().authid(), layer.name() + "_Outer_Outline_Line", "memory")
            if not out.isValid():
                raise Exception("无法创建输出图层。")
            provider = out.dataProvider()
            provider.addAttributes([
                QgsField("Group_Name", QVariant.String, len=254),
                QgsField("Feature_Count", QVariant.Int),
                QgsField("Source_IDs", QVariant.String, len=10000),
                QgsField("Connects", QVariant.Int)
            ])
            out.updateFields()
            failures = []
            total = len(groups)
            for pos, (group_name, group_feats) in enumerate(groups, 1):
                geoms, ids = [], []
                for feat in group_feats:
                    geom = QgsGeometry(feat.geometry())
                    if geom.isNull() or geom.isEmpty():
                        continue
                    if not geom.isGeosValid():
                        geom = geom.makeValid()
                    if not geom.isNull() and not geom.isEmpty():
                        geoms.append(geom)
                        ids.append(str(feat.id()))
                if geoms:
                    try:
                        merged, connects = merge_and_connect(geoms)
                        f = QgsFeature(out.fields())
                        f.setGeometry(merged)
                        f.setAttributes([str(group_name)[:254], len(ids), ",".join(ids)[:10000], connects])
                        provider.addFeature(f)
                    except Exception as exc:
                        failures.append(str(group_name) + ": " + str(exc))
                else:
                    failures.append(str(group_name) + ": no valid polygon geometry")
                self.progress.setValue(int(pos * 100 / total))
            out.updateExtents()
            if out.featureCount() == 0:
                raise Exception("没有生成任何结果。\n" + "\n".join(failures[:10]))
            QgsProject.instance().addMapLayer(out)
            self.iface.setActiveLayer(out)
            message = "处理完成。\n输出外轮廓线数量：" + str(out.featureCount())
            if failures:
                message += "\n失败/跳过：" + str(len(failures)) + "\n" + "\n".join(failures[:8])
            QMessageBox.information(self, "Polygon Merging", message)
        except Exception as exc:
            QMessageBox.critical(self, "处理失败", str(exc))
        finally:
            self.run_btn.setEnabled(True)


def polygon_parts(geom):
    """Return each polygon component as a single-part geometry."""
    parts = []
    if geom.isNull() or geom.isEmpty():
        return parts
    if QgsWkbTypes.geometryType(geom.wkbType()) != QgsWkbTypes.PolygonGeometry:
        for subgeom in geom.asGeometryCollection():
            parts.extend(polygon_parts(subgeom))
        return parts
    polygons = geom.asMultiPolygon() if geom.isMultipart() else [geom.asPolygon()]
    for poly in polygons:
        if poly and poly[0]:
            part = QgsGeometry.fromPolygonXY(poly)
            if not part.isNull() and not part.isEmpty():
                parts.append(part)
    return parts


def exterior_vertices(poly_geom):
    polygons = poly_geom.asMultiPolygon() if poly_geom.isMultipart() else [poly_geom.asPolygon()]
    if not polygons or not polygons[0] or not polygons[0][0]:
        return []
    ring = [QgsPointXY(p) for p in polygons[0][0]]
    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()
    return ring


def closest_vertex_pair(a, b):
    av, bv = exterior_vertices(a), exterior_vertices(b)
    if not av or not bv:
        raise Exception("无法读取多边形外环顶点")
    best, best_d2 = None, float("inf")
    for p in av:
        for q in bv:
            dx, dy = p.x() - q.x(), p.y() - q.y()
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best, best_d2 = (p, q), d2
    return best[0], best[1], math.sqrt(best_d2)


def merge_and_connect(geometries):
    """
    Dissolve source polygons, extract only exterior rings, then connect
    disconnected polygon components with straight vertex-to-vertex lines.
    No buffer, corridor, rounded cap, or synthetic intermediate vertex.
    """
    merged = QgsGeometry.unaryUnion(geometries)
    if merged.isNull() or merged.isEmpty():
        raise Exception("几何融合失败")
    if not merged.isGeosValid():
        merged = merged.makeValid()

    parts = polygon_parts(merged)
    if not parts:
        raise Exception("没有可用的多边形外环")

    # Extract only exterior rings after dissolving overlaps/touching polygons.
    line_geometries = []
    for part in parts:
        ring = exterior_vertices(part)
        if len(ring) < 3:
            continue
        ring.append(ring[0])
        line_geometries.append(QgsGeometry.fromPolylineXY(ring))

    # Kruskal minimum spanning tree: connect every disconnected component
    # with exactly one straight segment between the nearest exterior vertices.
    count = len(parts)
    parent = list(range(count))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    candidates = []
    for i in range(count):
        for j in range(i + 1, count):
            p, q, dist = closest_vertex_pair(parts[i], parts[j])
            candidates.append((dist, i, j, p, q))
    candidates.sort(key=lambda item: item[0])

    connects = 0
    for dist, i, j, p, q in candidates:
        ri, rj = find(i), find(j)
        if ri == rj:
            continue
        parent[ri] = rj
        line_geometries.append(QgsGeometry.fromPolylineXY([p, q]))
        connects += 1
        if connects == count - 1:
            break

    if count > 1 and connects != count - 1:
        raise Exception("未能将所有分离区域连接起来")

    # Union linework only; no buffer and no polygon fill.
    result = QgsGeometry.unaryUnion(line_geometries)
    if result.isNull() or result.isEmpty():
        raise Exception("生成外轮廓线失败")
    if QgsWkbTypes.geometryType(result.wkbType()) != QgsWkbTypes.LineGeometry:
        raise Exception("最终结果不是线几何")
    if not result.isMultipart():
        result.convertToMultiType()
    return result, connects
