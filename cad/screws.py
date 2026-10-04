"""M2 countersunk screws (stainless, hex socket) for the assembly view, at every screw in the design."""
import _here  # noqa: F401  (repo root as the working dir)
import numpy as np, trimesh, manifold3d as mf
import base as B, lid as Ld

HEAD_D, HEAD_H, SHANK_D = 3.8, 1.0, 2.0

def _m(t):
    t = t.copy(); t.merge_vertices()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))

def screw(length):
    """head top at z=0, pointing down -z (countersunk head, hex socket, plain shank)."""
    prof = [[0, 0], [HEAD_D / 2, 0], [SHANK_D / 2, -HEAD_H], [SHANK_D / 2, -length], [0, -length]]
    body = trimesh.creation.revolve(np.array(prof), sections=40)
    hexr = trimesh.creation.cylinder(radius=0.73, height=1.6, sections=6)   # 1.27 mm hex key
    hexr.apply_translation([0, 0, 0.0])
    out = (_m(body) - _m(hexr)).to_mesh()
    return trimesh.Trimesh(out.vert_properties[:, :3], out.tri_verts)

def placed():
    """{'base': mesh, 'lid': mesh} in the case frame (lid ones in the closed lid)."""
    base, lid = [], []
    for x, y in B.PLATE_SCREWS:                       # keyboard plate: head flush in the top
        s = screw(4.0); s.apply_translation([x, y, B.TOP_Z]); base.append(s)
    for x, y in B.HATCH_SCREWS:                       # hatch: from underneath, pointing up
        s = screw(4.0); s.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        s.apply_translation([x, y, 0.0]); base.append(s)
    for x, y in Ld.BEZEL_SCREWS:                      # bezel: from the screen face, pointing into the lid
        s = screw(4.0); s.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        s.apply_translation([x, y, Ld.LZ0]); lid.append(s)
    return {"base": trimesh.util.concatenate(base), "lid": trimesh.util.concatenate(lid)}

if __name__ == "__main__":
    P = placed()
    P["base"].export("out/parts_in_place/screws_base.stl"); P["lid"].export("out/parts_in_place/screws_lid.stl")
    print("screws: base", len(B.PLATE_SCREWS) + len(B.HATCH_SCREWS), "lid", len(Ld.BEZEL_SCREWS))
