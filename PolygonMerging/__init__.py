def classFactory(iface):
    from .polygon_merging import PolygonMergingPlugin
    return PolygonMergingPlugin(iface)
