"""
Master Blender 5.x scene builder, Cycles renderer, and glTF (.glb) exporter
for the Press Reception Hall 3D scene.
"""

import os
import sys
import time
import math
import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BLENDER_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from materials_lib import build_all_materials
from arch_furniture import get_or_create_collection, build_architecture_and_furniture
from rigged_characters_anim import build_and_animate_characters_and_press, FPS


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_area_light(name: str, loc, target_pt: Vector, energy: float, color_rgb, size_x: float, size_y: float, col):
    ldata = bpy.data.lights.new(name=name + "_Data", type="AREA")
    ldata.energy = energy
    ldata.color = color_rgb
    ldata.shape = "RECTANGLE"
    ldata.size = size_x
    ldata.size_y = size_y

    lobj = bpy.data.objects.new(name, ldata)
    lobj.location = loc
    direction = Vector(target_pt) - Vector(loc)
    lobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    col.objects.link(lobj)
    return lobj


def add_spot_light(name: str, loc, target_pt: Vector, energy: float, color_rgb, spot_deg: float, blend: float, radius: float, col):
    ldata = bpy.data.lights.new(name=name + "_Data", type="SPOT")
    ldata.energy = energy
    ldata.color = color_rgb
    ldata.spot_size = math.radians(spot_deg)
    ldata.spot_blend = blend
    ldata.shadow_soft_size = radius

    lobj = bpy.data.objects.new(name, ldata)
    lobj.location = loc
    direction = Vector(target_pt) - Vector(loc)
    lobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    col.objects.link(lobj)
    return lobj


def add_camera(name: str, loc, target_pt: Vector, lens_mm: float, col, dof_dist: float = 0.0, fstop: float = 4.0):
    cdata = bpy.data.cameras.new(name=name + "_Data")
    cdata.lens = lens_mm
    cdata.clip_start = 0.08
    cdata.clip_end = 80.0
    if dof_dist > 0.0:
        cdata.dof.use_dof = True
        cdata.dof.focus_distance = dof_dist
        cdata.dof.aperture_fstop = fstop

    cobj = bpy.data.objects.new(name, cdata)
    cobj.location = loc
    direction = Vector(target_pt) - Vector(loc)
    cobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    col.objects.link(cobj)
    return cobj


def setup_lighting_and_world():
    col_light = get_or_create_collection("05_Lighting")

    # Warm ambient interior world bounce (calibrated for realistic interior contrast)
    world = bpy.data.worlds.new("ReceptionHall_World")
    bpy.context.scene.world = world
    if not world.use_nodes:
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.08, 0.06, 0.045, 1.0)
        bg.inputs["Strength"].default_value = 0.05

    # 1. Main Grand Chandelier Warm Illumination (3450K)
    add_area_light(
        "Light_Chandelier_Main",
        loc=(0.0, 0.35, 3.95),
        target_pt=(0.0, 0.75, 0.0),
        energy=230.0,
        color_rgb=(1.0, 0.88, 0.70),
        size_x=2.4,
        size_y=2.4,
        col=col_light,
    )

    # 2. Four Perimeter Ceiling Cove Fill Lights (3600K)
    cove_fills = [
        ("Light_HallFill_North", (0.0, 3.4, 5.1), (0.0, 2.8, 1.0), 75.0, 5.5, 1.8),
        ("Light_HallFill_South", (0.0, -3.2, 5.1), (0.0, -1.2, 1.0), 65.0, 5.5, 1.8),
        ("Light_HallFill_West", (-4.2, 0.4, 5.0), (-2.2, 0.6, 1.0), 65.0, 1.8, 5.0),
        ("Light_HallFill_East", (4.2, 0.4, 5.0), (2.2, 0.6, 1.0), 65.0, 1.8, 5.0),
    ]
    for lname, lloc, ltgt, lenergy, sx, sy in cove_fills:
        add_area_light(lname, lloc, ltgt, lenergy, (1.0, 0.91, 0.76), sx, sy, col_light)

    # 3. Screen & VIP Backdrop Grazing Accent Spots (3800K)
    add_spot_light(
        "Light_ScreenAccent_Left",
        loc=(-1.8, 2.0, 4.7),
        target_pt=(-0.9, 4.3, 1.7),
        energy=155.0,
        color_rgb=(1.0, 0.90, 0.74),
        spot_deg=56.0,
        blend=0.55,
        radius=0.35,
        col=col_light,
    )
    add_spot_light(
        "Light_ScreenAccent_Right",
        loc=(1.8, 2.0, 4.7),
        target_pt=(0.9, 4.3, 1.7),
        energy=155.0,
        color_rgb=(1.0, 0.90, 0.74),
        spot_deg=56.0,
        blend=0.55,
        radius=0.35,
        col=col_light,
    )

    # 4. Iconic Year-2000 ENG Broadcast Camera On-Camera Spotlights (5300K crisp news key!)
    add_spot_light(
        "Light_ENG_Cam1_Key",
        loc=(-0.58, -1.35, 1.82),
        target_pt=(-0.24, 1.38, 1.44),
        energy=175.0,
        color_rgb=(0.94, 0.97, 1.0),
        spot_deg=44.0,
        blend=0.45,
        radius=0.12,
        col=col_light,
    )
    add_spot_light(
        "Light_ENG_Cam2_Fill",
        loc=(1.15, -1.25, 1.76),
        target_pt=(0.20, 2.05, 1.30),
        energy=95.0,
        color_rgb=(0.95, 0.98, 1.0),
        spot_deg=50.0,
        blend=0.55,
        radius=0.16,
        col=col_light,
    )


def setup_cameras() -> dict:
    col_cam = get_or_create_collection("06_Cameras")
    cams = {}

    # 1. Classic Oct 27, 2000 TV Broadcast Angle (Press Row Eye-Level)
    cams["classic_broadcast"] = add_camera(
        "Cam_01_Classic_Broadcast",
        loc=(-0.10, -1.52, 1.59),
        target_pt=(-0.02, 1.62, 1.32),
        lens_mm=37.0,
        col=col_cam,
        dof_dist=2.95,
        fstop=4.8,
    )

    # 2. Dramatic Confrontation Side-Wide Cross-Section (Full Tableau)
    cams["side_confrontation"] = add_camera(
        "Cam_02_Side_Confrontation_Wide",
        loc=(-4.35, -0.15, 1.82),
        target_pt=(0.20, 0.95, 1.38),
        lens_mm=24.0,
        col=col_cam,
    )

    # 3. Reverse Over-the-Shoulder from VIP Seating toward HK Reporters & Cameras
    cams["vip_over_shoulder"] = add_camera(
        "Cam_03_Over_Shoulder_VIP",
        loc=(-1.12, 2.52, 1.74),
        target_pt=(0.18, -0.78, 1.34),
        lens_mm=30.0,
        col=col_cam,
    )

    # 4. Medium-Close Portrait & Gesture Detail Shot (with balanced headroom!)
    cams["closeup_gesture"] = add_camera(
        "Cam_04_CloseUp_Gesture",
        loc=(0.06, -0.62, 1.56),
        target_pt=(-0.22, 1.36, 1.53),
        lens_mm=50.0,
        col=col_cam,
        dof_dist=2.02,
        fstop=4.2,
    )

    # 5. Architectural Elevated Overview of Reception Hall
    cams["hall_overview"] = add_camera(
        "Cam_05_Hall_Overview",
        loc=(5.15, -4.65, 4.05),
        target_pt=(-0.20, 1.15, 1.25),
        lens_mm=22.0,
        col=col_cam,
    )

    bpy.context.scene.camera = cams["classic_broadcast"]
    return cams


def render_views(cams: dict, res_x: int = 1280, res_y: int = 720, samples: int = 64):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.image_settings.file_format = "PNG"

    # AgX / Filmic high-dynamic-range tone mapping
    available_vt = [e.identifier for e in scene.view_settings.bl_rna.properties["view_transform"].enum_items]
    if "AgX" in available_vt:
        scene.view_settings.view_transform = "AgX"
        available_looks = [e.identifier for e in scene.view_settings.bl_rna.properties["look"].enum_items]
        if "AgX - Medium High Contrast" in available_looks:
            scene.view_settings.look = "AgX - Medium High Contrast"
    elif "Filmic" in available_vt:
        scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = -0.20

    render_dir = os.path.join(BLENDER_DIR, "renders")
    os.makedirs(render_dir, exist_ok=True)

    for key, cam_obj in cams.items():
        t0 = time.time()
        scene.camera = cam_obj
        out_path = os.path.join(render_dir, f"render_{key}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {key} -> {out_path} in {time.time() - t0:.2f}s")

    # Restore primary broadcast camera
    scene.camera = cams["classic_broadcast"]


def export_glb_and_blend():
    export_dir = os.path.join(REPO_ROOT, "public", "assets")
    os.makedirs(export_dir, exist_ok=True)
    glb_path = os.path.join(export_dir, "press_hall.glb")

    bpy.context.scene.frame_set(0)
    t0 = time.time()
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        export_apply=False,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_animations=True,
        export_animation_mode="SCENE",
        export_anim_scene_split_object=False,
        export_bake_animation=True,
        export_optimize_animation_size=True,
        export_image_format="AUTO",
        export_jpeg_quality=85,
    )
    print(f"Exported Animated GLB -> {glb_path} ({os.path.getsize(glb_path)/1024/1024:.2f} MB) in {time.time() - t0:.2f}s")

    # Set frame to iconic climax gesture (t=18.0s) and Cycles device to GPU for interactive Blender editing
    bpy.context.scene.frame_set(int(18.0 * FPS))
    bpy.context.scene.cycles.device = "GPU"
    blend_path = os.path.join(BLENDER_DIR, "press_hall.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)
    print(f"Saved Blender file -> {blend_path}")


def render_keyframe_beats(cams: dict, res_x: int = 1280, res_y: int = 720, samples: int = 44):
    """Render 3 key narrative animation beats to verify poses, lighting, and zero-text textures."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.image_settings.file_format = "PNG"

    available_vt = [e.identifier for e in scene.view_settings.bl_rna.properties["view_transform"].enum_items]
    if "AgX" in available_vt:
        scene.view_settings.view_transform = "AgX"
        available_looks = [e.identifier for e in scene.view_settings.bl_rna.properties["look"].enum_items]
        if "AgX - Medium High Contrast" in available_looks:
            scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.20

    render_dir = os.path.join(BLENDER_DIR, "renders")
    os.makedirs(render_dir, exist_ok=True)

    beats = [
        ("beat1_seated_qa", 2.0, cams["side_confrontation"]),
        ("beat2_double_wave", 9.0, cams["classic_broadcast"]),
        ("beat3_climax_point", 18.0, cams["classic_broadcast"]),
    ]
    for tag, sec, cam_obj in beats:
        t0 = time.time()
        scene.frame_set(int(sec * FPS))
        scene.camera = cam_obj
        out_path = os.path.join(render_dir, f"{tag}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        print(f"Rendered {tag} (t={sec}s) -> {out_path} in {time.time() - t0:.2f}s")
    scene.camera = cams["classic_broadcast"]


if __name__ == "__main__":
    t_start = time.time()
    clear_scene()
    mats = build_all_materials()
    build_architecture_and_furniture(mats)
    build_and_animate_characters_and_press(mats)
    setup_lighting_and_world()
    cams = setup_cameras()
    export_glb_and_blend()
    if "--render-beats" in sys.argv:
        render_keyframe_beats(cams, res_x=1152, res_y=648, samples=40)
    print(f"=== COMPLETE ANIMATED BUILD FINISHED IN {time.time() - t_start:.2f}s ===")
