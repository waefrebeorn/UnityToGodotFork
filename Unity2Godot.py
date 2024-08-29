import os
import yaml
import json
import struct
import base64
from PIL import Image
from godot_parser import GDScene, Node, Property, ExtResource

class UnityToGodotConverter:
    def __init__(self, unity_project_path, godot_project_path):
        self.unity_project_path = unity_project_path
        self.godot_project_path = godot_project_path
        self.prefabs = {}
        self.materials = {}
        self.meshes = {}
        self.animations = {}
        self.scripts = {}
        self.asset_map = {}
        self.unity_types_to_godot = {
            "Transform": "Node3D",
            "MeshRenderer": "MeshInstance3D",
            "Camera": "Camera3D",
            "Light": "Light3D",
            "Rigidbody": "RigidBody3D",
            "BoxCollider": "CollisionShape3D",
            "SphereCollider": "CollisionShape3D",
            "CapsuleCollider": "CollisionShape3D",
            "Canvas": "CanvasLayer",
            "RectTransform": "Control",
            "Image": "TextureRect",
            "Text": "Label",
            "Button": "Button",
            "ParticleSystem": "GPUParticles3D",
        }

    def convert_project(self):
        self.analyze_project_structure()
        self.convert_assets()
        self.convert_scenes()
        self.convert_prefabs()
        self.update_asset_references()

    def analyze_project_structure(self):
        for root, _, files in os.walk(self.unity_project_path):
            for file in files:
                if file.endswith(".prefab"):
                    self.analyze_prefab(os.path.join(root, file))
                elif file.endswith(".mat"):
                    self.analyze_material(os.path.join(root, file))
                elif file.endswith(".fbx") or file.endswith(".obj"):
                    self.analyze_mesh(os.path.join(root, file))
                elif file.endswith(".anim"):
                    self.analyze_animation(os.path.join(root, file))
                elif file.endswith(".cs"):
                    self.analyze_script(os.path.join(root, file))

    def analyze_prefab(self, prefab_path):
        prefab_name = os.path.splitext(os.path.basename(prefab_path))[0]
        self.prefabs[prefab_name] = prefab_path

    def analyze_material(self, material_path):
        material_name = os.path.splitext(os.path.basename(material_path))[0]
        self.materials[material_name] = material_path

    def analyze_mesh(self, mesh_path):
        mesh_name = os.path.splitext(os.path.basename(mesh_path))[0]
        self.meshes[mesh_name] = mesh_path

    def analyze_animation(self, animation_path):
        animation_name = os.path.splitext(os.path.basename(animation_path))[0]
        self.animations[animation_name] = animation_path

    def analyze_script(self, script_path):
        script_name = os.path.splitext(os.path.basename(script_path))[0]
        self.scripts[script_name] = script_path

    def convert_assets(self):
        self.convert_materials()
        self.convert_meshes()
        self.convert_animations()
        self.convert_scripts()

    def convert_materials(self):
        for material_name, material_path in self.materials.items():
            godot_material_path = os.path.join(self.godot_project_path, "materials", f"{material_name}.tres")
            os.makedirs(os.path.dirname(godot_material_path), exist_ok=True)
            
            with open(material_path, 'r') as f:
                material_data = yaml.safe_load(f)
            
            material = GDScene()
            material.add_node(Node("SpatialMaterial", name="material"))
            
            self.convert_material_properties(material_data, material.nodes[-1])
            
            material.write(godot_material_path)
            
            self.asset_map[material_path] = godot_material_path

    def convert_material_properties(self, unity_material, godot_material):
        if 'Color' in unity_material:
            color = unity_material['Color']
            godot_material.add_property("albedo_color", Property("Color", f"Color({color['r']}, {color['g']}, {color['b']}, {color['a']})"))
        
        if 'Metallic' in unity_material:
            godot_material.add_property("metallic", Property("float", str(unity_material['Metallic'])))
        
        if 'Smoothness' in unity_material:
            godot_material.add_property("roughness", Property("float", str(1 - unity_material['Smoothness'])))
        
        self.convert_texture_map(unity_material, godot_material, 'MainTex', 'albedo_texture')
        self.convert_texture_map(unity_material, godot_material, 'BumpMap', 'normal_texture')
        self.convert_texture_map(unity_material, godot_material, 'MetallicGlossMap', 'metallic_texture')

    def convert_texture_map(self, unity_material, godot_material, unity_prop, godot_prop):
        if unity_prop in unity_material:
            texture_path = unity_material[unity_prop]['Texture']
            godot_texture_path = self.convert_texture(texture_path)
            godot_material.add_property(godot_prop, Property("ExtResource", f'ExtResource("{godot_texture_path}")'))

    def convert_texture(self, unity_texture_path):
        godot_texture_path = os.path.join(self.godot_project_path, "textures", os.path.basename(unity_texture_path))
        os.makedirs(os.path.dirname(godot_texture_path), exist_ok=True)
        
        with Image.open(unity_texture_path) as img:
            img.save(godot_texture_path)
        
        return godot_texture_path

    def convert_meshes(self):
        for mesh_name, mesh_path in self.meshes.items():
            godot_mesh_path = os.path.join(self.godot_project_path, "meshes", f"{mesh_name}.mesh")
            os.makedirs(os.path.dirname(godot_mesh_path), exist_ok=True)
            
            self.placeholder_mesh_conversion(mesh_path, godot_mesh_path)
            
            self.asset_map[mesh_path] = godot_mesh_path

    def placeholder_mesh_conversion(self, unity_mesh_path, godot_mesh_path):
        print(f"Converting mesh: {unity_mesh_path} to {godot_mesh_path}")
        vertices = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)
        ]
        indices = [
            0, 1, 2, 2, 3, 0,  # Front
            1, 5, 6, 6, 2, 1,  # Right
            5, 4, 7, 7, 6, 5,  # Back
            4, 0, 3, 3, 7, 4,  # Left
            3, 2, 6, 6, 7, 3,  # Top
            4, 5, 1, 1, 0, 4   # Bottom
        ]
        with open(godot_mesh_path, 'wb') as f:
            f.write(struct.pack('<I', len(vertices)))
            for v in vertices:
                f.write(struct.pack('<fff', *v))
            f.write(struct.pack('<I', len(indices)))
            for i in indices:
                f.write(struct.pack('<I', i))

    def convert_animations(self):
        for anim_name, anim_path in self.animations.items():
            godot_anim_path = os.path.join(self.godot_project_path, "animations", f"{anim_name}.anim")
            os.makedirs(os.path.dirname(godot_anim_path), exist_ok=True)
            
            with open(anim_path, 'r') as f:
                anim_data = yaml.safe_load(f)
            
            animation = GDScene()
            animation.add_node(Node("Animation", name="animation"))
            
            self.convert_animation_data(anim_data, animation.nodes[-1])
            
            animation.write(godot_anim_path)
            
            self.asset_map[anim_path] = godot_anim_path

    def convert_animation_data(self, unity_anim, godot_anim):
        godot_anim.add_property("length", Property("float", str(unity_anim.get('length', 1.0))))
        godot_anim.add_property("loop", Property("bool", str(unity_anim.get('loop', False)).lower()))
        
        for track in unity_anim.get('tracks', []):
            self.convert_animation_track(track, godot_anim)

    def convert_animation_track(self, unity_track, godot_anim):
        track_node = Node("Track", name=unity_track['path'])
        godot_anim.add_child(track_node)
        
        track_node.add_property("type", Property("String", "transform"))
        track_node.add_property("path", Property("NodePath", unity_track['path']))
        
        keys_node = Node("Keys")
        track_node.add_child(keys_node)
        
        for i, key in enumerate(unity_track['keys']):
            key_node = Node(f"Key{i}")
            keys_node.add_child(key_node)
            key_node.add_property("time", Property("float", str(key['time'])))
            key_node.add_property("transform", Property("Transform", self.convert_transform(key['value'])))

    def convert_transform(self, unity_transform):
        position = unity_transform.get('position', [0, 0, 0])
        rotation = unity_transform.get('rotation', [0, 0, 0, 1])
        scale = unity_transform.get('scale', [1, 1, 1])
        return f"Transform(Vector3({scale[0]}, {scale[1]}, {scale[2]}), Quat({rotation[0]}, {rotation[1]}, {rotation[2]}, {rotation[3]}), Vector3({position[0]}, {position[1]}, {position[2]}))"

    def convert_scripts(self):
        for script_name, script_path in self.scripts.items():
            godot_script_path = os.path.join(self.godot_project_path, "scripts", f"{script_name}.gd")
            os.makedirs(os.path.dirname(godot_script_path), exist_ok=True)
            
            self.convert_csharp_to_gdscript(script_path, godot_script_path)
            
            self.asset_map[script_path] = godot_script_path

    def convert_csharp_to_gdscript(self, csharp_path, gdscript_path):
        print(f"Converting script: {csharp_path} to {gdscript_path}")
        with open(csharp_path, 'r') as csharp_file, open(gdscript_path, 'w') as gdscript_file:
            csharp_content = csharp_file.read()
            gdscript_content = f"# Converted from {os.path.basename(csharp_path)}\n\nextends Node\n\n# TODO: Convert C# code to GDScript\n\n# Original C# code:\n'''\n{csharp_content}\n'''"
            gdscript_file.write(gdscript_content)

    def convert_scenes(self):
        for root, _, files in os.walk(os.path.join(self.unity_project_path, "Assets")):
            for file in files:
                if file.endswith(".unity"):
                    unity_scene_path = os.path.join(root, file)
                    relative_path = os.path.relpath(unity_scene_path, self.unity_project_path)
                    godot_scene_path = os.path.join(self.godot_project_path, "scenes", relative_path.replace(".unity", ".tscn"))
                    os.makedirs(os.path.dirname(godot_scene_path), exist_ok=True)
                    
                    self.convert_scene(unity_scene_path, godot_scene_path)

    def convert_scene(self, unity_scene_path, godot_scene_path):
        with open(unity_scene_path, 'r') as f:
            unity_scene = yaml.safe_load(f)
        
        godot_scene = GDScene()
        root_node = Node("Node3D", name="Scene")
        godot_scene.add_node(root_node)
        
        for game_object in unity_scene.get('GameObjects', []):
            self.convert_game_object(game_object, root_node)
        
        godot_scene.write(godot_scene_path)

    def convert_game_object(self, game_object, parent_node):
        node_type = self.determine_node_type(game_object)
        node_name = game_object.get('Name', 'GameObject')
        node = Node(node_type, name=node_name)
        
        self.convert_transform(game_object, node)
        
        for component in game_object.get('Components', []):
            self.convert_component(component, node)
        
        parent_node.add_child(node)
        
        for child in game_object.get('Children', []):
            self.convert_game_object(child, node)

    def determine_node_type(self, game_object):
        for component in game_object.get('Components', []):
            component_type = component.get('Type')
            if component_type in self.unity_types_to_godot:
                return self.unity_types_to_godot[component_type]
        return "Node3D"

    def convert_component(self, component, node):
        component_type = component.get('Type')
        if component_type == "MeshFilter":
            self.convert_mesh_filter(component, node)
        elif component_type == "MeshRenderer":
            self.convert_mesh_renderer(component, node)
        elif component_type == "Camera":
            self.convert_camera(component, node)
        elif component_type == "Light":
            self.convert_light(component, node)
        elif component_type == "Rigidbody":
            self.convert_rigidbody(component, node)
        elif component_type in ["BoxCollider", "SphereCollider", "CapsuleCollider"]:
            self.convert_collider(component, node)
        elif component_type == "ParticleSystem":
            self.convert_particle_system(component, node)
        elif component_type == "Canvas":
            self.convert_canvas(component, node)
        elif component_type == "RectTransform":
            self.convert_rect_transform(component, node)
        elif component_type == "MonoBehaviour":
            self.convert_script_component(component, node)
        else:
            print(f"Unhandled component type: {component_type}")

    def convert_mesh_filter(self, component, node):
        mesh_path = component.get('Mesh', {}).get('Path')
        if mesh_path:
            godot_mesh_path = self.asset_map.get(mesh_path)
            if godot_mesh_path:
                node.add_property("mesh", Property("ExtResource", f'ExtResource("{godot_mesh_path}")'))

    def convert_mesh_renderer(self, component, node):
        materials = component.get('Materials', [])
        for i, material in enumerate(materials):
            material_path = material.get('Path')
            if material_path:
                godot_material_path = self.asset_map.get(material_path)
                if godot_material_path:
                    node.add_property(f"material_{i}", Property("ExtResource", f'ExtResource("{godot_material_path}")'))

    def convert_camera(self, component, node):
        node.add_property("fov", Property("float", str(component.get('FieldOfView', 60))))
        node.add_property("near", Property("float", str(component.get('NearClipPlane', 0.3))))
        node.add_property("far", Property("float", str(component.get('FarClipPlane', 1000))))

    def convert_light(self, component, node):
        light_type = component.get('Type', 'Point')
        if light_type == 'Directional':
            node.type = "DirectionalLight3D"
        elif light_type == 'Spot':
            node.type = "SpotLight3D"
        else:
            node.type = "OmniLight3D"

        color = component.get('Color', {'r': 1, 'g': 1, 'b': 1, 'a': 1})
        node.add_property("light_color", Property("Color", f"Color({color['r']}, {color['g']}, {color['b']}, {color['a']})"))
        node.add_property("light_energy", Property("float", str(component.get('Intensity', 1))))

    def convert_rigidbody(self, component, node):
        node.add_property("mass", Property("float", str(component.get('Mass', 1))))
        node.add_property("gravity_scale", Property("float", "1.0" if component.get('UseGravity', True) else "0.0"))
        if component.get('IsKinematic', False):
            node.type = "AnimatableBody3D"

    def convert_collider(self, component, node):
        collider_node = Node("CollisionShape3D", name="Collider")
        node.add_child(collider_node)

        shape_type = component['Type']
        if shape_type == "BoxCollider":
            shape = "BoxShape3D"
            size = component.get('Size', {'x': 1, 'y': 1, 'z': 1})
            shape_params = f"size = Vector3({size['x']}, {size['y']}, {size['z']})"
        elif shape_type == "SphereCollider":
            shape = "SphereShape3D"
            radius = component.get('Radius', 0.5)
            shape_params = f"radius = {radius}"
        elif shape_type == "CapsuleCollider":
            shape = "CapsuleShape3D"
            radius = component.get('Radius', 0.5)
            height = component.get('Height', 2)
            shape_params = f"radius = {radius}, height = {height}"

        collider_node.add_property("shape", Property("Shape3D", f"{shape}.new({shape_params})"))

    def convert_particle_system(self, component, node):
        node.add_property("amount", Property("int", str(component.get('MaxParticles', 1000))))
        node.add_property("lifetime", Property("float", str(component.get('StartLifetime', 5))))
        node.add_property("explosiveness", Property("float", "0.0"))
        node.add_property("randomness", Property("float", "0.0"))

        # TODO: Convert more particle system properties

    def convert_canvas(self, component, node):
        node.add_property("layer", Property("int", str(component.get('RenderMode', 0))))
        
        scaler = component.get('CanvasScaler', {})
        if scaler:
            node.add_property("scale_mode", Property("int", str(scaler.get('ScaleMode', 0))))
            ref_res = scaler.get('ReferenceResolution', {'x': 800, 'y': 600})
            node.add_property("reference_resolution", Property("Vector2", f"Vector2({ref_res['x']}, {ref_res['y']})"))

    def convert_rect_transform(self, component, node):
        anchors = component.get('Anchors', {'min': {'x': 0, 'y': 0}, 'max': {'x': 1, 'y': 1}})
        node.add_property("anchor_left", Property("float", str(anchors['min']['x'])))
        node.add_property("anchor_top", Property("float", str(anchors['min']['y'])))
        node.add_property("anchor_right", Property("float", str(anchors['max']['x'])))
        node.add_property("anchor_bottom", Property("float", str(anchors['max']['y'])))

        # TODO: Convert more RectTransform properties

    def convert_script_component(self, component, node):
        script_path = component.get('Script', {}).get('Path')
        if script_path:
            godot_script_path = self.asset_map.get(script_path)
            if godot_script_path:
                node.add_property("script", Property("ExtResource", f'ExtResource("{godot_script_path}")'))

    def convert_prefabs(self):
        for prefab_name, prefab_path in self.prefabs.items():
            godot_scene_path = os.path.join(self.godot_project_path, "prefabs", f"{prefab_name}.tscn")
            os.makedirs(os.path.dirname(godot_scene_path), exist_ok=True)
            
            with open(prefab_path, 'r') as f:
                prefab_data = yaml.safe_load(f)
            
            godot_scene = GDScene()
            root_node = Node("Node3D", name=prefab_name)
            godot_scene.add_node(root_node)
            
            self.convert_game_object(prefab_data, root_node)
            
            godot_scene.write(godot_scene_path)
            
            self.asset_map[prefab_path] = godot_scene_path

    def update_asset_references(self):
        for root, _, files in os.walk(self.godot_project_path):
            for file in files:
                if file.endswith(".tscn") or file.endswith(".tres"):
                    file_path = os.path.join(root, file)
                    self.update_file_references(file_path)

    def update_file_references(self, file_path):
        with open(file_path, 'r') as f:
            content = f.read()

        for unity_path, godot_path in self.asset_map.items():
            unity_filename = os.path.basename(unity_path)
            godot_filename = os.path.basename(godot_path)
            content = content.replace(unity_filename, godot_filename)

        with open(file_path, 'w') as f:
            f.write(content)

    def run(self):
        print("Starting Unity to Godot conversion...")
        self.convert_project()
        print("Conversion complete!")

if __name__ == "__main__":
    unity_project_path = input("Enter the path to your Unity project: ")
    godot_project_path = input("Enter the path for the new Godot project: ")
    converter = UnityToGodotConverter(unity_project_path, godot_project_path)
    converter.run()
