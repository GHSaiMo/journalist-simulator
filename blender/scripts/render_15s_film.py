"""
Multi-camera cinematography & 7-shot 15-second (360 frames @ 24fps) edited short film
renderer for the Great Hall 3D scene (zero text anywhere).
Rebuilds the updated scene + GLB, animates 7 dedicated cinema cameras with continuous
follow-focus, subtle handheld ENG camera breathing, dynamic ENG spotlight tracking,
and SLR xenon strobe flashes, renders all 360 frames in one EEVEE session, and
encodes the final H.264 MP4 via ffmpeg.
"""

import os
import sys
import glob
import math
import time
import shutil
import subprocess
import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_DIR = BLENDER_DIR
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from materials_lib import build_all_materials
from arch_furniture import get_or_create_collection, build_architecture_and_furniture
from rigged_characters_anim import (
    build_and_animate_characters_and_press,
    eval_central_speaker_trajectory,
    FPS,
    TOTAL_FRAMES,
    smoother01,
)
from build_scene import clear_scene, setup_lighting_and_world, setup_cameras, export_glb_and_blend


def handheld_offset(t: float, amp_pos: float = 0.012, amp_tgt: float = 0.018):
    """Organic non-periodic ENG broadcast shoulder-camera breathing."""
    dx = amp_pos * (0.6 * math.sin(t * 2.1) + 0.4 * math.sin(t * 5.3 + 1.1))
    dy = amp_pos * (0.5 * math.cos(t * 1.7 + 0.4) + 0.3 * math.sin(t * 4.1))
    dz = amp_pos * (0.7 * math.sin(t * 2.7 + 2.0) + 0.3 * math.cos(t * 6.2))

    tx = amp_tgt * (0.6 * math.sin(t * 1.9 + 0.7) + 0.4 * math.cos(t * 4.7))
    tz = amp_tgt * (0.6 * math.cos(t * 2.4 + 1.5) + 0.35 * math.sin(t * 5.7))
    return Vector((dx, dy, dz)), Vector((tx, 0.0, tz))


def animate_dynamic_scene_lights():
    """Keyframes the ENG camera spotlight tracking & SLR photojournalist strobe flashes."""
    col_light = get_or_create_collection("05_Lighting")
    eng_key = bpy.data.objects.get("Light_ENG_Cam1_Key")

    # Add Xenon SLR Camera Strobe Point Light right at photojournalist position
    strobe_data = bpy.data.lights.new(name="Light_SLR_Strobe_Data", type="POINT")
    strobe_data.color = (0.95, 0.98, 1.0)
    strobe_data.shadow_soft_size = 0.08
    strobe_data.energy = 0.0
    strobe_obj = bpy.data.objects.new("Light_SLR_Strobe", strobe_data)
    strobe_obj.location = (0.62, -1.25, 1.70)
    col_light.objects.link(strobe_obj)

    flash_frames = {178, 418, 446}

    for f in range(0, TOTAL_FRAMES + 1):
        t = (f % TOTAL_FRAMES) / float(FPS)
        st = eval_central_speaker_trajectory(t)
        head_z = 1.48 - 0.36 * st["sit_s"]

        if eng_key and f % 2 == 0:
            tgt = Vector((st["rx"], st["ry"], head_z))
            direction = tgt - eng_key.location
            eng_key.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
            eng_key.keyframe_insert(data_path="rotation_euler", frame=f)

        # Crisp 2-frame xenon flash spike
        if f in flash_frames:
            strobe_data.energy = 780.0
        elif (f - 1) in flash_frames:
            strobe_data.energy = 190.0
        else:
            strobe_data.energy = 0.0

        if f in flash_frames or (f - 1) in flash_frames or (f - 2) in flash_frames or (f + 1) in flash_frames or f == 0:
            strobe_data.keyframe_insert(data_path="energy", frame=f)


def build_seven_editorial_shots():
    """
    Creates 7 choreographed cinema cameras with continuous follow-focus,
    lens zooms, dolly/tracking moves, and ENG handheld micro-sway.
    Total = 52 + 50 + 52 + 48 + 68 + 40 + 50 = 360 frames (15.00s @ 24fps).
    """
    col_edit = get_or_create_collection("07_Editorial_Cut_Cameras")

    shot_specs = [
        {
            "id": "shot01_pushin_question",
            "f_start": 34,
            "f_end": 85,  # 52 frames (2.17s): Dolly push-in past teacup -> reporter mic & head shake
            "p0": Vector((1.92, 0.50, 1.08)),
            "p1": Vector((1.38, 1.05, 1.15)),
            "t0": Vector((-0.45, 1.95, 1.12)),
            "t1": Vector((-0.78, 2.58, 1.15)),
            "lens0": 42.0,
            "lens1": 45.0,
            "fstop": 3.0,
            "handheld": 0.003,
        },
        {
            "id": "shot02_standup_stride",
            "f_start": 86,
            "f_end": 135,  # 50 frames (2.08s): Low-angle tracking rise from armchair & stride forward
            "p0": Vector((-1.68, 0.92, 1.12)),
            "p1": Vector((-1.98, 0.08, 1.30)),
            "track_speaker": True,
            "tgt_z_off": -0.10,
            "lens0": 34.0,
            "lens1": 34.0,
            "fstop": 3.8,
            "handheld": 0.006,
        },
        {
            "id": "shot03_reverse_press_flash",
            "f_start": 164,
            "f_end": 215,  # 52 frames (2.17s): Reverse OTS sweeping past waving hands into press mics & flash!
            "p0": Vector((-0.96, 2.15, 1.68)),
            "p1": Vector((-0.48, 2.22, 1.65)),
            "t0": Vector((0.08, -0.55, 1.34)),
            "t1": Vector((-0.08, -0.65, 1.36)),
            "lens0": 30.0,
            "lens1": 32.0,
            "fstop": 3.6,
            "handheld": 0.005,
        },
        {
            "id": "shot04_closeup_elder",
            "f_start": 314,
            "f_end": 361,  # 48 frames (2.00s): Intimate 58mm f/2.6 close-up hands-to-chest & earnest nod
            "p0": Vector((-0.24, -0.45, 1.54)),
            "p1": Vector((-0.36, -0.40, 1.55)),
            "track_speaker": True,
            "tgt_z_off": 0.04,
            "lens0": 56.0,
            "lens1": 60.0,
            "fstop": 2.8,
            "handheld": 0.010,
        },
        {
            "id": "shot05_climax_point_zoom",
            "f_start": 398,
            "f_end": 465,  # 68 frames (2.83s): Iconic broadcast shot + live ENG zoom-in on wagging finger + 2 flashes!
            "p0": Vector((-0.08, -1.48, 1.58)),
            "p1": Vector((-0.06, -1.44, 1.58)),
            "t0": Vector((-0.18, 1.32, 1.36)),
            "t1": Vector((-0.12, 1.15, 1.44)),
            "lens0": 36.0,
            "lens1": 45.0,
            "fstop": 3.5,
            "handheld": 0.011,
        },
        {
            "id": "shot06_wide_chandelier_spread",
            "f_start": 468,
            "f_end": 507,  # 40 frames (1.67s): Wide chandelier confrontation cut as both arms fling wide open!
            "p0": Vector((-4.28, -0.30, 1.84)),
            "p1": Vector((-3.92, 0.18, 1.94)),
            "t0": Vector((0.05, 0.90, 1.38)),
            "t1": Vector((0.10, 0.95, 1.42)),
            "lens0": 24.0,
            "lens1": 25.0,
            "fstop": 5.0,
            "handheld": 0.003,
        },
        {
            "id": "shot07_pullback_departure",
            "f_start": 608,
            "f_end": 657,  # 50 frames (2.08s): Slow pull-back through press shoulders as he turns & walks back to chair
            "p0": Vector((0.04, -1.12, 1.50)),
            "p1": Vector((0.02, -1.86, 1.58)),
            "track_speaker": True,
            "tgt_z_off": -0.06,
            "lens0": 40.0,
            "lens1": 38.0,
            "fstop": 3.4,
            "handheld": 0.005,
        },
    ]

    shots = []
    for sp in shot_specs:
        cdata = bpy.data.cameras.new(name=sp["id"] + "_Data")
        cdata.clip_start = 0.08
        cdata.clip_end = 80.0
        cdata.dof.use_dof = True
        cdata.dof.aperture_fstop = sp["fstop"]

        cobj = bpy.data.objects.new(sp["id"] + "_Cam", cdata)
        col_edit.objects.link(cobj)

        f0, f1 = sp["f_start"], sp["f_end"]
        span = max(f1 - f0, 1)

        # Keyframe 1 frame before f0 and 1 frame after f1 too so motion-blur shutter at boundaries is smooth!
        for f in range(max(0, f0 - 1), min(TOTAL_FRAMES, f1 + 1) + 1):
            u = smoother01((f - f0) / float(span))
            t = f / float(FPS)

            cam_loc = sp["p0"].lerp(sp["p1"], u)
            if sp.get("track_speaker"):
                st = eval_central_speaker_trajectory(t)
                sp_z = (1.46 - 0.34 * st["sit_s"]) + sp.get("tgt_z_off", 0.0)
                tgt = Vector((st["rx"], st["ry"], sp_z))
            else:
                tgt = sp["t0"].lerp(sp["t1"], u)

            hh_p, hh_t = handheld_offset(t, sp["handheld"], sp["handheld"] * 1.4)
            final_loc = cam_loc + hh_p
            final_tgt = tgt + hh_t

            cobj.location = final_loc
            direction = final_tgt - final_loc
            cobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

            cdata.lens = sp["lens0"] + (sp["lens1"] - sp["lens0"]) * u
            cdata.dof.focus_distance = max(0.5, direction.length)

            cobj.keyframe_insert(data_path="location", frame=f)
            cobj.keyframe_insert(data_path="rotation_euler", frame=f)
            cdata.keyframe_insert(data_path="lens", frame=f)
            cdata.dof.keyframe_insert(data_path="focus_distance", frame=f)

        shots.append((sp, cobj))

    return shots


def render_and_encode_15s_mp4(shots, res_x: int = 1280, res_y: int = 720, samples: int = 16):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.fps = FPS
    scene.render.image_settings.file_format = "PNG"

    if hasattr(scene.eevee, "taa_samples"):
        scene.eevee.taa_samples = samples
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = False
    if hasattr(scene.eevee, "shadow_ray_count"):
        scene.eevee.shadow_ray_count = 1
    if hasattr(scene.eevee, "shadow_step_count"):
        scene.eevee.shadow_step_count = 4

    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.35

    available_vt = [e.identifier for e in scene.view_settings.bl_rna.properties["view_transform"].enum_items]
    if "AgX" in available_vt:
        scene.view_settings.view_transform = "AgX"
        available_looks = [e.identifier for e in scene.view_settings.bl_rna.properties["look"].enum_items]
        if "AgX - Medium High Contrast" in available_looks:
            scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.15

    frames_root = os.path.join(PROJECT_DIR, "renders", "film_15s_frames")
    if os.path.exists(frames_root):
        shutil.rmtree(frames_root)
    os.makedirs(frames_root, exist_ok=True)

    seq_dir = os.path.join(frames_root, "assembled")
    os.makedirs(seq_dir, exist_ok=True)
    global_idx = 1

    for sp, cam_obj in shots:
        shot_dir = os.path.join(frames_root, sp["id"])
        os.makedirs(shot_dir, exist_ok=True)
        scene.camera = cam_obj
        scene.frame_start = sp["f_start"]
        scene.frame_end = sp["f_end"]
        scene.render.filepath = os.path.join(shot_dir, "f_")

        t0 = time.time()
        bpy.ops.render.render(animation=True)
        dt = time.time() - t0

        rendered_pngs = sorted(glob.glob(os.path.join(shot_dir, "f_*.png")))
        for p in rendered_pngs:
            dst = os.path.join(seq_dir, f"frame_{global_idx:04d}.png")
            shutil.move(p, dst)
            global_idx += 1
        print(f"[FILM] {sp['id']}: {len(rendered_pngs)} frames rendered in {dt:.2f}s ({dt/max(len(rendered_pngs),1):.3f}s/f)")

    total_rendered = global_idx - 1
    print(f"[FILM] Total assembled frames: {total_rendered} ({total_rendered / float(FPS):.2f}s)")

    out_mp4 = os.path.join(BLENDER_DIR, "exports", "press_hall_15s_cut.mp4")
    fade_out_start = max(0.0, (total_rendered / float(FPS)) - 0.55)
    vf = f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start:.2f}:d=0.55,format=yuv420p"

    cmd = [
        "/opt/homebrew/bin/ffmpeg",
        "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(seq_dir, "frame_%04d.png"),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "17",
        "-movflags", "+faststart",
        out_mp4,
    ]
    subprocess.run(cmd, check=True)
    print(f"[FILM] Encoded H.264 MP4 -> {out_mp4} ({os.path.getsize(out_mp4)/1024/1024:.2f} MB)")


if __name__ == "__main__":
    t_all = time.time()
    clear_scene()
    mats = build_all_materials()
    build_architecture_and_furniture(mats)
    build_and_animate_characters_and_press(mats)
    setup_lighting_and_world()
    cams = setup_cameras()
    export_glb_and_blend()

    animate_dynamic_scene_lights()
    shots = build_seven_editorial_shots()
    render_and_encode_15s_mp4(shots, res_x=1280, res_y=720, samples=16)

    # Restore full 0..768 timeline & save .blend with all 7 editorial cameras included too!
    bpy.context.scene.frame_start = 0
    bpy.context.scene.frame_end = TOTAL_FRAMES
    bpy.context.scene.frame_set(int(18.0 * FPS))
    bpy.context.scene.camera = cams["classic_broadcast"]
    bpy.context.scene.cycles.device = "GPU"
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLENDER_DIR, "press_hall.blend"), compress=True)
    print(f"=== COMPLETE 15S FILM PIPELINE FINISHED IN {time.time() - t_all:.2f}s ===")
