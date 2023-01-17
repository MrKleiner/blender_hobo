
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
hobo_name = __name__.partition('.')[0]





# Nothing is converted twice, the filename of the converted image is sha256 of the source image
# 	But it's possible to force-reconvert

# Hashes are not recalculated twice, they're stored in the image datablock
# 	But it's possible to force-recalc hashes

# Image datablocks are marked as converted once done
# 	But it's possible to force-reconvert

# If the filesize of the converted image is bigger than source - the operation is discarded and image is marked as done
























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
magix_exe = addon_root_dir / 'bins' / 'imgmagick' / 'magick.exe'
nvtools_exe = addon_root_dir / 'bins' / 'nvtextools' / 'nvcompress.exe'














# =========================================================
# ---------------------------------------------------------
#                       Actual shit
# ---------------------------------------------------------
# =========================================================

def ensure_addon_is_set_up():
	import subprocess

	# ensure that magix is there
	if not magix_exe.is_file():
		# unpack magix
		unpk_prms = [
			str(addon_root_dir / 'bins' / '7z' / '7z.exe'),
			'x',
			'-o' + str(addon_root_dir / 'bins'),
			str(addon_root_dir / 'bins' / 'imgmagick.orgn'),
			'-aoa'
		]

		# exec magix unpacking
		subprocess.run(unpk_prms, stdout=subprocess.DEVNULL)

	# ensure that nvidia is there
	if not nvtools_exe.is_file():
		# unpack magix
		unpk_prms = [
			str(addon_root_dir / 'bins' / '7z' / '7z.exe'),
			'x',
			'-o' + str(addon_root_dir / 'bins' / 'nvtextools'),
			str(addon_root_dir / 'bins' / 'nvtextools.orgn'),
			'-aoa'
		]

		# exec magix unpacking
		subprocess.run(unpk_prms, stdout=subprocess.DEVNULL)


ensure_addon_is_set_up()

def hobo_rnd_id():
	return hashlib.sha256(('!lizard?'.join([str(random.random()) for rnd in range(int(256))])).encode()).hexdigest()


def hobo_to_dds_imgmagick(fpath):
	magix_prms = [
		str(magix_exe),
		str(fpath),
		'-define', 'dds:compression={none}',
		# '-define', 'dds:weight-by-alpha{false}',
		# str(dump_dir / f'{tgt_img_hash}.dds')
		'dds:'
	]

	dds_bytes = None
	with subprocess.Popen(magix_prms, stdout=subprocess.PIPE, bufsize=10**8) as img_pipe:
		dds_bytes = img_pipe.stdout.read()

	return dds_bytes


def hobo_to_dds_nvidia(fpath):
	dump_dir = Path(bpy.context.preferences.addons[hobo_name].preferences.dumpster_path)

	tmp_path = dump_dir / f'{hobo_rnd_id()}.tmpshit.dds'

	nvidia_prms = [
		str(nvtools_exe),
		'-fast',
		# can't wait for bc7 Blender support...
		'-bc3',
		str(fpath),
		str(tmp_path)
	]

	dds_echo = None
	with subprocess.Popen(nvidia_prms, stdout=subprocess.PIPE, bufsize=10**8) as img_pipe:
		dds_echo = img_pipe.stdout.read()


	if tmp_path.is_file():
		ddbytes = tmp_path.read_bytes()
		tmp_path.unlink(missing_ok=True)
		return ddbytes
	else:
		print('bad conversion')
		return False





def hobo_exec_opt(self, context, force=False):
	print('You hobo')
	print(bpy.context.preferences.addons[hobo_name].preferences.dumpster_path)
	dump_dir = Path(bpy.context.preferences.addons[hobo_name].preferences.dumpster_path)

	collected = {}

	# collect image paths
	for mat in bpy.data.materials:
		if mat.use_nodes != True:
			continue

		for mnode in mat.node_tree.nodes:
			if mnode.type != 'TEX_IMAGE':
				continue

			tgt_img = mnode.image
			img_path = Path(bpy.path.abspath(tgt_img.filepath))

			do_skip = (
				# if scene is set to manual exclude
				context.scene.hobo_config.as_exclusion == True and tgt_img.hobo_image_params.do_convert == False,
				# if scene is set to manual include
				context.scene.hobo_config.as_exclusion == False and tgt_img.hobo_image_params.do_convert != True,
				# if image was converted already
				tgt_img.get('hobo_is_converted') == True,
				# don't mind packed shit for now
				tgt_img.is_embedded_data == True,
				# do nothing if it's dds already
				img_path.suffix.lower() == '.dds'
			)

			if True in do_skip:
				continue

			img_hash = tgt_img.get('hobo_hash')
			if not img_hash:
				img_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()
				tgt_img['hobo_hash'] = img_hash

			if not (dump_dir / f'{img_hash}.dds').is_file():
				print('collected', img_path)
				collected[hashlib.sha1(str(img_path).encode()).hexdigest()] = (img_path, tgt_img, img_hash)


	# process image paths
	for to_dds in collected:
		tgt_img_path = collected[to_dds][0]
		tgt_img_dna = collected[to_dds][1]
		tgt_img_hash = collected[to_dds][2]

		print('hobo processing', str(tgt_img_path))

		dds_bytes = hobo_to_dds_nvidia(tgt_img_path)

		tgt_img_dna['hobo_is_converted'] = True
		tgt_img_dna['hobo_original_path'] = str(tgt_img_path)

		# conversion could fail due to unsupported file format, like .jfif
		if dds_bytes == False:
			continue

		# sometimes the resulting file might actually be bigger...
		# in this case - discard everything and move on
		if os.stat(str(tgt_img_path)).st_size > len(dds_bytes):
			print('good size')
			new_img_path = (dump_dir / f'{tgt_img_hash}.dds')
			new_img_path.write_bytes(dds_bytes)
			tgt_img_dna.filepath = str(new_img_path)
			tgt_img_dna.reload()



	print('Hobo done opts')








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
	# bl_idname = __name__
	bl_idname = __name__.partition('.')[0]

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
	bl_category = 'Hobo'
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
	bl_category = 'Hobo'
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










