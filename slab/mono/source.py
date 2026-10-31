"""Reads one layer of the original Trupeer Slab source as plain outlines:
name -> {width, unicode, contours, anchors}, each contour a list of [x, y, type] nodes
(line, curve, offcurve, as Glyphs stores them), with components drawn in place,
and anchors as {name: [x, y]}."""
import os
import glyphsLib

SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sources', 'TrupeerSlab.glyphs')
_font = None


def load(layer_name):
    global _font
    if _font is None:
        _font = glyphsLib.GSFont(SOURCE)
    f = _font

    def layer(g):
        for l in g.layers:
            if l.name == layer_name:
                return l

    def flat(g, tx=(1, 0, 0, 1, 0, 0)):
        a, b, c, d, e, f_ = tx
        l = layer(g)
        out = [[[a * n.position.x + c * n.position.y + e, b * n.position.x + d * n.position.y + f_, n.type]
                for n in p.nodes] for p in l.paths]
        for comp in l.components:
            A, B, C, D, E, F = comp.transform
            out.extend(flat(f.glyphs[comp.name],
                            (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
                             a * E + c * F + e, b * E + d * F + f_)))
        return out

    data = {}
    for g in f.glyphs:
        l = layer(g)
        if l is not None:
            data[g.name] = dict(width=l.width, unicode=g.unicode, contours=flat(g),
                                anchors={a.name: [a.position.x, a.position.y] for a in l.anchors})
    return data
