"""
Material library for the Press Reception Hall 3D scene.
Uses Principled BSDF with packed PNG image textures so both Blender Cycles
and glTF (.glb) export preserve full PBR fidelity.
"""

import os
import bpy

TEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures")


def _load_image(filename: str, colorspace: str = "sRGB"):
    path = os.path.join(TEX_DIR, filename)
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = colorspace
    try:
        img.pack()
    except Exception:
        pass
    return img


def make_pbr_mat(
    name: str,
    base_color=(0.8, 0.8, 0.8, 1.0),
    tex_file: str = None,
    uv_scale=(1.0, 1.0),
    metallic: float = 0.0,
    roughness: float = 0.5,
    coat: float = 0.0,
    sheen: float = 0.0,
    subsurface: float = 0.0,
    alpha: float = 1.0,
    use_tex_alpha: bool = False,
    emission_color=None,
    emission_strength: float = 0.0,
):
    if name in bpy.data.materials:
        return bpy.data.materials[name]

    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")

    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    if "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = sheen
    if "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = subsurface
    bsdf.inputs["Alpha"].default_value = alpha

    if alpha < 1.0 or use_tex_alpha:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
        if hasattr(mat, "blend_method"):
            mat.blend_method = "BLEND"

    if emission_color is not None and emission_strength > 0.0:
        bsdf.inputs["Emission Color"].default_value = emission_color
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    if tex_file:
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = _load_image(tex_file)
        tex_node.location = (-360, 260)

        if uv_scale != (1.0, 1.0):
            uv_node = nodes.new("ShaderNodeTexCoord")
            uv_node.location = (-780, 260)
            map_node = nodes.new("ShaderNodeMapping")
            map_node.location = (-580, 260)
            map_node.inputs["Scale"].default_value = (uv_scale[0], uv_scale[1], 1.0)
            links.new(uv_node.outputs["UV"], map_node.inputs["Vector"])
            links.new(map_node.outputs["Vector"], tex_node.inputs["Vector"])

        links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
        if use_tex_alpha:
            links.new(tex_node.outputs["Alpha"], bsdf.inputs["Alpha"])

    return mat


def build_all_materials() -> dict:
    m = {}

    # Architecture & Flooring
    m["carpet"] = make_pbr_mat(
        "Mat_Carpet_Crimson",
        tex_file="carpet_albedo.png",
        roughness=0.88,
        sheen=0.65,
    )
    m["stone_cream"] = make_pbr_mat(
        "Mat_Stone_Travertine",
        base_color=(0.86, 0.81, 0.71, 1.0),
        roughness=0.18,
        coat=0.35,
    )
    m["stone_dark"] = make_pbr_mat(
        "Mat_Stone_Emperador",
        base_color=(0.18, 0.11, 0.08, 1.0),
        roughness=0.14,
        coat=0.45,
    )
    m["rosewood"] = make_pbr_mat(
        "Mat_Wood_Rosewood",
        tex_file="wood_rosewood_albedo.png",
        uv_scale=(2.0, 2.0),
        roughness=0.26,
        coat=0.50,
    )
    m["wall_silk"] = make_pbr_mat(
        "Mat_Wall_Silk_Brocade",
        tex_file="wall_silk_albedo.png",
        uv_scale=(6.0, 4.0),
        roughness=0.66,
        sheen=0.40,
    )
    m["plaster_cream"] = make_pbr_mat(
        "Mat_Plaster_Cream",
        base_color=(0.93, 0.90, 0.83, 1.0),
        roughness=0.55,
    )
    m["ceiling_white"] = make_pbr_mat(
        "Mat_Ceiling_Ivory",
        base_color=(0.95, 0.93, 0.88, 1.0),
        roughness=0.62,
    )
    m["gold_brass"] = make_pbr_mat(
        "Mat_Gold_Brass",
        base_color=(0.86, 0.68, 0.28, 1.0),
        metallic=0.92,
        roughness=0.22,
    )
    m["screen_art"] = make_pbr_mat(
        "Mat_Screen_Panels",
        tex_file="screen_panels.png",
        roughness=0.32,
        coat=0.38,
    )

    # Furniture & Props
    m["armchair_fabric"] = make_pbr_mat(
        "Mat_Armchair_Fabric",
        tex_file="fabric_armchair_albedo.png",
        uv_scale=(3.0, 3.0),
        roughness=0.78,
        sheen=0.50,
    )
    m["lace"] = make_pbr_mat(
        "Mat_Lace_Antimacassar",
        tex_file="lace_antimacassar.png",
        use_tex_alpha=True,
        roughness=0.85,
        sheen=0.30,
    )
    m["porcelain_cup"] = make_pbr_mat(
        "Mat_Porcelain_Cup",
        tex_file="porcelain_cup.png",
        roughness=0.08,
        coat=0.75,
    )
    m["porcelain_white"] = make_pbr_mat(
        "Mat_Porcelain_White",
        base_color=(0.96, 0.96, 0.97, 1.0),
        roughness=0.07,
        coat=0.80,
    )
    m["porcelain_cobalt"] = make_pbr_mat(
        "Mat_Porcelain_Cobalt",
        base_color=(0.11, 0.24, 0.56, 1.0),
        roughness=0.08,
        coat=0.82,
    )
    m["leaf_palm"] = make_pbr_mat(
        "Mat_Leaf_Palm",
        base_color=(0.024, 0.115, 0.030, 1.0),
        roughness=0.36,
        subsurface=0.10,
    )
    m["soil_dark"] = make_pbr_mat(
        "Mat_Soil_Dark",
        base_color=(0.04, 0.025, 0.018, 1.0),
        roughness=0.92,
    )
    m["flower_red"] = make_pbr_mat(
        "Mat_Flower_Red",
        base_color=(0.42, 0.018, 0.026, 1.0),
        roughness=0.52,
        sheen=0.35,
    )
    m["flower_gold"] = make_pbr_mat(
        "Mat_Flower_Gold",
        base_color=(0.68, 0.40, 0.035, 1.0),
        roughness=0.48,
    )

    # Emissive Lighting Fixtures
    m["crystal_glow"] = make_pbr_mat(
        "Mat_Crystal_Glow",
        base_color=(1.0, 0.92, 0.76, 1.0),
        roughness=0.08,
        emission_color=(1.0, 0.84, 0.56, 1.0),
        emission_strength=4.2,
    )
    m["cove_glow"] = make_pbr_mat(
        "Mat_Cove_WarmGlow",
        base_color=(1.0, 0.90, 0.72, 1.0),
        roughness=0.3,
        emission_color=(1.0, 0.85, 0.60, 1.0),
        emission_strength=1.5,
    )
    m["press_lamp"] = make_pbr_mat(
        "Mat_Press_LampGlow",
        base_color=(0.98, 0.99, 1.0, 1.0),
        roughness=0.05,
        emission_color=(0.96, 0.98, 1.0, 1.0),
        emission_strength=12.0,
    )

    # Characters & Attire (Physically accurate Linear RGB albedos!)
    m["skin_warm"] = make_pbr_mat(
        "Mat_Skin_Warm",
        base_color=(0.48, 0.29, 0.20, 1.0),
        roughness=0.46,
        subsurface=0.14,
    )
    m["skin_fair"] = make_pbr_mat(
        "Mat_Skin_Fair",
        base_color=(0.56, 0.36, 0.26, 1.0),
        roughness=0.44,
        subsurface=0.15,
    )
    m["lips_warm"] = make_pbr_mat(
        "Mat_Lips_Warm",
        base_color=(0.28, 0.09, 0.08, 1.0),
        roughness=0.38,
    )
    m["suit_charcoal_navy"] = make_pbr_mat(
        "Mat_Suit_CharcoalNavy",
        base_color=(0.018, 0.022, 0.034, 1.0),
        roughness=0.68,
        sheen=0.25,
    )
    m["suit_dark_navy"] = make_pbr_mat(
        "Mat_Suit_DarkNavy",
        base_color=(0.020, 0.030, 0.056, 1.0),
        roughness=0.68,
        sheen=0.24,
    )
    m["suit_slate_grey"] = make_pbr_mat(
        "Mat_Suit_SlateGrey",
        base_color=(0.068, 0.075, 0.088, 1.0),
        roughness=0.72,
        sheen=0.20,
    )
    m["suit_black"] = make_pbr_mat(
        "Mat_Suit_Black",
        base_color=(0.012, 0.013, 0.016, 1.0),
        roughness=0.66,
        sheen=0.20,
    )
    m["blazer_burgundy"] = make_pbr_mat(
        "Mat_Blazer_Burgundy",
        base_color=(0.14, 0.018, 0.028, 1.0),
        roughness=0.66,
        sheen=0.28,
    )
    m["jacket_olive"] = make_pbr_mat(
        "Mat_Jacket_Reporter",
        base_color=(0.09, 0.082, 0.062, 1.0),
        roughness=0.76,
    )
    m["shirt_white"] = make_pbr_mat(
        "Mat_Shirt_White",
        base_color=(0.82, 0.83, 0.86, 1.0),
        roughness=0.56,
    )
    m["blouse_cream"] = make_pbr_mat(
        "Mat_Blouse_Cream",
        base_color=(0.76, 0.71, 0.62, 1.0),
        roughness=0.50,
        sheen=0.22,
    )
    m["tie_crimson"] = make_pbr_mat(
        "Mat_Tie_Crimson",
        base_color=(0.36, 0.018, 0.026, 1.0),
        roughness=0.30,
        sheen=0.35,
    )
    m["tie_navy"] = make_pbr_mat(
        "Mat_Tie_Navy",
        base_color=(0.025, 0.055, 0.18, 1.0),
        roughness=0.32,
        sheen=0.30,
    )
    m["hair_dark"] = make_pbr_mat(
        "Mat_Hair_Dark",
        base_color=(0.012, 0.010, 0.009, 1.0),
        roughness=0.38,
    )
    m["hair_silver"] = make_pbr_mat(
        "Mat_Hair_SilverGrey",
        base_color=(0.34, 0.35, 0.38, 1.0),
        roughness=0.44,
    )
    m["glasses_frame"] = make_pbr_mat(
        "Mat_Glasses_BlackFrame",
        base_color=(0.02, 0.02, 0.025, 1.0),
        roughness=0.12,
        coat=0.65,
    )
    m["glasses_lens"] = make_pbr_mat(
        "Mat_Glasses_Lens",
        base_color=(0.82, 0.90, 0.95, 1.0),
        roughness=0.04,
        alpha=0.22,
    )
    m["leather_black"] = make_pbr_mat(
        "Mat_Leather_Black",
        base_color=(0.04, 0.04, 0.045, 1.0),
        roughness=0.30,
        coat=0.35,
    )

    # Press Equipment
    m["cam_body"] = make_pbr_mat(
        "Mat_Camera_Body",
        base_color=(0.09, 0.095, 0.105, 1.0),
        metallic=0.38,
        roughness=0.46,
    )
    m["cam_chrome"] = make_pbr_mat(
        "Mat_Metal_Chrome",
        base_color=(0.76, 0.78, 0.81, 1.0),
        metallic=0.90,
        roughness=0.22,
    )
    m["telephoto_white"] = make_pbr_mat(
        "Mat_Telephoto_OffWhite",
        base_color=(0.86, 0.85, 0.81, 1.0),
        metallic=0.20,
        roughness=0.30,
    )
    m["lens_glass"] = make_pbr_mat(
        "Mat_Lens_CoatedGlass",
        base_color=(0.05, 0.10, 0.24, 1.0),
        metallic=0.25,
        roughness=0.04,
        coat=0.90,
    )
    m["mic_foam"] = make_pbr_mat(
        "Mat_Mic_Foam",
        base_color=(0.11, 0.11, 0.12, 1.0),
        roughness=0.95,
    )
    m["boom_blimp"] = make_pbr_mat(
        "Mat_Boom_Windscreen",
        base_color=(0.34, 0.35, 0.37, 1.0),
        roughness=0.96,
        sheen=0.60,
    )
    m["mic_flags"] = make_pbr_mat(
        "Mat_Mic_Flags_Atlas",
        tex_file="mic_flags_atlas.png",
        roughness=0.35,
    )
    m["notepad_paper"] = make_pbr_mat(
        "Mat_Notepad_Paper",
        base_color=(0.95, 0.93, 0.86, 1.0),
        roughness=0.75,
    )

    return m
