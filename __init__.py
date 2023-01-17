
bl_info = {
	'name': 'Blender Hobo',
	'author': 'MrKleiner',
	'version': (0, 19),
	'blender': (3, 4, 0),
	'location': 'N menu',
	'description': """Fit more dicks in VRAM's throat at the cost of texture quality""",
	'warning': 'You suck',
	'doc_url': '',
	'category': 'Add Mesh',
}

# hobo_name = bl_info['name']


import bpy

import hashlib, random, mathutils, time, datetime, subprocess, shutil, sys, os, json, math, re

from bpy.types import Operator
from bpy.props import FloatVectorProperty
from bpy_extras.object_utils import AddObjectHelper, object_data_add

from pathlib import Path

from bpy.props import (StringProperty,
					   BoolProperty,
					   IntProperty,
					   FloatProperty,
					   FloatVectorProperty,
					   EnumProperty,
					   PointerProperty,
					   )
from bpy.types import (Panel,
					   Operator,
					   AddonPreferences,
					   PropertyGroup,
					   )

addon_root_dir = Path(__file__).absolute().parent

# dumpst_dir = Path(bpy.context.preferences.addons[__package__].preferences.dumpster_path)
# print(dir(bpy.context.preferences.addons[__package__].preferences))
print(bpy.context.preferences.addons[__package__].preferences)
# print(bpy.context.preferences.addons[__name__])
# print(list(bpy.context.preferences.addons.keys()))
# print(list(bpy.context.preferences.addons[__name__].keys()))
print(__package__)
print('FUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU')
print('FUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU')
print('FUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU')
print('FUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU')
print('FUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU')
print('FUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU')
print('FUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUUU')













# =========================================================
# ---------------------------------------------------------
#                       Actual shit
# ---------------------------------------------------------
# =========================================================

def hobo_exec_opt(self, context):
	print('You hobo')























# =========================================================
# ---------------------------------------------------------
#                       Operator Links
# ---------------------------------------------------------
# =========================================================

class OBJECT_OT_hobo_exec_opt(Operator, AddObjectHelper):
	bl_idname = 'mesh.hobo_optimize'
	bl_label = 'Opt Hobo'
	bl_options = {'REGISTER'}

	def execute(self, context):
		hobo_exec_opt(self, context)
		return {'FINISHED'}


















# =========================================================
# ---------------------------------------------------------
#                   Property declarations
# ---------------------------------------------------------
# =========================================================


class blender_hobo_image_property_declaration(PropertyGroup):
	do_convert : BoolProperty(
		name='Convert',
		description='Whether to convert the image or not',
		default=True
	)
		


class blender_hobo_scene_property_declaration(PropertyGroup):
	as_exclusion : BoolProperty(
		name='Exclusion',
		description=""" When checked - Individual images have to be excluded from conversion.
		When UNchecked - individual images have to be marked for conversion.
		Go to the Hobo panel in the Image Editor/Node Editor panel and look for a self-explanatory checkbox""",
		default=True
	)



class blender_hobo_addon_prefs(bpy.types.AddonPreferences):
	bl_idname = __package__

	dumpster_path : StringProperty(
		name='Dumpster Location',
		description='Path to the directory to put converted textures to',
		default = '',
		subtype='DIR_PATH'
	)

	def draw(self, context):
		layout = self.layout
		row = layout.row()
		row.prop(self, 'dumpster_path', expand=True)






















# =========================================================
# ---------------------------------------------------------
#                          GUI
# ---------------------------------------------------------
# =========================================================


#
# Scene
#
class VIEW3D_PT_blender_hobo_scene_params_gui(bpy.types.Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'Lizards'
	bl_label = 'Hobo'
	# https://youtu.be/sT3joXENOb0

	def draw(self, context):
		layout = self.layout
		
		dumpster = layout.column(align=True)
		# dumpster.use_property_split = True
		# dumpster.use_property_decorate = False


		dumpster.operator('mesh.hobo_optimize',
			text='I want my scene to look rubbish'
		)
		dumpster.label(text=' ')
		dumpster.prop(context.scene.hobo_config, 'as_exclusion')




#
# Image Editor
#
class IMAGE_EDITOR_PT_blender_hobo_image_params_gui(bpy.types.Panel):
	bl_space_type = 'IMAGE_EDITOR'
	bl_region_type = 'UI'
	bl_category = 'Lizards'
	bl_label = 'Hobo'
	# https://youtu.be/sT3joXENOb0

	def draw(self, context):
		layout = self.layout
		
		dumpster = layout.column(align=True)
		# dumpster.use_property_split = True
		# dumpster.use_property_decorate = False

		dumpster.prop(context.space_data.image.hobo_image_params, 'do_convert', text=('Exclude' if context.scene.hobo_config.as_exclusion else 'Include'))




















































# =========================================================
# ---------------------------------------------------------
#                       Register
# ---------------------------------------------------------
# =========================================================


rclasses = (
	OBJECT_OT_hobo_exec_opt,
	IMAGE_EDITOR_PT_blender_hobo_image_params_gui,
	VIEW3D_PT_blender_hobo_scene_params_gui,
	blender_hobo_image_property_declaration,
	blender_hobo_scene_property_declaration,
	blender_hobo_addon_prefs
)

register_, unregister_ = bpy.utils.register_classes_factory(rclasses)

def register():
	register_()

	# Image params
	# Like exclusion/inclusion, info, etc
	bpy.types.Image.hobo_image_params = PointerProperty(type=blender_hobo_image_property_declaration)

	# Global Config per scene
	bpy.types.Scene.hobo_config = PointerProperty(type=blender_hobo_scene_property_declaration)







def unregister():
	unregister_()
	# bpy.utils.unregister_class(blfoilvtf)










