"""
Organic 3D mesh primitives (elliptical lofted segments & subdivided spheres)
for articulated character & broadcast equipment rigs.
"""

import math
import bpy
import bmesh
from mathutils import Vector


def make_lofted_segment(
    name: str,
    p0: Vector,
    p1: Vector,
    r0_xy=(0.06, 0.06),
    r1_xy=(0.05, 0.05),
    rings: int = 5,
    sides: int = 20,
    cap_ends: bool = True,
    bulge: float = 0.0,
    mat=None,
    col=None,
    parent=None,
):
    """Smooth elliptical lofted tube between 3D points p0 and p1 (in parent's local space)."""
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()

    axis = p1 - p0
    length = max(axis.length, 1e-4)
    z_dir = axis / length
    ref = Vector((0.0, 1.0, 0.0)) if abs(z_dir.y) < 0.9 else Vector((1.0, 0.0, 0.0))
    x_dir = ref.cross(z_dir).normalized()
    y_dir = z_dir.cross(x_dir).normalized()

    ring_verts = []
    for r_i in range(rings):
        t = r_i / float(rings - 1)
        center = p0.lerp(p1, t)
        bell = math.sin(t * math.pi) * bulge
        rx = r0_xy[0] * (1.0 - t) + r1_xy[0] * t + bell
        ry = r0_xy[1] * (1.0 - t) + r1_xy[1] * t + bell

        v_ring = []
        for s_i in range(sides):
            ang = 2.0 * math.pi * s_i / sides
            pt = center + x_dir * (math.cos(ang) * rx) + y_dir * (math.sin(ang) * ry)
            v_ring.append(bm.verts.new(pt))
        ring_verts.append(v_ring)

    for r_i in range(rings - 1):
        rA = ring_verts[r_i]
        rB = ring_verts[r_i + 1]
        for s_i in range(sides):
            s_next = (s_i + 1) % sides
            f = bm.faces.new((rA[s_i], rA[s_next], rB[s_next], rB[s_i]))
            f.smooth = True

    if cap_ends:
        c0 = bm.verts.new(p0 - z_dir * (min(r0_xy) * 0.25))
        c1 = bm.verts.new(p1 + z_dir * (min(r1_xy) * 0.25))
        for s_i in range(sides):
            s_next = (s_i + 1) % sides
            f0 = bm.faces.new((ring_verts[0][s_next], ring_verts[0][s_i], c0))
            f0.smooth = True
            f1 = bm.faces.new((ring_verts[-1][s_i], ring_verts[-1][s_next], c1))
            f1.smooth = True

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    if col:
        col.objects.link(obj)
    return obj


def make_sphere(name: str, center, radii=(0.06, 0.06, 0.06), rot_deg=(0, 0, 0), subs: int = 3, mat=None, col=None, parent=None):
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subs, radius=1.0)
    bmesh.ops.scale(bm, vec=radii, verts=bm.verts)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = center
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    if col:
        col.objects.link(obj)
    return obj
