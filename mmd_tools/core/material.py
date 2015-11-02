# -*- coding: utf-8 -*-

import logging
import os

import bpy
import mmd_tools

SPHERE_MODE_OFF    = 0
SPHERE_MODE_MULT   = 1
SPHERE_MODE_ADD    = 2
SPHERE_MODE_SUBTEX = 3

class FnMaterial(object):
    BASE_TEX_SLOT = 0
    TOON_TEX_SLOT = 1
    SPHERE_TEX_SLOT = 2

    def __init__(self, material=None):
        self.__material = material

    @classmethod
    def from_material_id(cls, material_id):
        for material in bpy.data.materials:
            if material.mmd_material.material_id == material_id:
                return cls(material)
        return None

    @property
    def material_id(self):
        mmd_mat = self.__material.mmd_material
        if mmd_mat.material_id < 0:
            max_id = -1
            for mat in bpy.data.materials:
                max_id = max(max_id, mat.mmd_material.material_id)
            mmd_mat.material_id = max_id + 1
        return mmd_mat.material_id

    @property
    def material(self):
        return self.__material


    def __same_image_file(self, image, filepath):
        if image and image.source == 'FILE':
            img_filepath = image.filepath_from_user()
            if img_filepath == filepath:
                return True
            try:
                return os.path.samefile(img_filepath, filepath)
            except:
                pass
        return False

    def __load_image(self, filepath):
        for i in bpy.data.images:
            if self.__same_image_file(i, filepath):
                return i

        try:
            return bpy.data.images.load(filepath)
        except:
            logging.warning('Cannot create a texture for %s. No such file.', filepath)

        img = bpy.data.images.new(os.path.basename(filepath), 1, 1)
        img.source = 'FILE'
        img.filepath = filepath
        return img

    def __load_texture(self, filepath):
        for t in bpy.data.textures:
            if t.type == 'IMAGE' and self.__same_image_file(t.image, filepath):
                return t
        tex = bpy.data.textures.new(name=bpy.path.display_name_from_filepath(filepath), type='IMAGE')
        tex.image = self.__load_image(filepath)
        return tex


    def create_texture(self, filepath):
        """ create a texture slot for textures of MMD models.

        Args:
            material: the material object to add a texture_slot
            filepath: the file path to texture.

        Returns:
            bpy.types.MaterialTextureSlot object
        """
        texture_slot = self.__material.texture_slots.create(self.BASE_TEX_SLOT)
        texture_slot.use_map_alpha = True
        texture_slot.texture_coords = 'UV'
        texture_slot.blend_type = 'MULTIPLY'
        texture_slot.texture = self.__load_texture(filepath)
        return texture_slot


    def remove_texture(self, index=BASE_TEX_SLOT):
        texture_slot = self.__material.texture_slots[index]
        if texture_slot:
            tex = texture_slot.texture
            self.__material.texture_slots.clear(index)
            #print('clear texture: %s  users: %d'%(tex.name, tex.users))
            if tex and tex.users < 1:
                #print(' - remove texture: '+tex.name)
                img = tex.image
                tex.image = None
                bpy.data.textures.remove(tex)
                if img and img.users < 1:
                    #print('    - remove image: '+img.name)
                    bpy.data.images.remove(img)


    def create_sphere_texture(self, filepath):
        """ create a texture slot for environment mapping textures of MMD models.

        Args:
            material: the material object to add a texture_slot
            filepath: the file path to environment mapping texture.

        Returns:
            bpy.types.MaterialTextureSlot object
        """
        texture_slot = self.__material.texture_slots.create(self.SPHERE_TEX_SLOT)
        texture_slot.texture_coords = 'NORMAL'
        texture_slot.texture = self.__load_texture(filepath)
        texture_slot.texture.use_alpha = texture_slot.texture.image.use_alpha = False
        self.update_sphere_texture_type()
        return texture_slot

    def update_sphere_texture_type(self):
        texture_slot = self.__material.texture_slots[self.SPHERE_TEX_SLOT]
        if not texture_slot:
            return
        sphere_texture_type = int(self.__material.mmd_material.sphere_texture_type)
        if sphere_texture_type not in (1, 2, 3):
            texture_slot.use = False
        else:
            texture_slot.use = True
            texture_slot.blend_type = ('MULTIPLY', 'ADD', 'SUBTRACT')[sphere_texture_type-1]

    def remove_sphere_texture(self):
        self.remove_texture(self.SPHERE_TEX_SLOT)


    def create_toon_texture(self, filepath):
        """ create a texture slot for toon textures of MMD models.

        Args:
            material: the material object to add a texture_slot
            filepath: the file path to toon texture.

        Returns:
            bpy.types.MaterialTextureSlot object
        """
        texture_slot = self.__material.texture_slots.create(self.TOON_TEX_SLOT)
        texture_slot.texture_coords = 'NORMAL'
        texture_slot.blend_type = 'MULTIPLY'
        texture_slot.texture = self.__load_texture(filepath)
        texture_slot.texture.use_alpha = texture_slot.texture.image.use_alpha = False
        texture_slot.texture.extension = 'EXTEND'
        return texture_slot

    def update_toon_texture(self):
        mmd_mat = self.__material.mmd_material
        if mmd_mat.is_shared_toon_texture:
            shared_toon_folder = mmd_tools.addon_preferences('shared_toon_folder', '')
            toon_path = os.path.join(shared_toon_folder, 'toon%02d.bmp'%(mmd_mat.shared_toon_texture+1))
            self.create_toon_texture(bpy.path.resolve_ncase(path=toon_path))
        elif mmd_mat.toon_texture != '':
            self.create_toon_texture(mmd_mat.toon_texture)
        else:
            self.remove_toon_texture()

    def remove_toon_texture(self):
        self.remove_texture(self.TOON_TEX_SLOT)


    def update_drop_shadow(self):
        pass

    def update_self_shadow_map(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        mat.use_cast_buffer_shadows = mmd_mat.enabled_self_shadow_map # only buffer shadows
        if hasattr(mat, 'use_cast_shadows'):
            # "use_cast_shadows" is not supported in older Blender (< 2.71),
            # so we still use "use_cast_buffer_shadows".
            mat.use_cast_shadows = mmd_mat.enabled_self_shadow_map

    def update_self_shadow(self):
        mat = self.__material
        mmd_mat = mat.mmd_material
        mat.use_shadows = mmd_mat.enabled_self_shadow
        mat.use_transparent_shadows = mmd_mat.enabled_self_shadow

