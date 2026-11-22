"""
Architectural & furniture geometry builder for the State Reception Hall 3D scene.
"""

import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler


def get_or_create_collection(name: str):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def make_box(
    name: str,
    size=(1.0, 1.0, 1.0),
    loc=(0.0, 0.0, 0.0),
    rot_deg=(0.0, 0.0, 0.0),
    bevel: float = 0.012,
    segs: int = 2,
    mat=None,
    col=None,
    parent=None,
    uv_mode: str = "box",
    uv_rect=(0.0, 0.0, 1.0, 1.0),
):
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)

    if bevel > 0.0:
        max_b = min(size) * 0.42
        b_amt = min(bevel, max_b)
        bmesh.ops.bevel(
            bm,
            geom=list(bm.edges),
            offset=b_amt,
            segments=segs,
            profile=0.5,
            affect="EDGES",
        )

    uv_layer = bm.loops.layers.uv.verify()
    u0, v0, u1, v1 = uv_rect
    sx, sy, sz = [max(s, 1e-4) for s in size]

    for face in bm.faces:
        face.smooth = bevel > 0.0
        n = face.normal
        for loop in face.loops:
            co = loop.vert.co
            if uv_mode == "top_planar":
                u = (co.x / sx + 0.5) * (u1 - u0) + u0
                v = (co.y / sy + 0.5) * (v1 - v0) + v0
            elif uv_mode == "front_planar":
                u = (co.x / sx + 0.5) * (u1 - u0) + u0
                v = (co.z / sz + 0.5) * (v1 - v0) + v0
            else:
                if abs(n.z) > 0.6:
                    u, v = co.x / sx + 0.5, co.y / sy + 0.5
                elif abs(n.y) > 0.6:
                    u, v = co.x / sx + 0.5, co.z / sz + 0.5
                else:
                    u, v = co.y / sy + 0.5, co.z / sz + 0.5
                u = u * (u1 - u0) + u0
                v = v * (v1 - v0) + v0
            loop[uv_layer].uv = (u, v)

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    if col:
        col.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)
    return obj


def make_lathe(
    name: str,
    profile_rz,
    segments: int = 36,
    loc=(0.0, 0.0, 0.0),
    rot_deg=(0.0, 0.0, 0.0),
    mat=None,
    col=None,
    parent=None,
):
    """Spin a list of (radius, z) points around Z axis."""
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm = bmesh.new()

    verts = [bm.verts.new((r, 0.0, z)) for (r, z) in profile_rz]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]

    bmesh.ops.spin(
        bm,
        geom=verts + edges,
        cent=(0.0, 0.0, 0.0),
        axis=(0.0, 0.0, 1.0),
        angle=2.0 * math.pi,
        steps=segments,
        use_merge=True,
    )
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    z_vals = [p[1] for p in profile_rz]
    z_min, z_max = min(z_vals), max(z_vals)
    z_span = max(z_max - z_min, 1e-4)
    uv_layer = bm.loops.layers.uv.verify()
    for face in bm.faces:
        face.smooth = True
        for loop in face.loops:
            co = loop.vert.co
            ang = (math.atan2(co.y, co.x) + math.pi) / (2.0 * math.pi)
            vz = (co.z - z_min) / z_span
            loop[uv_layer].uv = (ang, vz)

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    if mat:
        obj.data.materials.append(mat)
    if parent:
        obj.parent = parent
    if col:
        col.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)
    return obj


def build_teacup_set(name_prefix: str, loc, mats: dict, col, lid_ajar: bool = False):
    """Great Hall lidded blue-and-white porcelain teacup with saucer."""
    root = bpy.data.objects.new(name_prefix + "_Root", None)
    root.location = loc
    col.objects.link(root)

    # Saucer
    saucer_prof = [(0.0, 0.0), (0.042, 0.0), (0.068, 0.011), (0.064, 0.014), (0.038, 0.004), (0.0, 0.004)]
    make_lathe(name_prefix + "_Saucer", saucer_prof, segments=28, mat=mats["porcelain_white"], col=col, parent=root)

    # Cup body
    cup_prof = [
        (0.0, 0.005),
        (0.030, 0.005),
        (0.039, 0.055),
        (0.043, 0.098),
        (0.040, 0.098),
        (0.035, 0.055),
        (0.026, 0.010),
        (0.0, 0.010),
    ]
    make_lathe(name_prefix + "_Cup", cup_prof, segments=32, mat=mats["porcelain_cup"], col=col, parent=root)

    # Cup handle (delicate curved loop)
    mesh_h = bpy.data.meshes.new(name_prefix + "_HandleMesh")
    bm = bmesh.new()
    pts = [
        (0.038, 0.0, 0.082),
        (0.058, 0.0, 0.080),
        (0.060, 0.0, 0.054),
        (0.052, 0.0, 0.032),
        (0.034, 0.0, 0.028),
    ]
    for i in range(len(pts) - 1):
        p0, p1 = Vector(pts[i]), Vector(pts[i + 1])
        mid = (p0 + p1) * 0.5
        seg = bmesh.ops.create_cube(bm, size=1.0)
        v_seg = seg["verts"]
        bmesh.ops.scale(bm, vec=(0.006, 0.006, (p1 - p0).length * 1.15), verts=v_seg)
        rot_q = Vector((0, 0, 1)).rotation_difference((p1 - p0).normalized())
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot_q.to_matrix(), verts=v_seg)
        bmesh.ops.translate(bm, vec=mid, verts=v_seg)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh_h)
    bm.free()
    h_obj = bpy.data.objects.new(name_prefix + "_Handle", mesh_h)
    h_obj.data.materials.append(mats["porcelain_white"])
    h_obj.parent = root
    col.objects.link(h_obj)

    # Domed porcelain lid with finial knob
    lid_prof = [
        (0.0, 0.096),
        (0.045, 0.096),
        (0.044, 0.101),
        (0.026, 0.114),
        (0.008, 0.118),
        (0.011, 0.126),
        (0.006, 0.130),
        (0.0, 0.130),
    ]
    lid_loc = (0.008, -0.005, 0.002) if lid_ajar else (0.0, 0.0, 0.0)
    lid_rot = (7.0, 10.0, 0.0) if lid_ajar else (0.0, 0.0, 0.0)
    make_lathe(
        name_prefix + "_Lid",
        lid_prof,
        segments=28,
        loc=lid_loc,
        rot_deg=lid_rot,
        mat=mats["porcelain_cup"],
        col=col,
        parent=root,
    )
    return root


def build_diplomatic_armchair(name: str, loc, yaw_deg: float, mats: dict, col):
    """
    Authentic Great Hall of the People wide cream upholstered armchair
    with carved rosewood base and white crochet lace antimacassars.
    Front of chair faces -Y when yaw_deg == 0.
    """
    root = bpy.data.objects.new(name, None)
    root.location = loc
    root.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
    col.objects.link(root)

    # Carved rosewood base frame & 4 short legs
    make_box(name + "_WoodBase", (0.90, 0.82, 0.07), (0.0, 0.0, 0.13), bevel=0.012, mat=mats["rosewood"], col=col, parent=root)
    for lx in (-0.40, 0.40):
        for ly in (-0.36, 0.36):
            make_box(
                f"{name}_Leg_{lx:.1f}_{ly:.1f}",
                (0.075, 0.075, 0.11),
                (lx, ly, 0.055),
                bevel=0.015,
                mat=mats["rosewood"],
                col=col,
                parent=root,
            )

    # Lower upholstered apron & plush seat cushion
    make_box(name + "_SeatApron", (0.88, 0.80, 0.13), (0.0, 0.0, 0.22), bevel=0.025, mat=mats["armchair_fabric"], col=col, parent=root)
    make_box(name + "_SeatCushion", (0.64, 0.72, 0.15), (0.0, -0.03, 0.35), bevel=0.045, segs=3, mat=mats["armchair_fabric"], col=col, parent=root)

    # Left & Right curved plush armrests + front rosewood trim knuckles
    for side, sx in (("L", -0.38), ("R", 0.38)):
        make_box(
            f"{name}_Arm_{side}",
            (0.17, 0.82, 0.35),
            (sx, -0.01, 0.43),
            bevel=0.055,
            segs=3,
            mat=mats["armchair_fabric"],
            col=col,
            parent=root,
        )
        # Decorative carved rosewood front accent panel on armrest
        make_box(
            f"{name}_ArmWood_{side}",
            (0.09, 0.04, 0.24),
            (sx, -0.415, 0.38),
            bevel=0.012,
            mat=mats["rosewood"],
            col=col,
            parent=root,
        )
        # White crochet lace armrest cover (扶手巾)
        make_box(
            f"{name}_ArmLace_{side}",
            (0.184, 0.56, 0.005),
            (sx, -0.06, 0.611),
            bevel=0.001,
            mat=mats["lace"],
            col=col,
            parent=root,
            uv_mode="top_planar",
        )
        # Side drape flaps of armrest lace
        for dx, rot_y in ((-0.095, 82.0), (0.095, -82.0)):
            make_box(
                f"{name}_ArmLaceFlap_{side}_{dx:.2f}",
                (0.11, 0.54, 0.005),
                (sx + dx, -0.06, 0.555),
                rot_deg=(0.0, rot_y, 0.0),
                bevel=0.001,
                mat=mats["lace"],
                col=col,
                parent=root,
                uv_mode="top_planar",
            )

    # Tall stately reclined backrest + softly arched crown
    make_box(
        name + "_Backrest",
        (0.86, 0.20, 0.66),
        (0.0, 0.30, 0.66),
        rot_deg=(-10.0, 0.0, 0.0),
        bevel=0.06,
        segs=3,
        mat=mats["armchair_fabric"],
        col=col,
        parent=root,
    )
    make_box(
        name + "_BackCrown",
        (0.74, 0.18, 0.14),
        (0.0, 0.355, 0.96),
        rot_deg=(-10.0, 0.0, 0.0),
        bevel=0.055,
        segs=3,
        mat=mats["armchair_fabric"],
        col=col,
        parent=root,
    )

    # White crochet lace headrest antimacassar (标志性白色蕾丝靠头巾: front flap + top + rear flap)
    make_box(
        name + "_HeadLace_Front",
        (0.56, 0.008, 0.30),
        (0.0, 0.228, 0.85),
        rot_deg=(-10.0, 0.0, 0.0),
        bevel=0.001,
        mat=mats["lace"],
        col=col,
        parent=root,
        uv_mode="front_planar",
    )
    make_box(
        name + "_HeadLace_Top",
        (0.56, 0.19, 0.008),
        (0.0, 0.352, 1.032),
        rot_deg=(-10.0, 0.0, 0.0),
        bevel=0.001,
        mat=mats["lace"],
        col=col,
        parent=root,
        uv_mode="top_planar",
    )
    make_box(
        name + "_HeadLace_Rear",
        (0.56, 0.008, 0.22),
        (0.0, 0.456, 0.91),
        rot_deg=(-10.0, 0.0, 0.0),
        bevel=0.001,
        mat=mats["lace"],
        col=col,
        parent=root,
        uv_mode="front_planar",
    )

    return root


def build_tea_table(name: str, loc, yaw_deg: float, mats: dict, col, center_floral: bool = False):
    """Carved rosewood diplomatic side tea table with white lace doily."""
    root = bpy.data.objects.new(name, None)
    root.location = loc
    root.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
    col.objects.link(root)

    w_tbl = 0.58 if center_floral else 0.50
    h_tbl = 0.54
    # Tabletop & carved apron
    make_box(name + "_Top", (w_tbl, w_tbl, 0.036), (0.0, 0.0, h_tbl), bevel=0.008, mat=mats["rosewood"], col=col, parent=root)
    make_box(name + "_Apron", (w_tbl - 0.05, w_tbl - 0.05, 0.065), (0.0, 0.0, h_tbl - 0.045), bevel=0.006, mat=mats["rosewood"], col=col, parent=root)
    # Lower lattice shelf
    make_box(name + "_Shelf", (w_tbl - 0.08, w_tbl - 0.08, 0.022), (0.0, 0.0, 0.17), bevel=0.005, mat=mats["rosewood"], col=col, parent=root)

    off = w_tbl * 0.5 - 0.045
    for lx in (-off, off):
        for ly in (-off, off):
            make_box(
                f"{name}_Leg_{lx:.2f}_{ly:.2f}",
                (0.045, 0.045, h_tbl - 0.02),
                (lx, ly, (h_tbl - 0.02) * 0.5),
                bevel=0.008,
                mat=mats["rosewood"],
                col=col,
                parent=root,
            )

    # Single-sheet upward-facing white crochet lace table doily (zero bottom face -> zero Z-fighting!)
    doily_w = w_tbl * 0.78
    doily_z = h_tbl + 0.023  # 5mm clear of tabletop (0.558m)
    mesh_d = bpy.data.meshes.new(name + "_LaceDoily_mesh")
    bm_d = bmesh.new()
    hw = doily_w * 0.5
    v0 = bm_d.verts.new((-hw, -hw, doily_z))
    v1 = bm_d.verts.new((hw, -hw, doily_z))
    v2 = bm_d.verts.new((hw, hw, doily_z))
    v3 = bm_d.verts.new((-hw, hw, doily_z))
    face_d = bm_d.faces.new((v0, v1, v2, v3))
    uv_d = bm_d.loops.layers.uv.verify()
    for lp, uv_co in zip(face_d.loops, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))):
        lp[uv_d].uv = uv_co
    bm_d.to_mesh(mesh_d)
    bm_d.free()
    doily_obj = bpy.data.objects.new(name + "_LaceDoily", mesh_d)
    doily_obj.data.materials.append(mats["lace"])
    doily_obj.parent = root
    col.objects.link(doily_obj)

    if center_floral:
        # Low porcelain floral bowl + crimson & gold blooms + foliage
        bowl_prof = [(0.0, 0.0), (0.075, 0.0), (0.115, 0.045), (0.105, 0.048), (0.065, 0.008), (0.0, 0.008)]
        make_lathe(
            name + "_FlowerBowl",
            bowl_prof,
            segments=24,
            loc=(0.0, 0.03, doily_z + 0.004),
            mat=mats["porcelain_white"],
            col=col,
            parent=root,
        )
        # Foliage base
        make_box(
            name + "_FloralFoliage",
            (0.24, 0.20, 0.075),
            (0.0, 0.03, h_tbl + 0.072),
            bevel=0.032,
            segs=2,
            mat=mats["leaf_palm"],
            col=col,
            parent=root,
        )
        # Individual crimson & gold flower blossoms
        blooms = [
            (0.0, 0.03, 0.115, 0.046, "flower_red"),
            (-0.065, 0.01, 0.098, 0.040, "flower_red"),
            (0.065, 0.01, 0.098, 0.040, "flower_red"),
            (-0.035, 0.075, 0.102, 0.038, "flower_gold"),
            (0.038, 0.072, 0.102, 0.038, "flower_gold"),
            (0.0, -0.035, 0.092, 0.038, "flower_gold"),
        ]
        for idx, (bx, by, bz, br, mkey) in enumerate(blooms):
            make_box(
                f"{name}_Bloom_{idx}",
                (br * 1.4, br * 1.4, br * 1.1),
                (bx, by, h_tbl + bz),
                rot_deg=(idx * 17.0, idx * 23.0, idx * 37.0),
                bevel=br * 0.45,
                segs=2,
                mat=mats[mkey],
                col=col,
                parent=root,
            )

    return root


def build_potted_palm(name: str, loc, mats: dict, col, scale: float = 1.0):
    """Lush Great Hall potted Kentia palm in a white/blue porcelain planter."""
    root = bpy.data.objects.new(name, None)
    root.location = loc
    root.scale = (scale, scale, scale)
    col.objects.link(root)

    # Rosewood plant stand + white porcelain planter pot
    stand_prof = [(0.0, 0.0), (0.19, 0.0), (0.17, 0.08), (0.20, 0.10), (0.0, 0.10)]
    make_lathe(name + "_Stand", stand_prof, segments=24, mat=mats["rosewood"], col=col, parent=root)

    pot_prof = [
        (0.0, 0.10),
        (0.16, 0.10),
        (0.24, 0.44),
        (0.26, 0.48),
        (0.23, 0.48),
        (0.21, 0.43),
        (0.0, 0.43),
    ]
    make_lathe(name + "_Planter", pot_prof, segments=28, mat=mats["porcelain_cup"], col=col, parent=root)
    make_lathe(name + "_Soil", [(0.0, 0.42), (0.21, 0.42), (0.21, 0.44), (0.0, 0.44)], segments=20, mat=mats["soil_dark"], col=col, parent=root)

    # Graceful feathery pinnate Kentia palm fronds (羽状散尾葵叶片)
    mesh_f = bpy.data.meshes.new(name + "_FrondsMesh")
    bm = bmesh.new()
    n_fronds = 13
    for i in range(n_fronds):
        az = (2.0 * math.pi * i / n_fronds) + (i % 3) * 0.16
        tier = i % 3
        reach = 0.68 + tier * 0.24
        peak_h = 1.36 + (2 - tier) * 0.30

        prev_pt = Vector((0.0, 0.0, 0.44))
        steps = 11
        for s in range(1, steps + 1):
            t = s / float(steps)
            r = reach * t
            z = 0.44 + (peak_h - 0.44) * math.sin(t * math.pi * 0.66) - 0.22 * (t ** 2)
            cur_pt = Vector((math.cos(az) * r, math.sin(az) * r, z))

            seg_vec = cur_pt - prev_pt
            seg_dir = seg_vec.normalized()
            mid = (prev_pt + cur_pt) * 0.5
            rot_q = Vector((0, 0, 1)).rotation_difference(seg_dir)

            # Slender central rachis stem
            st = bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, vec=(0.012, 0.012, seg_vec.length * 1.08), verts=st["verts"])
            bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot_q.to_matrix(), verts=st["verts"])
            bmesh.ops.translate(bm, vec=mid, verts=st["verts"])

            # Paired slender pointed pinnate leaflets fanning left & right
            if s >= 2:
                side_vec = Vector((-math.sin(az), math.cos(az), 0.0))
                leaflet_len = (0.22 * math.sin(t * math.pi * 0.90) + 0.04)
                for side_sign in (-1.0, 1.0):
                    leaf_dir = (side_vec * side_sign * 0.78 + seg_dir * 0.55 + Vector((0, 0, -0.24))).normalized()
                    l_q = Vector((0, 0, 1)).rotation_difference(leaf_dir)
                    lf = bmesh.ops.create_cube(bm, size=1.0)
                    # Taper tip of leaflet
                    for v in lf["verts"]:
                        taper = 0.25 if v.co.z > 0 else 1.0
                        v.co.x *= 0.024 * taper
                        v.co.y *= 0.004
                        v.co.z = (v.co.z + 0.5) * leaflet_len
                    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=l_q.to_matrix(), verts=lf["verts"])
                    bmesh.ops.translate(bm, vec=mid, verts=lf["verts"])

            prev_pt = cur_pt

    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh_f)
    bm.free()

    fronds_obj = bpy.data.objects.new(name + "_Fronds", mesh_f)
    fronds_obj.data.materials.append(mats["leaf_palm"])
    fronds_obj.parent = root
    col.objects.link(fronds_obj)
    return root


def build_floor_vase(name: str, loc, mats: dict, col):
    """Grand blue-and-white Chinese porcelain floor vase on carved rosewood stand."""
    root = bpy.data.objects.new(name, None)
    root.location = loc
    col.objects.link(root)

    stand_prof = [(0.0, 0.0), (0.22, 0.0), (0.20, 0.06), (0.18, 0.24), (0.21, 0.28), (0.0, 0.28)]
    make_lathe(name + "_Pedestal", stand_prof, segments=28, mat=mats["rosewood"], col=col, parent=root)

    vase_prof = [
        (0.0, 0.28),
        (0.15, 0.28),
        (0.25, 0.56),
        (0.28, 0.84),
        (0.21, 1.06),
        (0.12, 1.18),
        (0.14, 1.32),
        (0.18, 1.38),
        (0.16, 1.39),
        (0.11, 1.31),
        (0.10, 1.16),
        (0.0, 1.14),
    ]
    make_lathe(name + "_PorcelainBody", vase_prof, segments=36, mat=mats["porcelain_cup"], col=col, parent=root)
    return root


def build_seven_panel_screen(loc, mats: dict, col):
    """
    7-panel carved rosewood & gold-leaf standing screen (人民大会堂香港厅大型座屏)
    with seamless panoramic landscape UV mapping across all 7 panels.
    """
    root = bpy.data.objects.new("Arch_SevenPanel_Screen", None)
    root.location = loc
    col.objects.link(root)

    panel_w = 0.74
    panel_h = 3.18
    panel_angles = [-13.0, 9.0, -7.0, 0.0, 7.0, -9.0, 13.0]

    # Compute exact hinged panel center positions from left to right
    x_cursor = 0.0
    y_cursor = 0.0
    centers = []
    for ang_deg in panel_angles:
        rad = math.radians(ang_deg)
        dx = math.cos(rad) * panel_w
        dy = math.sin(rad) * panel_w
        centers.append((x_cursor + dx * 0.5, y_cursor + dy * 0.5, ang_deg))
        x_cursor += dx
        y_cursor += dy

    # Center horizontally around X = 0
    mid_x = x_cursor * 0.5
    mid_y = sum(c[1] for c in centers) / len(centers)

    for idx, (cx, cy, ang_deg) in enumerate(centers):
        px = cx - mid_x
        py = cy - mid_y

        p_root = bpy.data.objects.new(f"Screen_Panel_{idx+1}", None)
        p_root.location = (px, py, 0.0)
        p_root.rotation_euler = (0.0, 0.0, math.radians(ang_deg))
        p_root.parent = root
        col.objects.link(p_root)

        # Rosewood outer frame + brass feet
        make_box(
            f"Screen_Frame_{idx+1}",
            (panel_w, 0.065, panel_h - 0.14),
            (0.0, 0.0, 0.14 + (panel_h - 0.14) * 0.5),
            bevel=0.008,
            mat=mats["rosewood"],
            col=col,
            parent=p_root,
        )
        # Carved top crest rail with gilded trim
        make_box(
            f"Screen_Crest_{idx+1}",
            (panel_w + 0.02, 0.085, 0.09),
            (0.0, 0.0, panel_h + 0.03),
            bevel=0.01,
            mat=mats["rosewood"],
            col=col,
            parent=p_root,
        )
        make_box(
            f"Screen_GoldBar_{idx+1}",
            (panel_w - 0.06, 0.072, 0.022),
            (0.0, 0.0, panel_h - 0.02),
            bevel=0.004,
            mat=mats["gold_brass"],
            col=col,
            parent=p_root,
        )
        for sx in (-panel_w * 0.44, panel_w * 0.44):
            make_box(
                f"Screen_Foot_{idx+1}_{sx:.2f}",
                (0.07, 0.22, 0.14),
                (sx, 0.0, 0.07),
                bevel=0.01,
                mat=mats["rosewood"],
                col=col,
                parent=p_root,
            )
            make_box(
                f"Screen_BrassShoe_{idx+1}_{sx:.2f}",
                (0.078, 0.23, 0.035),
                (sx, 0.0, 0.018),
                bevel=0.004,
                mat=mats["gold_brass"],
                col=col,
                parent=p_root,
            )

        # Artwork insert face (front and back) mapped to exact 1/7th slice of screen_panels.png
        u0 = idx / 7.0
        u1 = (idx + 1) / 7.0
        make_box(
            f"Screen_Canvas_{idx+1}",
            (panel_w - 0.05, 0.072, panel_h - 0.24),
            (0.0, 0.0, 0.19 + (panel_h - 0.24) * 0.5),
            bevel=0.003,
            mat=mats["screen_art"],
            col=col,
            parent=p_root,
            uv_mode="front_planar",
            uv_rect=(u0, 0.0, u1, 1.0),
        )

    return root


def build_crystal_chandelier(loc, mats: dict, col):
    """Grand 3-tier Great Hall crystal & gilded brass chandelier."""
    root = bpy.data.objects.new("Arch_Chandelier_Main", None)
    root.location = loc
    col.objects.link(root)

    # Ceiling rose & downrod
    make_lathe(
        "Chandelier_Canopy",
        [(0.0, 0.95), (0.36, 0.95), (0.32, 0.88), (0.06, 0.84), (0.04, 0.15), (0.0, 0.15)],
        segments=28,
        mat=mats["gold_brass"],
        col=col,
        parent=root,
    )

    tiers = [
        (1.38, 0.42, 24, 0.24),
        (0.96, 0.16, 18, 0.22),
        (0.54, -0.08, 12, 0.18),
    ]
    mesh_crystals = bpy.data.meshes.new("Chandelier_Crystals_Mesh")
    bm_c = bmesh.new()

    for t_idx, (radius, z_h, count, drop_h) in enumerate(tiers):
        # Brass ring
        ring_prof = [
            (radius - 0.035, z_h - 0.03),
            (radius + 0.035, z_h - 0.03),
            (radius + 0.040, z_h + 0.03),
            (radius - 0.035, z_h + 0.03),
            (radius - 0.035, z_h - 0.03),
        ]
        make_lathe(f"Chandelier_Ring_{t_idx}", ring_prof, segments=40, mat=mats["gold_brass"], col=col, parent=root)

        # Glowing crystal pendants around ring
        for k in range(count):
            ang = 2.0 * math.pi * k / count
            cx = math.cos(ang) * radius
            cy = math.sin(ang) * radius
            g = bmesh.ops.create_icosphere(bm_c, subdivisions=1, radius=1.0)
            bmesh.ops.scale(bm_c, vec=(0.028, 0.028, drop_h * 0.55), verts=g["verts"])
            bmesh.ops.translate(bm_c, vec=(cx, cy, z_h - drop_h * 0.45), verts=g["verts"])

    # Bottom glowing crystal finial sphere
    g_bot = bmesh.ops.create_icosphere(bm_c, subdivisions=2, radius=0.14)
    bmesh.ops.translate(bm_c, vec=(0.0, 0.0, -0.26), verts=g_bot["verts"])

    for f in bm_c.faces:
        f.smooth = True
    bm_c.to_mesh(mesh_crystals)
    bm_c.free()

    cryst_obj = bpy.data.objects.new("Chandelier_CrystalPendants", mesh_crystals)
    cryst_obj.data.materials.append(mats["crystal_glow"])
    cryst_obj.parent = root
    col.objects.link(cryst_obj)
    return root


def build_wall_assembly(
    wall_tag: str,
    length: float,
    height: float,
    loc,
    yaw_deg: float,
    mats: dict,
    col,
    has_double_door: bool = False,
):
    """
    Constructs one complete interior wall assembly parented under `Arch_Wall_<tag>`
    so interactive 3D viewers can toggle/fade outer walls cleanly by parent group.
    Front of wall faces local -Y.
    """
    root = bpy.data.objects.new(f"Arch_Wall_{wall_tag}", None)
    root.location = loc
    root.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
    col.objects.link(root)

    # Structural wall backing with silk brocade inner surface
    make_box(
        f"Wall_{wall_tag}_SilkUpper",
        (length, 0.16, height - 1.12),
        (0.0, 0.08, 1.12 + (height - 1.12) * 0.5),
        bevel=0.005,
        mat=mats["wall_silk"],
        col=col,
        parent=root,
    )
    # Dark rosewood lower wainscoting (护墙板) + brass trim rail
    make_box(
        f"Wall_{wall_tag}_Wainscot",
        (length, 0.20, 1.12),
        (0.0, 0.06, 0.56),
        bevel=0.008,
        mat=mats["rosewood"],
        col=col,
        parent=root,
    )
    make_box(
        f"Wall_{wall_tag}_BrassRail",
        (length, 0.22, 0.032),
        (0.0, 0.05, 1.135),
        bevel=0.005,
        mat=mats["gold_brass"],
        col=col,
        parent=root,
    )
    # Upper crown cornice molding
    make_box(
        f"Wall_{wall_tag}_Cornice",
        (length, 0.28, 0.24),
        (0.0, 0.02, height - 0.12),
        bevel=0.015,
        mat=mats["plaster_cream"],
        col=col,
        parent=root,
    )
    make_box(
        f"Wall_{wall_tag}_CorniceGold",
        (length, 0.29, 0.028),
        (0.0, 0.015, height - 0.245),
        bevel=0.004,
        mat=mats["gold_brass"],
        col=col,
        parent=root,
    )

    # Classical pilasters dividing wall into elegant bays
    n_bays = 4 if length > 12.0 else 3
    for i in range(n_bays + 1):
        px = -length * 0.5 + (length * i / n_bays)
        make_box(
            f"Wall_{wall_tag}_Pilaster_{i}",
            (0.34, 0.12, height - 1.38),
            (px, -0.02, 1.15 + (height - 1.38) * 0.5),
            bevel=0.012,
            mat=mats["plaster_cream"],
            col=col,
            parent=root,
        )
        make_box(
            f"Wall_{wall_tag}_Capital_{i}",
            (0.42, 0.16, 0.12),
            (px, -0.03, height - 0.30),
            bevel=0.012,
            mat=mats["gold_brass"],
            col=col,
            parent=root,
        )

    # Wainscoting decorative recessed panels
    n_wpanels = int(length // 1.4)
    for i in range(n_wpanels):
        wx = -length * 0.5 + (i + 0.5) * (length / n_wpanels)
        if has_double_door and abs(wx - 0.8) < 1.35:
            continue
        make_box(
            f"Wall_{wall_tag}_WPanel_{i}",
            (0.95, 0.03, 0.68),
            (wx, -0.045, 0.56),
            bevel=0.008,
            mat=mats["rosewood"],
            col=col,
            parent=root,
        )

    # Grand carved rosewood double doors on East/West walls
    if has_double_door:
        door_x = 0.85
        door_w = 2.10
        door_h = 3.25
        # Heavy rosewood door casing & lintel
        make_box(
            f"Wall_{wall_tag}_DoorFrame",
            (door_w + 0.28, 0.18, door_h + 0.16),
            (door_x, -0.03, (door_h + 0.16) * 0.5),
            bevel=0.012,
            mat=mats["rosewood"],
            col=col,
            parent=root,
        )
        for leaf_idx, dx in enumerate((-door_w * 0.245, door_w * 0.245)):
            make_box(
                f"Wall_{wall_tag}_DoorLeaf_{leaf_idx}",
                (door_w * 0.48, 0.08, door_h - 0.04),
                (door_x + dx, -0.09, (door_h - 0.04) * 0.5),
                bevel=0.01,
                mat=mats["rosewood"],
                col=col,
                parent=root,
            )
            # Brass kickplate & tall vertical pull handle
            make_box(
                f"Wall_{wall_tag}_Kickplate_{leaf_idx}",
                (door_w * 0.45, 0.012, 0.20),
                (door_x + dx, -0.135, 0.11),
                bevel=0.002,
                mat=mats["gold_brass"],
                col=col,
                parent=root,
            )
            hx = door_x + (0.09 if leaf_idx == 1 else -0.09)
            make_box(
                f"Wall_{wall_tag}_Handle_{leaf_idx}",
                (0.032, 0.055, 0.46),
                (hx, -0.155, 1.18),
                bevel=0.008,
                mat=mats["gold_brass"],
                col=col,
                parent=root,
            )

    return root


def build_south_entry_portal_and_corridor(hall_w: float, hall_d: float, hall_h: float, mats: dict, col):
    """
    Builds the South Wall with a real 2.16m x 3.28m central doorway cutout,
    two hinged carved rosewood double-door leaves (`EntryDoor_Hinge_L` & `EntryDoor_Hinge_R`)
    that swing open in real time, and an atmospheric outer reception corridor (`y = -5.84 .. -10.5m`)
    where the player begins before stepping into the hall.
    """
    y_wall = -hall_d * 0.5  # -5.80m
    root = bpy.data.objects.new("Arch_Wall_South_Portal", None)
    col.objects.link(root)

    door_w = 2.16
    door_h = 3.28
    half_door = door_w * 0.5  # 1.08m
    wing_w = hall_w * 0.5 - half_door  # 5.72m

    # 1. Left & Right South Wall Wings flanking the open central doorway
    for side_tag, cx in (("L", -(half_door + wing_w * 0.5)), ("R", half_door + wing_w * 0.5)):
        make_box(
            f"Wall_South_SilkUpper_{side_tag}",
            (wing_w, 0.18, hall_h - 1.12),
            (cx, y_wall - 0.07, 1.12 + (hall_h - 1.12) * 0.5),
            bevel=0.005,
            mat=mats["wall_silk"],
            col=col,
            parent=root,
        )
        make_box(
            f"Wall_South_Wainscot_{side_tag}",
            (wing_w, 0.22, 1.12),
            (cx, y_wall - 0.06, 0.56),
            bevel=0.008,
            mat=mats["rosewood"],
            col=col,
            parent=root,
        )
        make_box(
            f"Wall_South_BrassRail_{side_tag}",
            (wing_w, 0.24, 0.032),
            (cx, y_wall - 0.05, 1.135),
            bevel=0.005,
            mat=mats["gold_brass"],
            col=col,
            parent=root,
        )

    # Upper transom wall above the 3.28m doorway + full-width South cornice
    transom_h = hall_h - door_h
    make_box(
        "Wall_South_Transom",
        (door_w + 0.04, 0.18, transom_h),
        (0.0, y_wall - 0.07, door_h + transom_h * 0.5),
        bevel=0.005,
        mat=mats["wall_silk"],
        col=col,
        parent=root,
    )
    make_box(
        "Wall_South_Cornice",
        (hall_w, 0.28, 0.24),
        (0.0, y_wall + 0.02, hall_h - 0.12),
        bevel=0.015,
        mat=mats["plaster_cream"],
        col=col,
        parent=root,
    )
    make_box(
        "Wall_South_CorniceGold",
        (hall_w, 0.29, 0.028),
        (0.0, y_wall + 0.025, hall_h - 0.245),
        bevel=0.004,
        mat=mats["gold_brass"],
        col=col,
        parent=root,
    )

    # Classical pilasters on South interior wall (skipping 0.0 doorway center)
    for idx, px in enumerate((-hall_w * 0.5, -hall_w * 0.25, hall_w * 0.25, hall_w * 0.5)):
        make_box(
            f"Wall_South_Pilaster_{idx}",
            (0.34, 0.12, hall_h - 1.38),
            (px, y_wall + 0.02, 1.15 + (hall_h - 1.38) * 0.5),
            bevel=0.012,
            mat=mats["plaster_cream"],
            col=col,
            parent=root,
        )
        make_box(
            f"Wall_South_Capital_{idx}",
            (0.42, 0.16, 0.12),
            (px, y_wall + 0.03, hall_h - 0.30),
            bevel=0.012,
            mat=mats["gold_brass"],
            col=col,
            parent=root,
        )

    # 2. Carved Rosewood Door Frame Jambs, Lintel & Brass Threshold
    for side_tag, jx in (("L", -(half_door + 0.07)), ("R", half_door + 0.07)):
        make_box(
            f"EntryDoor_Jamb_{side_tag}",
            (0.16, 0.32, door_h + 0.12),
            (jx, y_wall - 0.06, (door_h + 0.12) * 0.5),
            bevel=0.012,
            mat=mats["rosewood"],
            col=col,
            parent=root,
        )
    make_box(
        "EntryDoor_Lintel",
        (door_w + 0.36, 0.34, 0.18),
        (0.0, y_wall - 0.06, door_h + 0.09),
        bevel=0.014,
        mat=mats["rosewood"],
        col=col,
        parent=root,
    )
    make_box(
        "EntryDoor_BrassThreshold",
        (door_w, 0.26, 0.010),
        (0.0, y_wall - 0.05, 0.005),
        bevel=0.002,
        mat=mats["gold_brass"],
        col=col,
        parent=root,
    )

    # 3. Articulated Left & Right Hinged Rosewood Double-Door Leaves
    leaf_w = 1.055
    leaf_h = 3.24
    for side_tag, hinge_x, dir_sign in (("L", -1.06, 1.0), ("R", 1.06, -1.0)):
        hinge = bpy.data.objects.new(f"EntryDoor_Hinge_{side_tag}", None)
        hinge.location = (hinge_x, y_wall - 0.04, 0.0)
        hinge.rotation_mode = "XYZ"
        hinge.parent = root
        col.objects.link(hinge)

        lx_mid = dir_sign * (leaf_w * 0.5)
        make_box(
            f"EntryDoor_Leaf_{side_tag}",
            (leaf_w, 0.078, leaf_h),
            (lx_mid, 0.0, leaf_h * 0.5 + 0.015),
            bevel=0.010,
            mat=mats["rosewood"],
            col=col,
            parent=hinge,
        )
        # Decorative recessed rosewood moldings + brass kickplates & handles on BOTH faces!
        for face_idx, fy in enumerate((-0.044, 0.044)):
            make_box(
                f"EntryDoor_UpperMold_{side_tag}_{face_idx}",
                (leaf_w * 0.72, 0.014, 1.45),
                (lx_mid, fy, 2.15),
                bevel=0.005,
                mat=mats["rosewood"],
                col=col,
                parent=hinge,
            )
            make_box(
                f"EntryDoor_LowerMold_{side_tag}_{face_idx}",
                (leaf_w * 0.72, 0.014, 0.72),
                (lx_mid, fy, 0.74),
                bevel=0.005,
                mat=mats["rosewood"],
                col=col,
                parent=hinge,
            )
            make_box(
                f"EntryDoor_Kickplate_{side_tag}_{face_idx}",
                (leaf_w * 0.92, 0.010, 0.20),
                (lx_mid, fy, 0.115),
                bevel=0.002,
                mat=mats["gold_brass"],
                col=col,
                parent=hinge,
            )
            hx = dir_sign * (leaf_w - 0.13)
            make_box(
                f"EntryDoor_Handle_{side_tag}_{face_idx}",
                (0.032, 0.055, 0.48),
                (hx, fy * 1.45, 1.18),
                bevel=0.008,
                mat=mats["gold_brass"],
                col=col,
                parent=hinge,
            )

    # 4. Outer Reception Corridor / Anteroom (y = -5.84 .. -10.50m)
    corr_w = 4.80
    corr_len = 4.70
    corr_h = 4.35
    corr_y_mid = y_wall - 0.12 - corr_len * 0.5  # ~ -8.27m

    make_box("Corridor_Floor", (corr_w + 0.4, corr_len + 0.3, 0.06), (0.0, corr_y_mid, -0.03), bevel=0.004, mat=mats["stone_cream"], col=col, parent=root)
    make_box("Corridor_RunnerCarpet", (1.92, corr_len - 0.15, 0.012), (0.0, corr_y_mid + 0.05, 0.008), bevel=0.004, mat=mats["carpet"], col=col, parent=root, uv_mode="top_planar")
    make_box("Corridor_Ceiling", (corr_w + 0.4, corr_len + 0.3, 0.14), (0.0, corr_y_mid, corr_h + 0.07), bevel=0.005, mat=mats["ceiling_white"], col=col, parent=root)
    make_box("Corridor_BackWall", (corr_w + 0.4, 0.18, corr_h), (0.0, corr_y_mid - corr_len * 0.5, corr_h * 0.5), bevel=0.005, mat=mats["wall_silk"], col=col, parent=root)

    for side_tag, wx, s_sign in (("L", -corr_w * 0.5, 1.0), ("R", corr_w * 0.5, -1.0)):
        make_box(f"Corridor_WallSilk_{side_tag}", (0.18, corr_len + 0.2, corr_h - 1.12), (wx, corr_y_mid, 1.12 + (corr_h - 1.12) * 0.5), bevel=0.005, mat=mats["wall_silk"], col=col, parent=root)
        make_box(f"Corridor_Wainscot_{side_tag}", (0.22, corr_len + 0.2, 1.12), (wx, corr_y_mid, 0.56), bevel=0.008, mat=mats["rosewood"], col=col, parent=root)
        make_box(f"Corridor_BrassRail_{side_tag}", (0.24, corr_len + 0.2, 0.030), (wx, corr_y_mid, 1.135), bevel=0.004, mat=mats["gold_brass"], col=col, parent=root)

        # Warm glowing classical brass wall sconce on each side of the corridor
        sx_in = wx + s_sign * 0.12
        make_box(f"Corridor_SconcePlate_{side_tag}", (0.03, 0.16, 0.34), (sx_in, -7.45, 2.15), bevel=0.006, mat=mats["gold_brass"], col=col, parent=root)
        make_box(f"Corridor_SconceShade_{side_tag}", (0.12, 0.14, 0.24), (sx_in + s_sign * 0.08, -7.45, 2.22), bevel=0.04, segs=3, mat=mats["crystal_glow"], col=col, parent=root)

    return root


def build_architecture_and_furniture(mats: dict):
    col_arch = get_or_create_collection("01_Architecture")
    col_furn = get_or_create_collection("02_Furniture_Props")

    hall_w = 13.6
    hall_d = 11.6
    hall_h = 5.6

    # 1. Stone floor, dark marble inlay border, and iconic Great Hall crimson carpet
    make_box("Arch_Floor_Travertine", (hall_w + 0.4, hall_d + 0.4, 0.06), (0.0, 0.0, -0.03), bevel=0.004, mat=mats["stone_cream"], col=col_arch)
    # Dark marble decorative border strips (clear of floor z=0.000)
    border_w, border_d = 11.5, 9.5
    for sy in (-border_d * 0.5, border_d * 0.5):
        make_box(f"Arch_MarbleInlay_Y_{sy:.1f}", (border_w + 0.36, 0.24, 0.005), (0.0, sy, 0.004), bevel=0.001, mat=mats["stone_dark"], col=col_arch)
    for sx in (-border_w * 0.5, border_w * 0.5):
        make_box(f"Arch_MarbleInlay_X_{sx:.1f}", (0.24, border_d + 0.36, 0.005), (sx, 0.0, 0.004), bevel=0.001, mat=mats["stone_dark"], col=col_arch)

    # Crimson Wool Reception Carpet (10.8m x 8.8m)
    make_box(
        "Arch_Reception_Carpet",
        (10.8, 8.8, 0.012),
        (0.0, 0.15, 0.010),
        bevel=0.005,
        segs=2,
        mat=mats["carpet"],
        col=col_arch,
        uv_mode="top_planar",
    )

    # 2. Four perimeter walls (North=+Y behind VIPs, South=-Y entry portal + outer corridor, East=+X, West=-X)
    build_wall_assembly("North", hall_w, hall_h, (0.0, hall_d * 0.5, 0.0), 0.0, mats, col_arch, has_double_door=False)
    build_south_entry_portal_and_corridor(hall_w, hall_d, hall_h, mats, col_arch)
    build_wall_assembly("East", hall_d, hall_h, (hall_w * 0.5, 0.0, 0.0), -90.0, mats, col_arch, has_double_door=True)
    build_wall_assembly("West", hall_d, hall_h, (-hall_w * 0.5, 0.0, 0.0), 90.0, mats, col_arch, has_double_door=True)

    # 3. Coffered Ceiling Assembly (grouped under Arch_Ceiling for clean cutaway in interactive 3D!)
    ceil_root = bpy.data.objects.new("Arch_Ceiling", None)
    ceil_root.location = (0.0, 0.0, hall_h)
    col_arch.objects.link(ceil_root)

    # Recessed upper coffer deck
    make_box("Ceiling_UpperDeck", (hall_w + 0.3, hall_d + 0.3, 0.10), (0.0, 0.0, 0.32), bevel=0.005, mat=mats["ceiling_white"], col=col_arch, parent=ceil_root)
    # Perimeter lower soffits creating central coffer (9.4m x 7.6m)
    coffer_w, coffer_d = 9.4, 7.6
    soffit_x = (hall_w - coffer_w) * 0.5
    soffit_y = (hall_d - coffer_d) * 0.5
    for sy in (-(hall_d - soffit_y) * 0.5, (hall_d - soffit_y) * 0.5):
        make_box(f"Ceiling_Soffit_Y_{sy:.1f}", (hall_w, soffit_y, 0.28), (0.0, sy, 0.14), bevel=0.01, mat=mats["plaster_cream"], col=col_arch, parent=ceil_root)
    for sx in (-(hall_w - soffit_x) * 0.5, (hall_w - soffit_x) * 0.5):
        make_box(f"Ceiling_Soffit_X_{sx:.1f}", (soffit_x, coffer_d, 0.28), (sx, 0.0, 0.14), bevel=0.01, mat=mats["plaster_cream"], col=col_arch, parent=ceil_root)

    # Glowing indirect ceiling cove light strips
    for sy in (-coffer_d * 0.5, coffer_d * 0.5):
        make_box(f"Ceiling_CoveGlow_Y_{sy:.1f}", (coffer_w, 0.08, 0.06), (0.0, sy, 0.24), bevel=0.005, mat=mats["cove_glow"], col=col_arch, parent=ceil_root)
    for sx in (-coffer_w * 0.5, coffer_w * 0.5):
        make_box(f"Ceiling_CoveGlow_X_{sx:.1f}", (0.08, coffer_d, 0.06), (sx, 0.0, 0.24), bevel=0.005, mat=mats["cove_glow"], col=col_arch, parent=ceil_root)

    # 12 Recessed downlights in soffit
    downlight_pts = [
        (-5.6, -3.6), (-2.8, -4.8), (0.0, -4.8), (2.8, -4.8), (5.6, -3.6),
        (-5.6, 3.6), (-2.8, 4.8), (0.0, 4.8), (2.8, 4.8), (5.6, 3.6),
        (-5.6, 0.0), (5.6, 0.0),
    ]
    for idx, (dx, dy) in enumerate(downlight_pts):
        make_lathe(
            f"Ceiling_Downlight_Rim_{idx}",
            [(0.08, -0.01), (0.12, -0.01), (0.12, 0.02), (0.08, 0.02)],
            segments=20,
            loc=(dx, dy, 0.0),
            mat=mats["gold_brass"],
            col=col_arch,
            parent=ceil_root,
        )
        make_lathe(
            f"Ceiling_Downlight_Bulb_{idx}",
            [(0.0, 0.005), (0.08, 0.005), (0.08, 0.02), (0.0, 0.02)],
            segments=20,
            loc=(dx, dy, 0.0),
            mat=mats["crystal_glow"],
            col=col_arch,
            parent=ceil_root,
        )

    # Grand Chandelier (hung lower into hall volume so crystal rings gleam in wide shots)
    chandelier = build_crystal_chandelier((0.0, 0.35, -1.42), mats, col_arch)
    chandelier.parent = ceil_root

    # 4. Grand 7-Panel Carved Rosewood & Landscape Folding Screen + Vases + Palms
    build_seven_panel_screen((0.0, 4.35, 0.0), mats, col_arch)
    build_floor_vase("Furn_PorcelainVase_Left", (-3.25, 4.15, 0.0), mats, col_furn)
    build_floor_vase("Furn_PorcelainVase_Right", (3.25, 4.15, 0.0), mats, col_furn)

    build_potted_palm("Furn_Palm_InnerLeft", (-2.15, 3.72, 0.0), mats, col_furn, scale=1.06)
    build_potted_palm("Furn_Palm_InnerRight", (2.15, 3.72, 0.0), mats, col_furn, scale=1.06)
    build_potted_palm("Furn_Palm_OuterLeft", (-4.55, 3.95, 0.0), mats, col_furn, scale=1.15)
    build_potted_palm("Furn_Palm_OuterRight", (4.55, 3.95, 0.0), mats, col_furn, scale=1.15)

    # 5. Diplomatic Armchairs & Rosewood Tea Tables
    #    Main VIP pair in front of the 7-panel screen + spacious perimeter seating all facing INWARD!
    #    Note: local -Y is chair front -> +yaw turns front toward +X (East), -yaw turns front toward -X (West).
    build_diplomatic_armchair("Furn_Armchair_VIP_Left", (-0.86, 2.90, 0.0), 7.0, mats, col_furn)
    build_diplomatic_armchair("Furn_Armchair_VIP_Right", (0.86, 2.90, 0.0), -7.0, mats, col_furn)

    # Center Rosewood Tea Table + Floral Centerpiece + 2 Lidded Porcelain Teacups
    build_tea_table("Furn_TeaTable_CenterVIP", (0.0, 2.96, 0.0), 0.0, mats, col_furn, center_floral=True)
    build_teacup_set("Prop_Teacup_VIP_Left", (-0.17, 2.79, 0.567), mats, col_furn, lid_ajar=True)
    build_teacup_set("Prop_Teacup_VIP_Right", (0.17, 2.79, 0.567), mats, col_furn, lid_ajar=False)

    # West Perimeter Armchairs & Side Tables (Backrests near West carpet border, seats facing EAST +X inward!)
    west_chairs = [
        ("Furn_Armchair_L1", (-4.70, 2.45, 0.0), 74.0),
        ("Furn_Armchair_L2", (-4.82, 0.80, 0.0), 88.0),
        ("Furn_Armchair_L3", (-4.82, -2.35, 0.0), 108.0),
        ("Furn_Armchair_S1", (-2.85, -3.55, 0.0), 158.0),
    ]
    for cname, cloc, cyaw in west_chairs:
        build_diplomatic_armchair(cname, cloc, cyaw, mats, col_furn)

    build_tea_table("Furn_TeaTable_L1", (-4.78, 1.62, 0.0), 82.0, mats, col_furn)
    build_teacup_set("Prop_Teacup_L1", (-4.78, 1.62, 0.567), mats, col_furn)
    build_tea_table("Furn_TeaTable_L2", (-4.75, -3.18, 0.0), 115.0, mats, col_furn)
    build_teacup_set("Prop_Teacup_L2", (-4.75, -3.18, 0.567), mats, col_furn)

    # East Perimeter Armchairs & Side Tables (Backrests near East carpet border, seats facing WEST -X inward!)
    east_chairs = [
        ("Furn_Armchair_R1", (4.70, 2.45, 0.0), -74.0),
        ("Furn_Armchair_R2", (4.82, 0.80, 0.0), -88.0),
        ("Furn_Armchair_R3", (4.82, -2.35, 0.0), -108.0),
        ("Furn_Armchair_S2", (2.85, -3.55, 0.0), -158.0),
    ]
    for cname, cloc, cyaw in east_chairs:
        build_diplomatic_armchair(cname, cloc, cyaw, mats, col_furn)

    build_tea_table("Furn_TeaTable_R1", (4.78, 1.62, 0.0), -82.0, mats, col_furn)
    build_teacup_set("Prop_Teacup_R1", (4.78, 1.62, 0.567), mats, col_furn)
    build_tea_table("Furn_TeaTable_R2", (4.75, -3.18, 0.0), -115.0, mats, col_furn)
    build_teacup_set("Prop_Teacup_R2", (4.75, -3.18, 0.567), mats, col_furn)
