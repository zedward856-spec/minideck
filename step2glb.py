"""Coloured STEP -> trimesh meshes (one per colour), keeping the colours the STEP file carries.

    from step2glb import load_coloured
    parts = load_coloured("models/x.stp", tol=0.05)   # [(trimesh, (r, g, b)), ...] in the STEP's frame

    python3 step2glb.py in.stp out.glb [tol]        # quick standalone conversion
"""
import sys, numpy as np, trimesh
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorTool, XCAFDoc_ColorSurf, XCAFDoc_ColorGen
from OCP.collections import Sequence_TDF_Label as TDF_LabelSequence
from OCP.TDF import TDF_Label
from OCP.Quantity import Quantity_Color, Quantity_TOC_sRGB
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
from OCP.IFSelect import IFSelect_RetDone


def _colour(ctool, obj):
    c = Quantity_Color()
    for t in (XCAFDoc_ColorSurf, XCAFDoc_ColorGen):
        ok = XCAFDoc_ColorTool.GetColor_s(obj, t, c) if isinstance(obj, TDF_Label) else ctool.GetColor(obj, t, c)
        if ok:
            r, g, b = c.Values(Quantity_TOC_sRGB)
            return (round(r, 3), round(g, 3), round(b, 3))
    return None


def load_coloured(path, tol=0.05, default=(0.5, 0.5, 0.5)):
    doc = TDocStd_Document(TCollection_ExtendedString("doc"))
    rd = STEPCAFControl_Reader(); rd.SetColorMode(True); rd.SetNameMode(True)
    if rd.ReadFile(path) != IFSelect_RetDone:
        raise IOError(path)
    rd.Transfer(doc)
    stool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ctool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    groups = {}

    def walk(label, loc, inherited):
        shape = stool.GetShape_s(label)
        col = _colour(ctool, label) or _colour(ctool, shape) or inherited
        if stool.IsAssembly_s(label) or stool.IsReference_s(label):
            if stool.IsReference_s(label):
                ref = TDF_Label(); stool.GetReferredShape_s(label, ref)
                walk(ref, loc * stool.GetLocation_s(label), col)
                return
            kids = TDF_LabelSequence(); stool.GetComponents_s(label, kids)
            for i in range(1, kids.Length() + 1):
                walk(kids.Value(i), loc, col)
            return
        shape = shape.Moved(loc)
        BRepMesh_IncrementalMesh(shape, tol, False, 0.5, True)
        exp = TopExp_Explorer(shape, TopAbs_FACE)
        while exp.More():
            face = TopoDS.Face(exp.Current()) if hasattr(TopoDS, "Face") else TopoDS.Face_s(exp.Current())
            fc = _colour(ctool, face) or col or default
            L = TopLoc_Location()
            tri = BRep_Tool.Triangulation_s(face, L)
            if tri is not None:
                T = L.Transformation()
                v = np.array([[*tri.Node(i).Transformed(T).Coord()] for i in range(1, tri.NbNodes() + 1)])
                f = np.array([tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)]) - 1
                if face.Orientation() == TopAbs_REVERSED:
                    f = f[:, ::-1]
                groups.setdefault(fc, []).append(trimesh.Trimesh(v, f, process=False))
            exp.Next()

    roots = TDF_LabelSequence(); stool.GetFreeShapes(roots)
    for i in range(1, roots.Length() + 1):
        walk(roots.Value(i), TopLoc_Location(), None)
    out = []
    for col, ms in groups.items():
        m = trimesh.util.concatenate(ms); m.merge_vertices()
        out.append((m, col))
    return out


if __name__ == "__main__":
    parts = load_coloured(sys.argv[1], float(sys.argv[3]) if len(sys.argv) > 3 else 0.05)
    sc = trimesh.Scene()
    for i, (m, c) in enumerate(parts):
        m.visual.face_colors = [int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), 255]
        sc.add_geometry(m, geom_name=f"c{i}")
    sc.export(sys.argv[2])
    print(len(parts), "colours,", sum(len(m.faces) for m, _ in parts), "faces")
