"""
Articulated hierarchical 3D character rigs & 32-second seamless looping
choreography recreating the physical body language and press dynamics of the
October 27, 2000 reception hall scene (zero text anywhere).
"""

import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
from arch_furniture import get_or_create_collection, make_box, make_lathe
from characters_press import make_lofted_segment, make_sphere

FPS = 24
LOOP_SECONDS = 32.0
TOTAL_FRAMES = int(FPS * LOOP_SECONDS)  # 768 frames (frames 0..768 where 768 == 0)


def clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)


def smooth01(x: float) -> float:
    u = clamp01(x)
    return u * u * (3.0 - 2.0 * u)


def smoother01(x: float) -> float:
    u = clamp01(x)
    return u * u * u * (u * (u * 6.0 - 15.0) + 10.0)


def seg_alpha(t: float, t0: float, t1: float) -> float:
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return smoother01((t - t0) / max(t1 - t0, 1e-5))


def window_env(t: float, t_start: float, t_end: float, fade: float = 0.55) -> float:
    """Smooth raised window [0 -> 1 -> 0] over [t_start, t_end]."""
    return smooth01((t - t_start) / max(fade, 1e-4)) * (1.0 - smooth01((t - (t_end - fade)) / max(fade, 1e-4)))


def new_pivot(name: str, loc=(0.0, 0.0, 0.0), rot_deg=(0.0, 0.0, 0.0), parent=None, col=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.05
    obj.rotation_mode = "XYZ"
    obj.location = loc
    obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
    if parent:
        obj.parent = parent
    if col:
        col.objects.link(obj)
    return obj


def build_articulated_hand(prefix: str, is_right: bool, skin_mat, col, wrist_pivot):
    """
    Hand hanging along local -Z from wrist_pivot.
    Local -Y is thumb/forward edge, +Y is pinky/back edge.
    Inner palm faces +X for Right hand (on -X body side), -X for Left hand (+X body side).
    Returns dict with `index` and `curl` finger pivots for dynamic pointing vs open palm!
    """
    palm_in_sign = 1.0 if is_right else -1.0

    # Palm body: thin in X (thickness), wide in Y (across knuckles), hanging down -Z
    make_box(
        prefix + "_Palm",
        (0.026, 0.076, 0.078),
        (0.0, 0.0, -0.038),
        bevel=0.009,
        mat=skin_mat,
        col=col,
        parent=wrist_pivot,
    )

    # Thumb angled forward (-Y)
    thumb_piv = new_pivot(prefix + "_ThumbPiv", (palm_in_sign * 0.004, -0.034, -0.025), (-28.0, 0.0, 0.0), wrist_pivot, col)
    make_lofted_segment(
        prefix + "_ThumbMesh",
        Vector((0.0, 0.0, 0.0)),
        Vector((palm_in_sign * 0.008, -0.016, -0.048)),
        r0_xy=(0.010, 0.010),
        r1_xy=(0.0075, 0.0075),
        rings=3,
        sides=10,
        mat=skin_mat,
        col=col,
        parent=thumb_piv,
    )

    # Index finger pivot (stays straight during pointing!)
    index_piv = new_pivot(prefix + "_IndexPiv", (0.0, -0.025, -0.074), (0.0, 0.0, 0.0), wrist_pivot, col)
    make_lofted_segment(
        prefix + "_IndexMesh",
        Vector((0.0, 0.0, 0.0)),
        Vector((0.0, -0.003, -0.074)),
        r0_xy=(0.009, 0.009),
        r1_xy=(0.0065, 0.0065),
        rings=4,
        sides=10,
        mat=skin_mat,
        col=col,
        parent=index_piv,
    )

    # Middle + Ring + Pinky 2-joint group (curls tightly into palm when pointing or gripping!)
    curl_piv = new_pivot(prefix + "_CurlPiv", (0.0, 0.012, -0.072), (0.0, 0.0, 0.0), wrist_pivot, col)
    curl_tip_piv = new_pivot(prefix + "_CurlTipPiv", (0.0, 0.0, -0.036), (0.0, 0.0, 0.0), curl_piv, col)
    for idx, fy_off, flen in ((0, -0.015, 0.036), (1, 0.002, 0.034), (2, 0.018, 0.030)):
        make_lofted_segment(
            f"{prefix}_FingerProx_{idx}",
            Vector((0.0, fy_off, 0.0)),
            Vector((0.0, fy_off, -flen)),
            r0_xy=(0.0085, 0.0085),
            r1_xy=(0.0075, 0.0075),
            rings=2,
            sides=10,
            mat=skin_mat,
            col=col,
            parent=curl_piv,
        )
        make_lofted_segment(
            f"{prefix}_FingerDist_{idx}",
            Vector((0.0, fy_off, 0.0)),
            Vector((0.0, fy_off, -flen * 0.92)),
            r0_xy=(0.0075, 0.0075),
            r1_xy=(0.0060, 0.0060),
            rings=2,
            sides=10,
            mat=skin_mat,
            col=col,
            parent=curl_tip_piv,
        )

    return {"thumb": thumb_piv, "index": index_piv, "curl": curl_piv, "curl_tip": curl_tip_piv, "is_right": is_right}


def build_rigged_head(
    prefix: str,
    neck_pivot,
    hair_style: str,
    has_thick_glasses: bool,
    skin_mat,
    hair_mat,
    mats: dict,
    col,
):
    """Sculpted head with articulated jaw/lower-lip pivot for natural speech animation."""
    head_piv = new_pivot(prefix + "_Head", (0.0, -0.008, 0.095), (0.0, 0.0, 0.0), neck_pivot, col)

    # Neck cylinder attached to neck_pivot
    make_lofted_segment(
        prefix + "_NeckMesh",
        Vector((0.0, 0.0, -0.015)),
        Vector((0.0, -0.006, 0.085)),
        r0_xy=(0.056, 0.056),
        r1_xy=(0.051, 0.051),
        rings=3,
        mat=skin_mat,
        col=col,
        parent=neck_pivot,
    )

    # Sculpted cranium mesh
    mesh = bpy.data.meshes.new(prefix + "_CraniumMesh")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        rx, ry, rz = 0.088, 0.104, 0.116
        if z < 0.0:
            jaw_taper = 1.0 - 0.24 * abs(z)
            rx *= jaw_taper
            ry *= (1.0 - 0.10 * abs(z))
        if 0.05 < z < 0.35 and y < -0.5:
            ry *= 1.04
        v.co = Vector((x * rx, y * ry, z * rz))
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()

    head_obj = bpy.data.objects.new(prefix + "_HeadMesh", mesh)
    head_obj.data.materials.append(skin_mat)
    head_obj.parent = head_piv
    col.objects.link(head_obj)

    # Nose & Ears
    make_lofted_segment(
        prefix + "_Nose",
        Vector((0.0, -0.094, 0.024)),
        Vector((0.0, -0.114, -0.014)),
        r0_xy=(0.011, 0.010),
        r1_xy=(0.014, 0.012),
        rings=4,
        sides=12,
        mat=skin_mat,
        col=col,
        parent=head_piv,
    )
    for side, sx in (("L", 0.088), ("R", -0.088)):
        make_sphere(f"{prefix}_Ear_{side}", (sx, 0.005, 0.0), radii=(0.012, 0.020, 0.030), subs=2, mat=skin_mat, col=col, parent=head_piv)

    # Eyes & Eyebrows
    for side, sx in (("L", 0.032), ("R", -0.032)):
        make_sphere(f"{prefix}_EyeWhite_{side}", (sx, -0.094, 0.018), radii=(0.011, 0.006, 0.008), subs=2, mat=mats["shirt_white"], col=col, parent=head_piv)
        make_sphere(f"{prefix}_EyePupil_{side}", (sx, -0.099, 0.018), radii=(0.0055, 0.004, 0.0055), subs=2, mat=mats["glasses_frame"], col=col, parent=head_piv)
        make_box(
            f"{prefix}_Brow_{side}",
            (0.028, 0.009, 0.007),
            (sx, -0.099, 0.036),
            rot_deg=(0.0, 6.0 if side == "L" else -6.0, 0.0),
            bevel=0.0025,
            mat=hair_mat,
            col=col,
            parent=head_piv,
        )

    # Upper lip + dark oral cavity + Articulated Lower Lip / Jaw Pivot!
    make_box(f"{prefix}_LipTop", (0.038, 0.011, 0.007), (0.0, -0.096, -0.040), bevel=0.003, mat=mats["lips_warm"], col=col, parent=head_piv)
    make_box(f"{prefix}_OralCavity", (0.030, 0.008, 0.011), (0.0, -0.093, -0.045), bevel=0.002, mat=mats["suit_black"], col=col, parent=head_piv)
    jaw_piv = new_pivot(prefix + "_Jaw", (0.0, -0.072, -0.044), (0.0, 0.0, 0.0), head_piv, col)
    make_box(f"{prefix}_LipBot", (0.036, 0.011, 0.0075), (0.0, -0.024, -0.003), bevel=0.003, mat=mats["lips_warm"], col=col, parent=jaw_piv)

    # Hairstyles
    if hair_style == "combed_back_high":
        make_sphere(prefix + "_HairCrown", (0.0, 0.020, 0.032), radii=(0.093, 0.098, 0.098), rot_deg=(-18.0, 0.0, 0.0), subs=3, mat=hair_mat, col=col, parent=head_piv)
        for side, sx in (("L", 0.076), ("R", -0.076)):
            make_sphere(f"{prefix}_HairTemple_{side}", (sx, -0.005, 0.025), radii=(0.022, 0.058, 0.052), subs=2, mat=hair_mat, col=col, parent=head_piv)
    elif hair_style == "silver_flattop":
        make_sphere(prefix + "_HairBack", (0.0, 0.018, 0.026), radii=(0.092, 0.096, 0.094), subs=3, mat=hair_mat, col=col, parent=head_piv)
        make_box(prefix + "_HairFlatTop", (0.145, 0.165, 0.048), (0.0, 0.005, 0.105), bevel=0.020, segs=3, mat=hair_mat, col=col, parent=head_piv)
    elif hair_style == "female_bob":
        make_sphere(prefix + "_HairTop", (0.0, 0.006, 0.032), radii=(0.097, 0.108, 0.102), subs=3, mat=hair_mat, col=col, parent=head_piv)
        for side, sx in (("L", 0.078), ("R", -0.078)):
            make_lofted_segment(
                f"{prefix}_HairSide_{side}",
                Vector((sx, -0.018, 0.055)),
                Vector((sx * 1.05, -0.010, -0.118)),
                r0_xy=(0.026, 0.068),
                r1_xy=(0.018, 0.058),
                rings=5,
                sides=14,
                mat=hair_mat,
                col=col,
                parent=head_piv,
            )
        make_lofted_segment(
            prefix + "_HairBackDrape",
            Vector((0.0, 0.058, 0.055)),
            Vector((0.0, 0.068, -0.125)),
            r0_xy=(0.088, 0.045),
            r1_xy=(0.082, 0.035),
            rings=5,
            sides=16,
            mat=hair_mat,
            col=col,
            parent=head_piv,
        )
    else:
        make_sphere(prefix + "_HairStd", (0.0, 0.010, 0.032), radii=(0.094, 0.104, 0.098), rot_deg=(-8.0, 0.0, 0.0), subs=3, mat=hair_mat, col=col, parent=head_piv)

    # Thick black square-framed glasses
    if has_thick_glasses:
        g_y, g_z = -0.107, 0.018
        rim_w, rim_h, thick = 0.056, 0.040, 0.0082
        for side, cx in (("L", 0.035), ("R", -0.035)):
            make_box(f"{prefix}_GlassTop_{side}", (rim_w, thick, thick * 1.18), (cx, g_y, g_z + rim_h * 0.5), bevel=0.0018, mat=mats["glasses_frame"], col=col, parent=head_piv)
            make_box(f"{prefix}_GlassBot_{side}", (rim_w, thick * 0.92, thick * 0.92), (cx, g_y, g_z - rim_h * 0.5), bevel=0.0018, mat=mats["glasses_frame"], col=col, parent=head_piv)
            make_box(f"{prefix}_GlassOut_{side}", (thick, thick, rim_h), (cx + (rim_w * 0.5 if side == "L" else -rim_w * 0.5), g_y, g_z), bevel=0.0018, mat=mats["glasses_frame"], col=col, parent=head_piv)
            make_box(f"{prefix}_GlassIn_{side}", (thick * 0.85, thick, rim_h), (cx + (-rim_w * 0.5 if side == "L" else rim_w * 0.5), g_y, g_z), bevel=0.0018, mat=mats["glasses_frame"], col=col, parent=head_piv)
            make_box(f"{prefix}_GlassLens_{side}", (rim_w - 0.008, 0.002, rim_h - 0.008), (cx, g_y + 0.001, g_z), bevel=0.0005, mat=mats["glasses_lens"], col=col, parent=head_piv)
            tx = 0.064 if side == "L" else -0.064
            make_box(f"{prefix}_GlassTemple_{side}", (0.006, 0.114, 0.0085), (tx * 1.35, -0.046, g_z + 0.005), rot_deg=(-4.0, 0.0, -5.0 if side == "L" else 5.0), bevel=0.001, mat=mats["glasses_frame"], col=col, parent=head_piv)
        make_box(f"{prefix}_GlassBridge", (0.020, thick, thick * 1.15), (0.0, g_y - 0.001, g_z + 0.008), bevel=0.0018, mat=mats["glasses_frame"], col=col, parent=head_piv)

    return head_piv, jaw_piv


def build_rigged_character(
    name: str,
    loc,
    yaw_deg: float,
    mats: dict,
    col,
    height_scale: float = 1.0,
    body_width: float = 1.0,
    female: bool = False,
    high_waisted: bool = False,
    open_jacket: bool = False,
    suit_mat_key: str = "suit_charcoal_navy",
    trouser_mat_key: str = None,
    shirt_mat_key: str = "shirt_white",
    tie_mat_key: str = "tie_crimson",
    hair_style: str = "parted",
    hair_mat_key: str = "hair_dark",
    has_thick_glasses: bool = False,
):
    """
    Constructs a fully rigged hierarchical character facing local -Y.
    Anatomical Right = -X, Anatomical Left = +X, Up = +Z.
    Standing Hips height = 0.92m (Thigh 0.43 + Calf 0.42 + Shoe 0.07).
    """
    suit_mat = mats[suit_mat_key]
    pants_mat = mats[trouser_mat_key or suit_mat_key]
    shirt_mat = mats[shirt_mat_key]
    skin_mat = mats["skin_fair" if female else "skin_warm"]
    hair_mat = mats[hair_mat_key]
    bw = body_width * (0.86 if female else 1.0)

    root = new_pivot(name + "_Root", loc, (0.0, 0.0, yaw_deg), None, col)
    root.scale = (height_scale, height_scale, height_scale)

    hips = new_pivot(name + "_Hips", (0.0, 0.0, 0.92), (0.0, 0.0, 0.0), root, col)

    # Pelvis & Skirt/Waistband attached to Hips
    waist_top = 0.14 if high_waisted else 0.07
    make_lofted_segment(
        f"{name}_Pelvis",
        Vector((0.0, 0.0, -0.06)),
        Vector((0.0, 0.0, waist_top)),
        r0_xy=(0.184 * bw, 0.130 * bw),
        r1_xy=(0.178 * bw, 0.126 * bw),
        rings=4,
        mat=pants_mat,
        col=col,
        parent=hips,
    )
    if female:
        make_lofted_segment(
            f"{name}_Skirt",
            Vector((0.0, 0.0, 0.05)),
            Vector((0.0, 0.0, -0.40)),
            r0_xy=(0.178 * bw, 0.128 * bw),
            r1_xy=(0.198 * bw, 0.138 * bw),
            rings=5,
            mat=pants_mat,
            col=col,
            parent=hips,
        )

    # Legs: Hip_R (-X) and Hip_L (+X)
    legs = {}
    for side, sx in (("R", -0.105 * bw), ("L", 0.105 * bw)):
        hip_piv = new_pivot(f"{name}_Hip_{side}", (sx, 0.0, 0.0), (0.0, 0.0, 0.0), hips, col)
        make_sphere(f"{name}_HipCap_{side}", (0.0, 0.0, 0.0), radii=(0.090 * bw, 0.092 * bw, 0.090 * bw), subs=2, mat=pants_mat, col=col, parent=hip_piv)
        make_lofted_segment(
            f"{name}_Thigh_{side}",
            Vector((0.0, 0.0, 0.0)),
            Vector((0.0, 0.0, -0.43)),
            r0_xy=(0.094 * bw, 0.100 * bw),
            r1_xy=(0.073 * bw, 0.077 * bw),
            rings=5,
            mat=pants_mat,
            col=col,
            parent=hip_piv,
        )

        knee_piv = new_pivot(f"{name}_Knee_{side}", (0.0, 0.0, -0.43), (0.0, 0.0, 0.0), hip_piv, col)
        calf_mat = skin_mat if female else pants_mat
        make_sphere(f"{name}_KneeCap_{side}", (0.0, 0.0, 0.0), radii=(0.071 * bw, 0.073 * bw, 0.071 * bw), subs=2, mat=calf_mat, col=col, parent=knee_piv)
        make_lofted_segment(
            f"{name}_Calf_{side}",
            Vector((0.0, 0.0, 0.0)),
            Vector((0.0, 0.0, -0.42)),
            r0_xy=((0.056 if female else 0.071 * bw), (0.060 if female else 0.076 * bw)),
            r1_xy=((0.039 if female else 0.055 * bw), (0.043 if female else 0.060 * bw)),
            rings=5,
            mat=calf_mat,
            col=col,
            parent=knee_piv,
        )

        ankle_piv = new_pivot(f"{name}_Ankle_{side}", (0.0, 0.0, -0.42), (0.0, 0.0, 0.0), knee_piv, col)
        make_box(
            f"{name}_Shoe_{side}",
            (0.092, 0.24, 0.072),
            (0.0, -0.052, -0.034),
            bevel=0.024,
            segs=2,
            mat=mats["leather_black"],
            col=col,
            parent=ankle_piv,
        )
        legs[side] = {"hip": hip_piv, "knee": knee_piv, "ankle": ankle_piv}

    # Torso pivot at Hips + (0, 0, 0.06) -> shoulder_local_z = 0.46 (world 0.92 + 0.06 + 0.46 = 1.44m)
    torso = new_pivot(name + "_Torso", (0.0, 0.0, 0.06), (0.0, 0.0, 0.0), hips, col)
    sh_z = 0.46

    if open_jacket:
        belt_z = 0.08
        make_lofted_segment(
            f"{name}_ShirtTorso",
            Vector((0.0, -0.012, 0.04)),
            Vector((0.0, -0.012, sh_z - 0.01)),
            r0_xy=(0.165 * bw, 0.112 * bw),
            r1_xy=(0.185 * bw, 0.115 * bw),
            rings=5,
            mat=shirt_mat,
            col=col,
            parent=torso,
        )
        make_lofted_segment(
            f"{name}_Belt",
            Vector((0.0, 0.0, belt_z - 0.018)),
            Vector((0.0, 0.0, belt_z + 0.022)),
            r0_xy=(0.184 * bw, 0.132 * bw),
            r1_xy=(0.184 * bw, 0.132 * bw),
            rings=2,
            mat=mats["leather_black"],
            col=col,
            parent=torso,
        )
        make_box(f"{name}_BeltBuckle", (0.048, 0.018, 0.040), (0.0, -0.135 * bw, belt_z + 0.002), bevel=0.003, mat=mats["cam_chrome"], col=col, parent=torso)

        # Open suit jacket back & front panels + lapels
        make_box(
            f"{name}_JacketBack",
            (0.42 * bw, 0.145 * bw, sh_z + 0.16),
            (0.0, 0.068 * bw, (sh_z - 0.14) * 0.5),
            bevel=0.032,
            segs=3,
            mat=suit_mat,
            col=col,
            parent=torso,
        )
        for side, sx in (("R", -0.136 * bw), ("L", 0.136 * bw)):
            make_box(
                f"{name}_JacketFront_{side}",
                (0.162 * bw, 0.165 * bw, sh_z + 0.16),
                (sx, -0.048 * bw, (sh_z - 0.14) * 0.5),
                rot_deg=(0.0, 0.0, -4.0 if side == "R" else 4.0),
                bevel=0.032,
                segs=2,
                mat=suit_mat,
                col=col,
                parent=torso,
            )
            make_box(
                f"{name}_Lapel_{side}",
                (0.056, 0.022, 0.29),
                (sx * 0.68, -0.136 * bw, sh_z - 0.14),
                rot_deg=(0.0, 15.0 if side == "R" else -15.0, 0.0),
                bevel=0.006,
                mat=suit_mat,
                col=col,
                parent=torso,
            )
    else:
        make_lofted_segment(
            f"{name}_SuitTorso",
            Vector((0.0, 0.0, -0.04)),
            Vector((0.0, 0.0, sh_z)),
            r0_xy=(0.185 * bw, 0.130 * bw),
            r1_xy=(0.215 * bw, 0.134 * bw),
            rings=6,
            mat=suit_mat,
            col=col,
            parent=torso,
        )
        make_box(
            f"{name}_ShirtV",
            (0.105, 0.018, 0.23),
            (0.0, -0.134 * bw, sh_z - 0.11),
            bevel=0.005,
            mat=shirt_mat,
            col=col,
            parent=torso,
        )

    # Shirt Collar & Full Unclipped Silk Necktie
    make_lofted_segment(
        f"{name}_Collar",
        Vector((0.0, -0.015, sh_z - 0.01)),
        Vector((0.0, -0.018, sh_z + 0.038)),
        r0_xy=(0.074, 0.074),
        r1_xy=(0.064, 0.064),
        rings=3,
        mat=shirt_mat,
        col=col,
        parent=torso,
    )
    if tie_mat_key and not female:
        tie_top_y = -(0.128 * bw if open_jacket else 0.142 * bw)
        tie_bot_y = -(0.136 * bw if open_jacket else 0.146 * bw)
        tie_bot_z = 0.10 if open_jacket else (sh_z - 0.21)
        make_box(f"{name}_TieKnot", (0.036, 0.020, 0.036), (0.0, tie_top_y, sh_z - 0.015), bevel=0.007, mat=mats[tie_mat_key], col=col, parent=torso)
        make_lofted_segment(
            f"{name}_TieBlade",
            Vector((0.0, tie_top_y - 0.004, sh_z - 0.030)),
            Vector((0.0, tie_bot_y, tie_bot_z)),
            r0_xy=(0.022, 0.007),
            r1_xy=(0.038, 0.007),
            rings=5,
            mat=mats[tie_mat_key],
            col=col,
            parent=torso,
        )

    # Neck & Head + Jaw
    neck = new_pivot(name + "_Neck", (0.0, 0.0, sh_z + 0.02), (0.0, 0.0, 0.0), torso, col)
    head_piv, jaw_piv = build_rigged_head(
        name,
        neck,
        hair_style=hair_style,
        has_thick_glasses=has_thick_glasses,
        skin_mat=skin_mat,
        hair_mat=hair_mat,
        mats=mats,
        col=col,
    )

    # Articulated Arms: Shoulder_R (-X) and Shoulder_L (+X)
    arms = {}
    for side, sx, is_r in (("R", -0.220 * bw, True), ("L", 0.220 * bw, False)):
        sh_piv = new_pivot(f"{name}_Shoulder_{side}", (sx, 0.0, sh_z - 0.045), (0.0, 0.0, 0.0), torso, col)
        make_sphere(f"{name}_ShoulderCap_{side}", (0.0, 0.0, 0.0), radii=(0.068 * bw, 0.068 * bw, 0.068 * bw), subs=2, mat=suit_mat, col=col, parent=sh_piv)
        make_lofted_segment(
            f"{name}_UpperArm_{side}",
            Vector((0.0, 0.0, 0.0)),
            Vector((0.0, 0.0, -0.27)),
            r0_xy=(0.064 * bw, 0.064 * bw),
            r1_xy=(0.053 * bw, 0.053 * bw),
            rings=4,
            mat=suit_mat,
            col=col,
            parent=sh_piv,
        )

        el_piv = new_pivot(f"{name}_Elbow_{side}", (0.0, 0.0, -0.27), (0.0, 0.0, 0.0), sh_piv, col)
        make_sphere(f"{name}_ElbowCap_{side}", (0.0, 0.0, 0.0), radii=(0.053 * bw, 0.053 * bw, 0.053 * bw), subs=2, mat=suit_mat, col=col, parent=el_piv)
        make_lofted_segment(
            f"{name}_Forearm_{side}",
            Vector((0.0, 0.0, 0.0)),
            Vector((0.0, 0.0, -0.215)),
            r0_xy=(0.052 * bw, 0.052 * bw),
            r1_xy=(0.044 * bw, 0.044 * bw),
            rings=4,
            mat=suit_mat,
            col=col,
            parent=el_piv,
        )
        make_lofted_segment(
            f"{name}_ShirtCuff_{side}",
            Vector((0.0, 0.0, -0.215)),
            Vector((0.0, 0.0, -0.245)),
            r0_xy=(0.042 * bw, 0.042 * bw),
            r1_xy=(0.040 * bw, 0.040 * bw),
            rings=2,
            mat=shirt_mat,
            col=col,
            parent=el_piv,
        )

        wr_piv = new_pivot(f"{name}_Wrist_{side}", (0.0, 0.0, -0.245), (0.0, 0.0, 0.0), el_piv, col)
        hand_parts = build_articulated_hand(f"{name}_Hand_{side}", is_r, skin_mat, col, wr_piv)
        arms[side] = {"shoulder": sh_piv, "elbow": el_piv, "wrist": wr_piv, "hand": hand_parts}

    return {
        "root": root,
        "hips": hips,
        "torso": torso,
        "neck": neck,
        "head": head_piv,
        "jaw": jaw_piv,
        "legs": legs,
        "arms": arms,
        "bw": bw,
    }


def attach_mic_to_wrist(name: str, wrist_piv, is_right: bool, quadrant_idx: int, mats: dict, col):
    """Attaches a textless broadcast microphone upright & forward inside the gripped hand."""
    palm_in_x = 0.016 if is_right else -0.016
    mic_root = new_pivot(
        name,
        loc=(palm_in_x, -0.012, -0.048),
        rot_deg=(78.0, 0.0, 0.0),  # +78 deg around X swings +Z mic tip UPWARD & FORWARD toward speaker!
        parent=wrist_piv,
        col=col,
    )
    make_lathe(
        name + "_Shaft",
        [(0.0, -0.09), (0.013, -0.09), (0.017, 0.14), (0.0, 0.14)],
        segments=18,
        mat=mats["cam_body"],
        col=col,
        parent=mic_root,
    )
    qx = quadrant_idx % 2
    qy = 1 - (quadrant_idx // 2)
    uv_r = (qx * 0.5 + 0.01, qy * 0.5 + 0.01, (qx + 1) * 0.5 - 0.01, (qy + 1) * 0.5 - 0.01)
    make_box(
        name + "_StationFlag",
        (0.068, 0.068, 0.062),
        (0.0, 0.0, 0.112),
        bevel=0.005,
        mat=mats["mic_flags"],
        col=col,
        parent=mic_root,
        uv_rect=uv_r,
    )
    make_sphere(name + "_Windscreen", (0.0, 0.0, 0.175), radii=(0.032, 0.032, 0.042), subs=2, mat=mats["mic_foam"], col=col, parent=mic_root)
    return mic_root


def build_betacam_rig(name: str, loc, mats: dict, col, on_tripod: bool = False):
    """
    Creates an animatable Betacam SP camera facing local -Y (so yaw=180 faces +Y).
    Returns pivot object that pans/tilts cleanly.
    """
    cam_pos = Vector(loc)
    if on_tripod:
        t_root = new_pivot(name + "_TripodBase", (cam_pos.x, cam_pos.y, 0.014), (0, 0, 0), None, col)
        head_h = cam_pos.z - 0.12 - 0.014
        make_box(name + "_FluidHead", (0.13, 0.14, 0.09), (0.0, 0.0, head_h + 0.04), bevel=0.01, mat=mats["cam_body"], col=col, parent=t_root)
        for k in range(3):
            ang = math.radians(k * 120.0 + 30.0)
            foot = Vector((math.cos(ang) * 0.42, math.sin(ang) * 0.42, 0.0))
            top = Vector((math.cos(ang) * 0.05, math.sin(ang) * 0.05, head_h))
            make_lofted_segment(f"{name}_TripodLeg_{k}", top, foot, r0_xy=(0.018, 0.018), r1_xy=(0.012, 0.012), rings=3, mat=mats["cam_chrome"], col=col, parent=t_root)

    piv = new_pivot(name, cam_pos, (0.0, 0.0, 180.0), None, col)

    # Local -Y is lens forward!
    make_box(name + "_Body", (0.14, 0.36, 0.21), (0.0, 0.0, 0.0), bevel=0.012, mat=mats["cam_body"], col=col, parent=piv)
    make_box(name + "_TapeDeck", (0.045, 0.20, 0.15), (-0.085, 0.02, -0.01), bevel=0.008, mat=mats["cam_body"], col=col, parent=piv)
    make_box(name + "_Battery", (0.11, 0.09, 0.16), (0.0, 0.22, 0.0), bevel=0.010, mat=mats["suit_black"], col=col, parent=piv)
    make_box(name + "_TopHandle", (0.032, 0.26, 0.024), (0.0, -0.02, 0.145), bevel=0.005, mat=mats["cam_body"], col=col, parent=piv)
    for hy in (-0.13, 0.09):
        make_box(f"{name}_HandlePost_{hy:.2f}", (0.028, 0.028, 0.045), (0.0, hy, 0.12), bevel=0.004, mat=mats["cam_body"], col=col, parent=piv)

    make_lathe(
        name + "_ZoomLens",
        [(0.0, 0.18), (0.052, 0.18), (0.056, 0.34), (0.062, 0.39), (0.0, 0.39)],
        segments=24,
        rot_deg=(90.0, 0.0, 0.0),
        mat=mats["cam_body"],
        col=col,
        parent=piv,
    )
    make_box(name + "_MatteBox", (0.16, 0.075, 0.13), (0.0, -0.42, 0.0), bevel=0.006, mat=mats["suit_black"], col=col, parent=piv)
    make_sphere(name + "_ObjectiveGlass", (0.0, -0.41, 0.0), radii=(0.052, 0.012, 0.052), subs=2, mat=mats["lens_glass"], col=col, parent=piv)
    make_box(name + "_ViewfinderTube", (0.055, 0.16, 0.055), (0.13, -0.03, 0.08), bevel=0.012, mat=mats["cam_body"], col=col, parent=piv)
    make_box(name + "_TopLampHousing", (0.09, 0.07, 0.075), (0.0, -0.15, 0.215), bevel=0.008, mat=mats["cam_body"], col=col, parent=piv)
    make_box(name + "_TopLampFace", (0.076, 0.012, 0.062), (0.0, -0.185, 0.215), bevel=0.002, mat=mats["press_lamp"], col=col, parent=piv)
    return piv


def set_pose_deg(obj, rot_xyz):
    obj.rotation_euler = (
        math.radians(rot_xyz[0]),
        math.radians(rot_xyz[1]),
        math.radians(rot_xyz[2]),
    )


def apply_sit_or_walk_legs(rig: dict, sit_s: float, walk_phase: float, walk_amp: float):
    """Exact foot-grounded sit/stand + natural human walking stride."""
    hips = rig["hips"]
    leg_r = rig["legs"]["R"]
    leg_l = rig["legs"]["L"]

    if sit_s > 0.001:
        ang = 88.0 * sit_s
        rad = math.radians(ang)
        hips.location = (0.0, 0.43 * math.sin(rad), 0.49 + 0.43 * math.cos(rad))
        hips.rotation_euler = (0.0, 0.0, 0.0)
        set_pose_deg(leg_r["hip"], (-ang, 3.0 * sit_s, -4.0 * sit_s))
        set_pose_deg(leg_l["hip"], (-ang, -3.0 * sit_s, 4.0 * sit_s))
        set_pose_deg(leg_r["knee"], (ang, 0.0, 0.0))
        set_pose_deg(leg_l["knee"], (ang, 0.0, 0.0))
        set_pose_deg(leg_r["ankle"], (0.0, 0.0, 0.0))
        set_pose_deg(leg_l["ankle"], (0.0, 0.0, 0.0))
    else:
        bob = -0.018 * (1.0 - abs(math.cos(walk_phase))) * walk_amp
        sway_x = 0.015 * math.sin(walk_phase) * walk_amp
        hips.location = (sway_x, 0.0, 0.92 + bob)
        set_pose_deg(hips, (0.0, 1.8 * math.sin(walk_phase) * walk_amp, 3.5 * math.sin(walk_phase) * walk_amp))

        hr = -25.0 * math.sin(walk_phase) * walk_amp
        hl = 25.0 * math.sin(walk_phase) * walk_amp
        kr = max(0.0, math.cos(walk_phase)) * 34.0 * walk_amp
        kl = max(0.0, -math.cos(walk_phase)) * 34.0 * walk_amp

        set_pose_deg(leg_r["hip"], (hr, 0.0, 0.0))
        set_pose_deg(leg_l["hip"], (hl, 0.0, 0.0))
        set_pose_deg(leg_r["knee"], (kr, 0.0, 0.0))
        set_pose_deg(leg_l["knee"], (kl, 0.0, 0.0))
        set_pose_deg(leg_r["ankle"], (-(hr + kr) * 0.35, 0.0, 0.0))
        set_pose_deg(leg_l["ankle"], (-(hl + kl) * 0.35, 0.0, 0.0))


def set_hand_curl(hand_dict: dict, point_amt: float, grip_amt: float = 0.0):
    """
    point_amt=1 -> index extended straight, other 3 fingers curled tight into palm!
    grip_amt=1  -> all 4 fingers curled tightly around mic shaft!
    0, 0        -> open expressive gesture hand!
    """
    sign = -1.0 if hand_dict["is_right"] else 1.0
    curl_total = clamp01(point_amt + grip_amt)
    set_pose_deg(hand_dict["curl"], (0.0, sign * (10.0 + 72.0 * curl_total), 0.0))
    set_pose_deg(hand_dict["curl_tip"], (0.0, sign * (8.0 + 78.0 * curl_total), 0.0))
    index_curl_deg = sign * (6.0 * (1.0 - point_amt) + 76.0 * grip_amt)
    set_pose_deg(hand_dict["index"], (0.0, index_curl_deg, 0.0))


def eval_central_speaker_trajectory(t: float):
    """
    Seamless 32.0s trajectory & expressive pose state for Char_01 (Central Speaker).
    Guaranteed C1 loop continuity: state(0.0) == state(32.0).
    """
    # Waypoints: (t0, t1, x0, y0, yaw0, x1, y1, yaw1)
    # Facing -Y: yaw=0 -> South (-Y), yaw>0 -> East (+X), yaw<0 -> West (-X), yaw=-135 -> NW
    chair_x, chair_y, chair_yaw = -0.81, 2.47, 7.0

    # Sit envelope: 1.0 at [0..3.6], stands up [3.6..4.8], stays 0.0 until [30.5..31.7], back to 1.0 at 32.0!
    if t < 3.6:
        sit_s = 1.0
    elif t < 4.8:
        sit_s = 1.0 - smoother01((t - 3.6) / 1.2)
    elif t < 30.5:
        sit_s = 0.0
    elif t < 31.7:
        sit_s = smoother01((t - 30.5) / 1.2)
    else:
        sit_s = 1.0

    # Root world (x, y, yaw) piecewise smooth trajectory
    if t < 4.8:
        rx, ry, yaw = chair_x, chair_y, chair_yaw
        walk_amp, walk_cycles = 0.0, 0.0
    elif t < 6.9:
        # Walk briskly forward from chair (-0.84, 2.38) to front press line (-0.22, 1.18)
        u = seg_alpha(t, 4.8, 6.9)
        rx = chair_x + (-0.22 - chair_x) * u
        ry = chair_y + (1.18 - chair_y) * u
        yaw = chair_yaw + (14.0 - chair_yaw) * smooth01((t - 4.8) / 1.4)
        walk_amp = math.sin(u * math.pi) ** 0.55
        walk_cycles = u * 2.0 * math.pi * 2.0
    elif t < 11.2:
        # Standing front-center addressing press ("按照基本法...")
        rx, ry = -0.22, 1.18
        yaw = 14.0 - 18.0 * window_env(t, 8.2, 10.6, 0.8)
        walk_amp, walk_cycles = 0.0, 0.0
    elif t < 13.1:
        # Pace West (viewer's left) (-0.22, 1.18) -> (-0.74, 1.28)
        u = seg_alpha(t, 11.2, 13.1)
        rx = -0.22 + (-0.74 - (-0.22)) * u
        ry = 1.18 + (1.28 - 1.18) * u
        yaw = 14.0 - 44.0 * window_env(t, 11.2, 12.6, 0.5) + 8.0 * u
        walk_amp = math.sin(u * math.pi) ** 0.6
        walk_cycles = u * 2.0 * math.pi * 1.5
    elif t < 15.7:
        # Address from West side, tapping chest ("作为一个长者...")
        rx, ry = -0.74, 1.28
        yaw = 22.0
        walk_amp, walk_cycles = 0.0, 0.0
    elif t < 17.0:
        # Step briskly in toward front-row female reporter (-0.74, 1.28) -> (-0.14, 1.06)
        u = seg_alpha(t, 15.7, 17.0)
        rx = -0.74 + (-0.14 - (-0.74)) * u
        ry = 1.28 + (1.06 - 1.28) * u
        yaw = 22.0 + (12.0 - 22.0) * u
        walk_amp = math.sin(u * math.pi) ** 0.6
        walk_cycles = u * 2.0 * math.pi * 1.5
    elif t < 21.0:
        # CLIMAX stance right in front of microphones: finger wagging & wide arms!
        rx, ry = -0.14, 1.06
        yaw = 12.0 - 8.0 * window_env(t, 19.5, 20.9, 0.5)
        walk_amp, walk_cycles = 0.0, 0.0
    elif t < 23.2:
        # Pace East (viewer's right) (-0.14, 1.06) -> (+0.26, 1.26)
        u = seg_alpha(t, 21.0, 23.2)
        rx = -0.14 + (0.26 - (-0.14)) * u
        ry = 1.06 + (1.26 - 1.06) * u
        yaw = 12.0 + (-18.0 - 12.0) * u
        walk_amp = math.sin(u * math.pi) ** 0.6
        walk_cycles = u * 2.0 * math.pi * 1.5
    elif t < 25.5:
        # Animated sweeping gesture & concluding wave-off from East side
        rx, ry = 0.26, 1.26
        yaw = -18.0
        walk_amp, walk_cycles = 0.0, 0.0
    elif t < 26.5:
        # Turn counter-clockwise (-18 -> -138 deg) to face back toward left-center armchair!
        u = seg_alpha(t, 25.5, 26.5)
        rx, ry = 0.26, 1.26
        yaw = -18.0 + (-138.0 - (-18.0)) * u
        walk_amp = math.sin(u * math.pi) * 0.35
        walk_cycles = u * math.pi
    elif t < 29.4:
        # Walk calmly back to left-center VIP armchair (+0.26, 1.26) -> (-0.84, 2.38)
        u = seg_alpha(t, 26.5, 29.4)
        rx = 0.26 + (chair_x - 0.26) * u
        ry = 1.26 + (chair_y - 1.26) * u
        yaw = -138.0
        walk_amp = math.sin(u * math.pi) ** 0.55
        walk_cycles = u * 2.0 * math.pi * 2.5
    elif t < 30.5:
        # Pivot clockwise back from -138 deg -> -6 deg to face front before sitting!
        u = seg_alpha(t, 29.4, 30.5)
        rx, ry = chair_x, chair_y
        yaw = -138.0 + (chair_yaw - (-138.0)) * u
        walk_amp = math.sin(u * math.pi) * 0.35
        walk_cycles = u * math.pi
    else:
        rx, ry, yaw = chair_x, chair_y, chair_yaw
        walk_amp, walk_cycles = 0.0, 0.0

    # -------------------------------------------------------------------------
    # Upper Body, Head, Jaw & Expressive Arm Choreography
    # -------------------------------------------------------------------------
    # Base seated armrest-resting pose (s=1) vs base standing pose (s=0)
    sh_r = [-28.0 * sit_s - 10.0 * (1.0 - sit_s), 12.0 * sit_s + 6.0 * (1.0 - sit_s), 0.0]
    el_r = [-58.0 * sit_s - 28.0 * (1.0 - sit_s), 0.0, 0.0]
    wr_r = [0.0, 0.0, 0.0]

    sh_l = [-28.0 * sit_s - 10.0 * (1.0 - sit_s), -12.0 * sit_s - 6.0 * (1.0 - sit_s), 0.0]
    el_l = [-58.0 * sit_s - 28.0 * (1.0 - sit_s), 0.0, 0.0]
    wr_l = [0.0, 0.0, 0.0]

    point_r = 0.0
    torso_pitch = -6.0 * sit_s + 2.5 * (1.0 - sit_s) + 1.2 * math.sin(t * 2.0 * math.pi / 4.0)
    torso_yaw = 0.0
    head_pitch = 2.0 * sit_s - 3.0 * (1.0 - sit_s)
    head_yaw = 0.0
    head_roll = 0.0
    speaking = 0.0

    # 1) Seated listening & head-shake before standing (1.5s .. 4.8s)
    w_listen = window_env(t, 1.2, 3.6, 0.5)
    torso_pitch += 10.0 * w_listen
    head_yaw += 10.0 * window_env(t, 1.0, 2.5, 0.4) + 12.0 * math.sin((t - 2.6) * 9.5) * window_env(t, 2.6, 3.6, 0.25)

    # Stand-up & Sit-down forward torso momentum
    torso_pitch += 20.0 * window_env(t, 3.6, 4.8, 0.45)
    torso_pitch += 18.0 * window_env(t, 30.5, 31.7, 0.45)

    # Natural arm swing during walking segments
    if walk_amp > 0.01:
        swing = 20.0 * math.sin(walk_cycles) * walk_amp
        sh_r[0] += -swing
        sh_l[0] += swing
        el_r[0] += -18.0 * walk_amp
        el_l[0] += -18.0 * walk_amp

    # 2) Beat A (6.8s .. 11.2s): Emphatic Double-Hand Outward Clearing Waves!
    w_wave = window_env(t, 6.8, 11.2, 0.55)
    if w_wave > 0.001:
        sweep = math.sin((t - 6.8) * 4.4)
        sh_r[0] += (-42.0 + 8.0 * sweep) * w_wave
        sh_r[1] += (26.0 + 20.0 * max(0.0, sweep)) * w_wave
        el_r[0] += (-46.0 + 12.0 * sweep) * w_wave
        wr_r[2] += -20.0 * w_wave

        sh_l[0] += (-42.0 + 8.0 * sweep) * w_wave
        sh_l[1] += (-26.0 - 20.0 * max(0.0, sweep)) * w_wave
        el_l[0] += (-46.0 + 12.0 * sweep) * w_wave
        wr_l[2] += 20.0 * w_wave

        torso_pitch += 6.0 * w_wave
        head_pitch += (5.0 + 4.0 * abs(sweep)) * w_wave
        head_yaw += 14.0 * math.sin((t - 7.0) * 1.6) * w_wave
        speaking = max(speaking, w_wave)

    # 3) Beat B (13.0s .. 15.8s): Both Hands to Chest ("作为一个长者...") & Earnest Nodding
    w_elder = window_env(t, 12.9, 15.8, 0.5)
    if w_elder > 0.001:
        pulse = math.sin((t - 13.0) * 5.2)
        sh_r[0] += -42.0 * w_elder
        sh_r[1] += (-12.0 - 6.0 * pulse) * w_elder
        el_r[0] += (-74.0 - 8.0 * pulse) * w_elder

        sh_l[0] += -38.0 * w_elder
        sh_l[1] += (12.0 + 6.0 * pulse) * w_elder
        el_l[0] += (-70.0 - 8.0 * pulse) * w_elder

        torso_pitch += 5.0 * w_elder
        head_pitch += (7.0 + 5.0 * abs(pulse)) * w_elder
        head_roll += 4.0 * w_elder
        speaking = max(speaking, w_elder)

    # 4) Beat C (16.8s .. 19.7s): CLIMAX — Clear Silhouette Raised Right Arm + Wagging Index Finger!
    w_point = window_env(t, 16.7, 19.7, 0.42)
    if w_point > 0.001:
        wag = math.sin((t - 16.9) * 8.2)
        sh_r[0] += (-66.0 - 11.0 * wag) * w_point
        sh_r[1] += 14.0 * w_point
        sh_r[2] += -30.0 * w_point  # Turn elbow crease outward so raised pointing hand stays clear of face!
        el_r[0] += (-46.0 + 12.0 * wag) * w_point
        wr_r[0] += 12.0 * w_point
        point_r = w_point

        # Left hand open at waist/chest counter-gesturing
        sh_l[0] += -32.0 * w_point
        sh_l[1] += -20.0 * w_point
        el_l[0] += (-52.0 + 8.0 * wag) * w_point

        torso_pitch += (9.0 + 3.0 * max(0.0, -wag)) * w_point
        head_pitch += (8.0 + 4.5 * max(0.0, -wag)) * w_point
        head_yaw += -6.0 * w_point
        speaking = max(speaking, w_point)

    # 5) Beat D (19.5s .. 21.1s): Wide Exasperated Two-Arm Spread ("Sometimes naive!")
    w_spread = window_env(t, 19.5, 21.1, 0.38)
    if w_spread > 0.001:
        sh_r[0] += -58.0 * w_spread
        sh_r[1] += 42.0 * w_spread
        el_r[0] += -45.0 * w_spread

        sh_l[0] += -58.0 * w_spread
        sh_l[1] += -42.0 * w_spread
        el_l[0] += -45.0 * w_spread

        torso_pitch += 5.0 * w_spread
        head_pitch += 6.0 * w_spread
        head_roll += -5.0 * w_spread
        speaking = max(speaking, w_spread)

    # 6) Beat E (22.6s .. 25.5s): Left Hand on High Belt + Sweeping Right Hand & Wave-Off!
    w_sweep = window_env(t, 22.5, 25.5, 0.48)
    if w_sweep > 0.001:
        arc = math.sin((t - 22.6) * 5.0)
        # Left hand resting near high-waisted hip/belt
        sh_l[0] += 14.0 * w_sweep
        sh_l[1] += -26.0 * w_sweep
        el_l[0] += -76.0 * w_sweep

        # Right hand sweeping grandly then downward wave-off
        sh_r[0] += (-62.0 + 18.0 * arc) * w_sweep
        sh_r[1] += (24.0 + 14.0 * arc) * w_sweep
        el_r[0] += (-44.0 + 12.0 * arc) * w_sweep

        torso_yaw += -8.0 * arc * w_sweep
        head_yaw += 12.0 * arc * w_sweep
        speaking = max(speaking, w_sweep)

    # Syllabic jaw articulation whenever speaking > 0
    jaw_open_deg = speaking * (7.0 + 7.5 * max(0.0, math.sin(t * 15.5) * math.cos(t * 6.3)))

    return {
        "rx": rx,
        "ry": ry,
        "yaw": yaw,
        "sit_s": sit_s,
        "walk_amp": walk_amp,
        "walk_cycles": walk_cycles,
        "torso": (torso_pitch, 0.0, torso_yaw),
        "head": (head_pitch, head_roll, head_yaw),
        "jaw_deg": jaw_open_deg,
        "sh_r": sh_r,
        "el_r": el_r,
        "wr_r": wr_r,
        "sh_l": sh_l,
        "el_l": el_l,
        "wr_l": wr_l,
        "point_r": point_r,
    }


def heading_deg_to_target(src_xy, tgt_xy) -> float:
    """Computes Euler Z yaw (deg) so local -Y faces from src_xy toward tgt_xy."""
    dx = tgt_xy[0] - src_xy[0]
    dy = tgt_xy[1] - src_xy[1]
    # Forward F = (sin(yaw), -cos(yaw)) == (dx, dy)/r -> yaw = atan2(dx, -dy)
    return math.degrees(math.atan2(dx, -dy))


def heading_deg_near(src_xy, tgt_xy, ref_deg: float = 180.0) -> float:
    """Computes continuous Euler Z yaw (deg) unwrapped closest to ref_deg (eliminates ±180° wrap spins!)."""
    raw = heading_deg_to_target(src_xy, tgt_xy)
    return ref_deg + ((raw - ref_deg + 180.0) % 360.0 - 180.0)


def angle_diff_deg(target_deg: float, base_deg: float) -> float:
    d = (target_deg - base_deg + 180.0) % 360.0 - 180.0
    return d


def build_and_animate_characters_and_press(mats: dict):
    col_chars = get_or_create_collection("03_Characters")
    col_press = get_or_create_collection("04_Press_Equipment")
    floor_z = 0.014

    bpy.context.scene.render.fps = FPS
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = TOTAL_FRAMES

    # 1. Central Speaker (Char_01)
    c_main = build_rigged_character(
        "Char_01_MainSpeaker",
        loc=(-0.81, 2.47, floor_z),
        yaw_deg=7.0,
        mats=mats,
        col=col_chars,
        height_scale=1.03,
        body_width=1.12,
        high_waisted=True,
        open_jacket=True,
        suit_mat_key="suit_charcoal_navy",
        shirt_mat_key="shirt_white",
        tie_mat_key="tie_crimson",
        hair_style="combed_back_high",
        hair_mat_key="hair_dark",
        has_thick_glasses=True,
    )

    # 2. Seated VIPs & Officials (Exact seated root offset: cx + 0.43*sin(yaw), cy - 0.43*cos(yaw), all facing INWARD!)
    def _seat_root(cx, cy, yaw_deg):
        rad = math.radians(yaw_deg)
        return (cx + 0.43 * math.sin(rad), cy - 0.43 * math.cos(rad), floor_z)

    seated_defs = [
        ("Char_02_SeatedVIP_Right", _seat_root(0.86, 2.90, -7.0), -7.0, 0.99, 1.06, "suit_dark_navy", "tie_navy", "silver_flattop", "hair_silver"),
        ("Char_03_Official_Left1", _seat_root(-4.70, 2.45, 74.0), 74.0, 0.99, 1.02, "suit_black", "tie_crimson", "parted", "hair_dark"),
        ("Char_04_Official_Left2", _seat_root(-4.82, 0.80, 88.0), 88.0, 0.98, 1.00, "suit_slate_grey", "tie_navy", "parted", "hair_dark"),
    ]
    seated_rigs = []
    for sname, sloc, syaw, hsc, bwd, smat, tmat, hstyle, hmat in seated_defs:
        r = build_rigged_character(
            sname, sloc, syaw, mats, col_chars,
            height_scale=hsc, body_width=bwd,
            suit_mat_key=smat, tie_mat_key=tmat, hair_style=hstyle, hair_mat_key=hmat,
        )
        seated_rigs.append((r, sloc, syaw))

    # 3. Four Front-Row Reporters Holding Broadcast Microphones
    rep_defs = [
        # (name, loc, base_yaw, female, suit_key, shirt_key, tie_key, hair, mic_hand, mic_quad)
        ("Char_05_LeadReporter", (0.28, -0.82, floor_z), 192.0, True, "suit_black", "blouse_cream", None, "female_bob", "R", 0),
        ("Char_06_Reporter_B", (-0.48, -0.88, floor_z), 170.0, False, "suit_slate_grey", "shirt_white", "tie_navy", "parted", "R", 1),
        ("Char_07_Reporter_C", (0.90, -0.78, floor_z), 210.0, True, "blazer_burgundy", "blouse_cream", None, "female_bob", "L", 2),
        ("Char_08_Reporter_D", (-1.06, -0.82, floor_z), 156.0, False, "suit_dark_navy", "shirt_white", "tie_crimson", "parted", "R", 3),
    ]
    rep_rigs = []
    for idx, (rname, rloc, ryaw, fem, skey, shkey, tkey, hst, mhand, mquad) in enumerate(rep_defs):
        r = build_rigged_character(
            rname, rloc, ryaw, mats, col_chars,
            height_scale=0.94 if fem else 0.98,
            body_width=0.94 if fem else 1.0,
            female=fem,
            suit_mat_key=skey,
            trouser_mat_key="suit_black" if fem else skey,
            shirt_mat_key=shkey,
            tie_mat_key=tkey,
            hair_style=hst,
        )
        attach_mic_to_wrist(f"Press_Mic_{idx+1}", r["arms"][mhand]["wrist"], mhand == "R", mquad, mats, col_press)
        if idx == 0:
            # Notepad in left hand of lead reporter
            make_box("Press_Notepad_Lead", (0.13, 0.19, 0.012), (0.0, -0.06, -0.09), rot_deg=(-65.0, 0.0, 0.0), bevel=0.002, mat=mats["notepad_paper"], col=col_press, parent=r["arms"]["L"]["wrist"])
        rep_rigs.append((r, Vector(rloc), ryaw, mhand, idx))

    # 4. Two ENG Betacam Cameramen + Panning Broadcast Cameras
    cam1_op = build_rigged_character(
        "Char_09_Cameraman_Shoulder", (-0.78, -1.72, floor_z), 172.0, mats, col_chars,
        height_scale=1.01, suit_mat_key="jacket_olive", trouser_mat_key="suit_slate_grey", tie_mat_key=None,
    )
    betacam_1 = build_betacam_rig("Press_Betacam_01_Shoulder", (-0.62, -1.58, 1.58), mats, col_press, on_tripod=False)

    cam2_op = build_rigged_character(
        "Char_10_Cameraman_Tripod", (1.40, -1.86, floor_z), 205.0, mats, col_chars,
        height_scale=1.0, suit_mat_key="suit_slate_grey", trouser_mat_key="suit_black", tie_mat_key=None,
    )
    betacam_2 = build_betacam_rig("Press_Betacam_02_Tripod", (1.22, -1.48, 1.54), mats, col_press, on_tripod=True)

    # 5. Boom Audio Operator + Overhead Boom Pole Rig
    boom_op = build_rigged_character(
        "Char_11_Audio_BoomOp", (-1.62, -1.32, floor_z), 152.0, mats, col_chars,
        height_scale=1.0, suit_mat_key="suit_black", trouser_mat_key="suit_slate_grey", tie_mat_key=None,
    )
    boom_piv = new_pivot("Press_BoomRig", (-1.52, -1.22, 1.78), (22.0, 0.0, 152.0), None, col_press)
    make_lofted_segment("Press_BoomPole", Vector((0.0, 0.25, 0.0)), Vector((0.0, -2.35, 0.55)), r0_xy=(0.014, 0.014), r1_xy=(0.009, 0.009), rings=4, mat=mats["cam_body"], col=col_press, parent=boom_piv)
    make_lofted_segment("Press_BoomBlimp", Vector((0.0, -2.22, 0.52)), Vector((0.0, -2.56, 0.46)), r0_xy=(0.048, 0.048), r1_xy=(0.048, 0.048), rings=4, mat=mats["boom_blimp"], col=col_press, parent=boom_piv)

    # 6. Press Photojournalist + SLR with White Telephoto Lens attached to Right Wrist
    photo_op = build_rigged_character(
        "Char_12_Photographer", (0.68, -1.55, floor_z), 196.0, mats, col_chars,
        height_scale=0.99, suit_mat_key="jacket_olive", trouser_mat_key="suit_black", tie_mat_key=None,
    )
    slr_piv = new_pivot("Press_SLR_Rig", (0.04, -0.06, -0.07), (-85.0, 0.0, 0.0), photo_op["arms"]["R"]["wrist"], col_press)
    make_box("Press_SLR_Body", (0.14, 0.08, 0.11), (0.0, 0.0, 0.0), bevel=0.008, mat=mats["cam_body"], col=col_press, parent=slr_piv)
    make_box("Press_SLR_Flash", (0.06, 0.07, 0.09), (0.0, 0.0, 0.09), bevel=0.005, mat=mats["cam_body"], col=col_press, parent=slr_piv)
    make_lofted_segment("Press_SLR_TeleLens", Vector((0.0, -0.04, 0.0)), Vector((0.0, -0.26, 0.0)), r0_xy=(0.040, 0.040), r1_xy=(0.044, 0.044), rings=4, mat=mats["telephoto_white"], col=col_press, parent=slr_piv)

    # 7. Flanking Protocol / Security Staff (facing INWARD toward hall center!)
    staff_rigs = []
    for sname, sloc, syaw in (
        ("Char_13_Protocol_West", (-5.25, 3.35, floor_z), 50.0),
        ("Char_14_Protocol_East", (5.25, 3.35, floor_z), -50.0),
    ):
        sr = build_rigged_character(sname, sloc, syaw, mats, col_chars, height_scale=1.01, suit_mat_key="suit_black", tie_mat_key="tie_navy")
        staff_rigs.append((sr, Vector(sloc), syaw))

    # =========================================================================
    # BAKE KEYFRAMES ACROSS THE ENTIRE 32-SECOND LOOP (Step = 2 frames = 12Hz keys
    # with Bezier smooth interpolation, exact match at frame 0 and TOTAL_FRAMES!)
    # =========================================================================
    key_step = 2
    frames = list(range(0, TOTAL_FRAMES + 1, key_step))
    if frames[-1] != TOTAL_FRAMES:
        frames.append(TOTAL_FRAMES)

    def kf_loc(obj, f):
        obj.keyframe_insert(data_path="location", frame=f)

    def kf_rot(obj, f):
        obj.keyframe_insert(data_path="rotation_euler", frame=f)

    for f in frames:
        # Seamless periodic wrap: t == 0.0 at BOTH frame 0 and frame TOTAL_FRAMES!
        t = 0.0 if f == TOTAL_FRAMES else (f / float(FPS))
        st = eval_central_speaker_trajectory(t)
        sp_xy = (st["rx"], st["ry"])

        # --- 1. Central Speaker ---
        c_main["root"].location = (st["rx"], st["ry"], floor_z)
        set_pose_deg(c_main["root"], (0.0, 0.0, st["yaw"]))
        apply_sit_or_walk_legs(c_main, st["sit_s"], st["walk_cycles"], st["walk_amp"])
        set_pose_deg(c_main["torso"], st["torso"])
        set_pose_deg(c_main["neck"], st["head"])
        set_pose_deg(c_main["jaw"], (st["jaw_deg"], 0.0, 0.0))

        set_pose_deg(c_main["arms"]["R"]["shoulder"], st["sh_r"])
        set_pose_deg(c_main["arms"]["R"]["elbow"], st["el_r"])
        set_pose_deg(c_main["arms"]["R"]["wrist"], st["wr_r"])
        set_hand_curl(c_main["arms"]["R"]["hand"], point_amt=st["point_r"], grip_amt=0.0)

        set_pose_deg(c_main["arms"]["L"]["shoulder"], st["sh_l"])
        set_pose_deg(c_main["arms"]["L"]["elbow"], st["el_l"])
        set_pose_deg(c_main["arms"]["L"]["wrist"], st["wr_l"])
        set_hand_curl(c_main["arms"]["L"]["hand"], point_amt=0.0, grip_amt=0.0)

        for obj in (
            c_main["root"], c_main["hips"], c_main["torso"], c_main["neck"], c_main["jaw"],
            c_main["legs"]["R"]["hip"], c_main["legs"]["R"]["knee"], c_main["legs"]["R"]["ankle"],
            c_main["legs"]["L"]["hip"], c_main["legs"]["L"]["knee"], c_main["legs"]["L"]["ankle"],
            c_main["arms"]["R"]["shoulder"], c_main["arms"]["R"]["elbow"], c_main["arms"]["R"]["wrist"],
            c_main["arms"]["R"]["hand"]["index"], c_main["arms"]["R"]["hand"]["curl"], c_main["arms"]["R"]["hand"]["curl_tip"],
            c_main["arms"]["L"]["shoulder"], c_main["arms"]["L"]["elbow"], c_main["arms"]["L"]["wrist"],
        ):
            kf_rot(obj, f)
        kf_loc(c_main["root"], f)
        kf_loc(c_main["hips"], f)

        # --- 2. Seated VIP & Left-Wing Officials ---
        for idx_s, (srig, sloc, syaw) in enumerate(seated_rigs):
            if f == 0:
                apply_sit_or_walk_legs(srig, 1.0, 0.0, 0.0)
                set_pose_deg(srig["arms"]["R"]["shoulder"], (-22.0, -8.0, 0.0))
                set_pose_deg(srig["arms"]["R"]["elbow"], (-68.0, 0.0, 0.0))
                set_pose_deg(srig["arms"]["L"]["shoulder"], (-22.0, 8.0, 0.0))
                set_pose_deg(srig["arms"]["L"]["elbow"], (-68.0, 0.0, 0.0))
                set_hand_curl(srig["arms"]["R"]["hand"], 0.0, 0.65)
                set_hand_curl(srig["arms"]["L"]["hand"], 0.0, 0.65)

            aim_yaw = heading_deg_to_target((sloc[0], sloc[1] + 0.42), sp_xy)
            rel_yaw = max(-34.0, min(34.0, angle_diff_deg(aim_yaw, syaw) * 0.55))
            breath = 1.2 * math.sin(t * 2.0 * math.pi / 4.0 + idx_s)
            nod = 3.5 * math.sin(t * 2.0 * math.pi / 8.0 + idx_s * 1.7) * (1.0 - st["sit_s"])
            set_pose_deg(srig["torso"], (-7.0 + breath * 0.5, 0.0, rel_yaw * 0.25))
            set_pose_deg(srig["neck"], (2.0 + nod, 0.0, rel_yaw * 0.75))
            kf_rot(srig["torso"], f)
            kf_rot(srig["neck"], f)

        # --- 3. Front-Row Reporters Holding Microphones ---
        q_env = window_env(t, 0.4, 3.6, 0.5)  # Lead reporter asking initial sharp question
        close_push = window_env(t, 5.8, 25.4, 0.9)  # Speaker standing close to press line!

        for rrig, rloc, ryaw, mhand, r_idx in rep_rigs:
            aim_yaw = heading_deg_to_target((rloc.x, rloc.y), sp_xy)
            rel_yaw = max(-28.0, min(28.0, angle_diff_deg(aim_yaw, ryaw)))

            # Subtle forward step when asking, slight lean-back when speaker steps right up close!
            step_fwd = (0.12 * q_env if r_idx == 0 else 0.03 * q_env) - 0.07 * close_push
            rad_yaw = math.radians(ryaw)
            fwd_vec = Vector((math.sin(rad_yaw), -math.cos(rad_yaw), 0.0))
            rrig["root"].location = rloc + fwd_vec * step_fwd
            set_pose_deg(rrig["root"], (0.0, 0.0, ryaw + rel_yaw * 0.45))
            apply_sit_or_walk_legs(rrig, 0.0, t * 2.0 * math.pi / 4.0 + r_idx, 0.06)

            lean = (7.0 + 4.0 * q_env) - 9.5 * close_push
            set_pose_deg(rrig["torso"], (lean, 0.0, rel_yaw * 0.25))
            look_up = -7.5 * close_push + (4.5 * math.sin(t * 7.0) * q_env if r_idx == 0 else 0.0)
            set_pose_deg(rrig["neck"], (look_up, 0.0, rel_yaw * 0.45))

            # Lead reporter jaw speaks during question [0.5 .. 3.4s]!
            rep_jaw = (8.5 * max(0.0, math.sin(t * 14.0)) * q_env) if r_idx == 0 else 0.0
            set_pose_deg(rrig["jaw"], (rep_jaw, 0.0, 0.0))

            # Outstretched microphone arm dynamically tracks speaker height & position!
            mic_arm = rrig["arms"][mhand]
            other_side = "L" if mhand == "R" else "R"
            other_arm = rrig["arms"][other_side]
            reach_boost = 10.0 * close_push + (8.0 * q_env if r_idx == 0 else 0.0)
            set_pose_deg(mic_arm["shoulder"], (-62.0 - reach_boost * 0.6, (-8.0 if mhand == "R" else 8.0), 0.0))
            set_pose_deg(mic_arm["elbow"], (-44.0 + reach_boost * 0.4, 0.0, 0.0))
            set_hand_curl(mic_arm["hand"], 0.0, 1.0)

            if r_idx == 0:
                set_pose_deg(other_arm["shoulder"], (-28.0, 10.0, 0.0))
                set_pose_deg(other_arm["elbow"], (-66.0, 0.0, 0.0))
            else:
                set_pose_deg(other_arm["shoulder"], (-8.0, (-5.0 if other_side == "L" else 5.0), 0.0))
                set_pose_deg(other_arm["elbow"], (-18.0, 0.0, 0.0))
            set_hand_curl(other_arm["hand"], 0.0, 0.8)

            kf_loc(rrig["root"], f)
            for obj in (rrig["root"], rrig["torso"], rrig["neck"], rrig["jaw"], mic_arm["shoulder"], mic_arm["elbow"]):
                kf_rot(obj, f)

        # --- 4. Panning ENG Betacam Broadcast Cameras + Operators ---
        sp_head_z = 1.56 - 0.38 * st["sit_s"]
        for bcam, cop, base_cpos, is_shoulder, base_cyaw in (
            (betacam_1, cam1_op, Vector((-0.62, -1.58, 1.58)), True, 172.0),
            (betacam_2, cam2_op, Vector((1.22, -1.48, 1.54)), False, 205.0),
        ):
            cyaw = heading_deg_near((base_cpos.x, base_cpos.y), sp_xy, base_cyaw)
            dist_xy = math.hypot(sp_xy[0] - base_cpos.x, sp_xy[1] - base_cpos.y)
            cpitch = math.degrees(math.atan2(sp_head_z - base_cpos.z, max(dist_xy, 0.5)))
            # Note: local -Y forward -> positive rot_x pitches -Y DOWNWARD, so -cpitch aims UP!
            set_pose_deg(bcam, (-cpitch * 0.65, 0.0, cyaw))
            kf_rot(bcam, f)

            set_pose_deg(cop["root"], (0.0, 0.0, cyaw))
            set_pose_deg(cop["torso"], (2.0, 0.0, 0.0))
            set_pose_deg(cop["neck"], (-2.5, 0.0, 0.0))
            if f == 0:
                apply_sit_or_walk_legs(cop, 0.0, 0.0, 0.0)
                set_pose_deg(cop["arms"]["R"]["shoulder"], (-68.0 if is_shoulder else -44.0, 8.0, 0.0))
                set_pose_deg(cop["arms"]["R"]["elbow"], (-72.0 if is_shoulder else -58.0, 0.0, 0.0))
                set_pose_deg(cop["arms"]["L"]["shoulder"], (-62.0 if is_shoulder else -44.0, -14.0, 0.0))
                set_pose_deg(cop["arms"]["L"]["elbow"], (-64.0 if is_shoulder else -58.0, 0.0, 0.0))
            kf_rot(cop["root"], f)
            kf_rot(cop["torso"], f)
            kf_rot(cop["neck"], f)

        # --- 5. Overhead Boom Audio Operator Tracking Speaker ---
        boom_yaw = heading_deg_near((-1.52, -1.22), sp_xy, 152.0)
        boom_dip = 16.0 - 7.0 * close_push
        set_pose_deg(boom_piv, (boom_dip, 0.0, boom_yaw))
        set_pose_deg(boom_op["root"], (0.0, 0.0, boom_yaw))
        set_pose_deg(boom_op["torso"], (1.5, 0.0, 0.0))
        set_pose_deg(boom_op["neck"], (-4.0, 0.0, 0.0))
        if f == 0:
            apply_sit_or_walk_legs(boom_op, 0.0, 0.0, 0.0)
            set_pose_deg(boom_op["arms"]["R"]["shoulder"], (-115.0, 8.0, 0.0))
            set_pose_deg(boom_op["arms"]["R"]["elbow"], (-28.0, 0.0, 0.0))
            set_pose_deg(boom_op["arms"]["L"]["shoulder"], (-102.0, -10.0, 0.0))
            set_pose_deg(boom_op["arms"]["L"]["elbow"], (-34.0, 0.0, 0.0))
        kf_rot(boom_piv, f)
        kf_rot(boom_op["root"], f)
        kf_rot(boom_op["torso"], f)
        kf_rot(boom_op["neck"], f)

        # --- 6. Photojournalist Lifting SLR at Peak Dramatic Moments ---
        snap_env = max(
            window_env(t, 6.6, 8.8, 0.45),
            window_env(t, 16.6, 20.6, 0.45),
            window_env(t, 22.6, 24.6, 0.45),
        )
        ph_yaw = heading_deg_near((0.68, -1.55), sp_xy, 196.0)
        set_pose_deg(photo_op["root"], (0.0, 0.0, ph_yaw))
        set_pose_deg(photo_op["torso"], (2.0 * snap_env, 0.0, 0.0))
        set_pose_deg(photo_op["neck"], (-2.0 - 2.0 * snap_env, 0.0, 0.0))
        set_pose_deg(photo_op["arms"]["R"]["shoulder"], (-42.0 - 38.0 * snap_env, 12.0, 0.0))
        set_pose_deg(photo_op["arms"]["R"]["elbow"], (-58.0 - 34.0 * snap_env, 0.0, 0.0))
        set_pose_deg(photo_op["arms"]["L"]["shoulder"], (-40.0 - 36.0 * snap_env, -16.0, 0.0))
        set_pose_deg(photo_op["arms"]["L"]["elbow"], (-55.0 - 30.0 * snap_env, 0.0, 0.0))
        if f == 0:
            apply_sit_or_walk_legs(photo_op, 0.0, 0.0, 0.0)
        for obj in (
            photo_op["root"], photo_op["torso"], photo_op["neck"],
            photo_op["arms"]["R"]["shoulder"], photo_op["arms"]["R"]["elbow"],
            photo_op["arms"]["L"]["shoulder"], photo_op["arms"]["L"]["elbow"],
        ):
            kf_rot(obj, f)

        # --- 7. Flanking Protocol Staff Subtle Attention & Concluding Step ---
        staff_alert = window_env(t, 23.0, 27.5, 0.8)
        for srig, sloc, syaw in staff_rigs:
            if f == 0:
                apply_sit_or_walk_legs(srig, 0.0, 0.0, 0.0)
                set_pose_deg(srig["arms"]["R"]["shoulder"], (-10.0, -14.0, 0.0))
                set_pose_deg(srig["arms"]["R"]["elbow"], (-32.0, 0.0, 0.0))
                set_pose_deg(srig["arms"]["L"]["shoulder"], (-10.0, 14.0, 0.0))
                set_pose_deg(srig["arms"]["L"]["elbow"], (-32.0, 0.0, 0.0))
            aim_s = heading_deg_to_target((sloc.x, sloc.y), sp_xy)
            rel_s = max(-30.0, min(30.0, angle_diff_deg(aim_s, syaw)))
            set_pose_deg(srig["neck"], (2.0 * staff_alert, 0.0, rel_s * 0.7))
            set_pose_deg(srig["torso"], (3.0 * staff_alert, 0.0, rel_s * 0.2))
            kf_rot(srig["neck"], f)
            kf_rot(srig["torso"], f)

    # Clamp all animation F-curve handles to AUTO_CLAMPED so spline segments never overshoot!
    for action in bpy.data.actions:
        if hasattr(action, "fcurves"):
            for fc in action.fcurves:
                for kp in fc.keyframe_points:
                    kp.handle_left_type = "AUTO_CLAMPED"
                    kp.handle_right_type = "AUTO_CLAMPED"
                fc.update()
