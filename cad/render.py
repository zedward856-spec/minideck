import _here  # noqa: F401  (repo root as the working dir)
import pyvista as pv
pv.OFF_SCREEN = True
def render(meshes, out, views=('iso',), size=(1400, 700), labels=None):
    """meshes: list of (stl_path_or_pv_mesh, color, opacity). views: camera positions per subplot."""
    p = pv.Plotter(off_screen=True, shape=(1, len(views)), window_size=size, border=False)
    for i, v in enumerate(views):
        p.subplot(0, i)
        for m, c, a in meshes:
            mm = pv.read(m) if isinstance(m, str) else m
            p.add_mesh(mm, color=c, opacity=a, smooth_shading=False, show_edges=False)
        p.set_background('white')
        if isinstance(v, str): getattr(p, f'view_{v}')()
        else: p.camera_position = v
        p.camera.zoom(1.2)
        if labels: p.add_text(labels[i], font_size=10, color='black')
    p.screenshot(out)
