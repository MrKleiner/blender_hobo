bl_info = {
	'name': 'Blender Hobo',
	'author': 'MrKleiner',
	'version': (0, 21),
	'blender': (3, 4, 1),
	'location': 'N menu',
	# 'description': """Fit more dicks down VRAM's throat at the cost of texture quality""",
	'description': """Decrease the amount of VRAM taken by textures""",
	# 'warning': 'You suck',
	'doc_url': '',
	'category': 'Add Mesh',
}

# hobo_name = bl_info['name']




#
# Even though this also increases render speed, keep in mind that it only affects textures and not lighting n stuff
#



# The difference between Simplify and this is that the texture size stays the same

# Nothing is converted twice, the filename of the converted image is sha256 of the source image
# 	But it's possible to force-reconvert

# Hashes are not recalculated twice, they're stored in the image datablock
# 	But it's possible to force-recalc hashes

# Image datablocks are marked as converted once done
# 	But it's possible to force-reconvert

# If the filesize of the converted image is bigger than source - the operation is discarded and image is marked as done

# All the associations are stored in a few database files for convenience

# The effect can be easily reversed: the 'hobo_original_path' attribute of the image stores the path to the source image




















import bpy

import hashlib, random, mathutils, time, datetime, subprocess, shutil, sys, os, json, math, re, sqlite3

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

hobo_name = __name__.partition('.')[0]
addon_root_dir = Path(__file__).absolute().parent
magix_exe = addon_root_dir / 'bins' / 'imgmagick' / 'magick.exe'
nvtools_exe = addon_root_dir / 'bins' / 'nvtextools' / 'nvcompress.exe'
nvtools_adv_exe = addon_root_dir / 'bins' / 'nvtextools' / 'nvtt_export.exe'
current_blend = Path(bpy.path.abspath(bpy.data.filepath))

global hdumpster_dir
hdumpster_dir = None















# =========================================================
# ---------------------------------------------------------
#                       Actual shit
# ---------------------------------------------------------
# =========================================================

# imagemagick and nvidia tools come inside an archive
# this function will unpack this stuff if it's not already unpacked
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

# Yes, this function is triggered on every blender startup
# but it shouldn't be too big of a problem, since it simply checks whether 2 files exist inside the addon folder
ensure_addon_is_set_up()


# This will set up the dependency and conversion history journals if they're not present
def ensure_database_present():
	if (hdumpster_dir / 'sys').is_dir():
		return
	(hdumpster_dir / 'sys').mkdir()

	# Conversion history
	connection = sqlite3.connect(str(hdumpster_dir / 'sys' / 'conv_hist.db'))
	cursor_obj = connection.cursor()
	cursor_obj.execute("""
		CREATE TABLE history (
			creator_path VARCHAR,
			creator_name VARCHAR,
			img_src VARCHAR NOT NULL,
			img_src_hash CHAR(64) NOT NULL UNIQUE,
			img_path_hash VARCHAR NOT NULL,
			src_size BIGINT,
			conv_size INT,
			conv_with VARCHAR,
			conv_format VARCHAR,
			conv_ext VARCHAR(16) NOT NULL
		);
	""")
	connection.commit()
	connection.close()


	# Dependencies
	connection = sqlite3.connect(str(hdumpster_dir / 'sys' / 'deps.db'))
	cursor_obj = connection.cursor()
	cursor_obj.execute("""
		CREATE TABLE deps (
			img_hash VARCHAR NOT NULL,
			user VARCHAR NOT NULL,
			user_hash CHAR(64) NOT NULL,
			user_name VARCHAR NOT NULL,
			UNIQUE(img_hash, user, user_hash, user_name)
		);
	""")
	connection.commit()
	connection.close()




# Generate a random id. Basically, bootleg UUID
def hobo_rnd_id():
	return hashlib.sha256(('!lizard?'.join([str(random.random()) for rnd in range(int(256))])).encode()).hexdigest()


#
# Image conversion functions
#


# Add converted image to the converted images registry
def hobo_add_converted_img_to_registry(imgsrc_path, imgsrc_fhash, convd_size, convd_algo, converter_app, convd_file_ext):
	connection = sqlite3.connect(str(hdumpster_dir / 'sys' / 'conv_hist.db'))
	cursor = connection.cursor()

	insert_params = ("""
		INSERT OR REPLACE INTO history
		(creator_path, creator_name, img_src, img_src_hash, img_path_hash, src_size, conv_size, conv_with, conv_format, conv_ext)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
	""")

	data_tuple = (
		# creator_path
		str(current_blend),
		# creator_name
		current_blend.name,
		# img_src
		str(imgsrc_path),
		# img_src_hash
		imgsrc_fhash,
		# img_path_hash
		hashlib.sha256(str(imgsrc_path).encode()).hexdigest(),
		# src_size
		os.stat(imgsrc_path).st_size,
		# conv_size
		convd_size,
		# conv_with
		converter_app,
		# conv_format
		convd_algo,
		# conv_ext
		convd_file_ext
	)

	cursor.execute(insert_params, data_tuple)
	connection.commit()
	connection.close()





# Convert an image to dds using imagemagick
def hobo_to_dds_imgmagick(fpath, image_hash):
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

# convert an image to dds using nvidia tools (best)
def hobo_to_dds_nvidia(fpath, image_hash):

	tmp_path = hdumpster_dir / f'{hobo_rnd_id()}.tmpshit.dds'

	nvidia_prms = [
		str(nvtools_exe),
		'-fast',
		# can't wait for bc7 Blender support...
		'-nomips' if bpy.context.scene.hobo_config.generate_mips == True else '',
		'-bc3',
		str(fpath),
		str(tmp_path)
	]

	nvidia_prms = [
		str(nvtools_adv_exe),
		# can't wait for bc7 Blender support...
		'-f', '18',
		# '-f', '15',
		'-q', '0',
		'--mips' if bpy.context.scene.hobo_config.generate_mips == True else '--no-mips',
		'--mip-filter', '1',
		'-o', str(tmp_path),

		str(fpath)
	]

	nvidia_prms = filter(None, nvidia_prms)

	dds_echo = None
	with subprocess.Popen(nvidia_prms, stdout=subprocess.PIPE, bufsize=10**8) as img_pipe:
		dds_echo = img_pipe.stdout.read()

	if not tmp_path.is_file():
		print('bad conversion')
		return False


	ddbytes = tmp_path.read_bytes()
	tmp_path.unlink(missing_ok=True)

	conv_fsize = len(ddbytes)
	original_size = os.stat(fpath).st_size

	if original_size < conv_fsize and bpy.context.scene.hobo_config.skip_non_hdd_efficient == False:
		return False


	# add to conversion registry
	# imgsrc_path, imgsrc_fhash, convd_size, convd_algo, convd_file_ext
	hobo_add_converted_img_to_registry(
		fpath,
		image_hash,
		conv_fsize,
		'bc3',
		'nvidia_tools_gui',
		'dds'
	)

	return ddbytes






# When the 'Exclusion' checkbox is toggled - 
# this function triggers and inverts all the checkboxes on the images
# for instance, toggling from Exclusion to Inclusion would make previously check checkboxes unchecked
def hobo_invert_exclusion_case(self, context):
	for img in bpy.data.images:
		img.hobo_image_params.do_convert = not img.hobo_image_params.do_convert

# Add an image as dependency to the dependency journal
# (this doesn't affect anything at all, it's only here to better know which image is used where)
def hobo_add_img_dep(image_hash):
	connection_deps = sqlite3.connect(str(hdumpster_dir / 'sys' / 'deps.db'))
	cursor_deps = connection_deps.cursor()

	current_blend = Path(bpy.path.abspath(bpy.data.filepath))

	insert_params = ("""
		INSERT OR REPLACE INTO deps
		(img_hash, user, user_hash, user_name)
		VALUES (?, ?, ?, ?);
	""")
	data_tuple = (
		image_hash,
		str(current_blend),
		hashlib.sha256(str(current_blend).encode()).hexdigest(),
		str(current_blend.name)
	)
	cursor_deps.execute(insert_params, data_tuple)
	connection_deps.commit()
	connection_deps.close()

# this function restores converted images to their original filepath
def hobo_restore_originals(self, context):
	for img in bpy.data.images:
		original_fpath = img.get('hobo_original_path')
		if original_fpath:
			img.filepath = original_fpath
			img['hobo_is_converted'] = False





# -------------------------------------------------------------------------
# The main function which goes through all the images and does the stuff
# -------------------------------------------------------------------------
def hobo_exec_opt(self, context, force=False):
	global hdumpster_dir

	print('You hobo')
	print(bpy.context.preferences.addons[hobo_name].preferences.dumpster_path)
	hdumpster_dir = Path(bpy.context.preferences.addons[hobo_name].preferences.dumpster_path)

	ensure_database_present()


	collected = {}
	context.scene.hobo_config.saved_space = 0

	# collect images to convert
	for mat in bpy.data.materials:
		# Some materials don't use nodes
		if mat.use_nodes != True:
			continue

		for mnode in mat.node_tree.nodes:
			if mnode.type != 'TEX_IMAGE':
				continue

			tgt_img = mnode.image
			# this can point to a missing file if the the image was converted, but the resulting dds deleted later
			img_path = Path(bpy.path.abspath(tgt_img.filepath))
			img_path_hash = hashlib.sha1(str(img_path).encode()).hexdigest()
			# this can be none, because by far not every image was converted
			original_img_path = Path(str(tgt_img.get('hobo_original_path')))
			# print(tgt_img.name, context.scene.hobo_config.as_exclusion == False,  tgt_img.hobo_image_params.do_convert == False)
			do_skip = (
				# if scene is set to manual exclude, then do_convert should not be True (image is not excluded)
				context.scene.hobo_config.as_exclusion == True and tgt_img.hobo_image_params.do_convert == True,
				# if scene is set to manual include, then do_convert should not be False (image is included)
				context.scene.hobo_config.as_exclusion == False and tgt_img.hobo_image_params.do_convert == False,
				# don't mind packed shit for now
				tgt_img.is_embedded_data == True,
				# do nothing if the original source is dds
				img_path.suffix.lower() == '.dds' and tgt_img.get('hobo_is_converted') != True,
				# If this is the second encounter of the same image - skip
				img_path_hash in collected,
				# If this image was not converted and the image file is missing (happens). Skip
				tgt_img.get('hobo_is_converted') == False and not img_path.is_file()
			)

			if True in do_skip:
				# print(do_skip)
				continue

			# if this image was converted, but the converted dds was later deleted - reconvert
			if tgt_img.get('hobo_is_converted') == True and not img_path.is_file():
				del tgt_img['hobo_is_converted']
				tgt_img.filepath = tgt_img['hobo_original_path']
				tgt_img['hobo_original_path'] = None
				if 'hobo_hash' in tgt_img:
					del tgt_img['hobo_hash']

			# at this point it's only left to believe that hobo_is_converted doesn't lie
			if tgt_img.get('hobo_is_converted') == True and force != True:
				# account savings
				try:
					context.scene.hobo_config.saved_space += os.stat(tgt_img['hobo_original_path']).st_size - os.stat(img_path).st_size
				except Exception as e:
					pass

				# and skip this image, since it's, supposedly, already processed and is fine
				continue

			# this is separated from the code above, because reconversio does not require image hash recalculation
			if force == True:
				tgt_img['hobo_hash'] = None
				tgt_img.filepath = tgt_img.get('hobo_original_path')
				img_path = Path(bpy.path.abspath(tgt_img.filepath))
				tgt_img['hobo_original_path'] = None

			# Get image hash
			img_hash = tgt_img.get('hobo_hash')
			if not img_hash:
				img_hash = hashlib.sha256(img_path.read_bytes()).hexdigest()
				tgt_img['hobo_hash'] = img_hash

			# this path MAY contain a converted image
			converted_image_path = hdumpster_dir / f'{img_hash}.dds'

			if force == True:
				converted_image_path.unlink(missing_ok=True)


			if not converted_image_path.is_file():
				print('collected', img_path)
				collected[img_path_hash] = (img_path, tgt_img, img_hash)
			else:

				hobo_add_img_dep(img_hash)

				tgt_img.filepath = str(converted_image_path)
				tgt_img['hobo_is_converted'] = True
				tgt_img['hobo_original_path'] = str(img_path)
				context.scene.hobo_config.saved_space += os.stat(img_path).st_size - os.stat(converted_image_path).st_size

		

	# process image paths
	for to_dds in collected:
		tgt_img_path = collected[to_dds][0]
		tgt_img_dna = collected[to_dds][1]
		tgt_img_hash = collected[to_dds][2]

		print('hobo processing', str(tgt_img_path))

		dds_bytes = hobo_to_dds_nvidia(tgt_img_path, tgt_img_hash)

		tgt_img_dna['hobo_is_converted'] = True
		tgt_img_dna['hobo_original_path'] = str(tgt_img_path)

		# conversion could fail due to unsupported file format, like .jfif
		# or due to converted image being bigger, than original, while skip_non_hdd_efficient is True
		if dds_bytes == False:
			continue


		print('conversion ok')
		context.scene.hobo_config.saved_space += os.stat(tgt_img_path).st_size - len(dds_bytes)
		new_img_path = (hdumpster_dir / f'{tgt_img_hash}.dds')
		new_img_path.write_bytes(dds_bytes)
		tgt_img_dna.filepath = str(new_img_path)
		tgt_img_dna.reload()

		# add to dependency registry
		hobo_add_img_dep(tgt_img_hash)



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


class OBJECT_OT_hobo_exec_opt_force(Operator, AddObjectHelper):
	bl_idname = 'mesh.hobo_optimize_force'
	bl_label = 'Opt Hobo'
	bl_options = {'REGISTER'}

	def execute(self, context):
		hobo_exec_opt(self, context, True)
		return {'FINISHED'}


class OBJECT_OT_hobo_exec_restore_originals(Operator, AddObjectHelper):
	bl_idname = 'mesh.hobo_restore_originals'
	bl_label = 'Hobo Restore'
	bl_options = {'REGISTER'}

	def execute(self, context):
		context.scene.hobo_config.saved_space = 0
		hobo_restore_originals(self, context)
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
		default=False
	)


class blender_hobo_material_property_declaration(PropertyGroup):
	exclude_material : BoolProperty(
		name='Exclude Material',
		description='Whether to convert the image or not',
		default=True
	)


class blender_hobo_scene_property_declaration(PropertyGroup):
	as_exclusion : BoolProperty(
		name='Exclusion',
		description=""" When checked - Individual images have to be excluded from conversion.
		When UNchecked - individual images have to be marked for conversion.
		Go to the Hobo panel in the Image Editor/Node Editor N panel and look for a self-explanatory checkbox""",
		default=False,
		update=hobo_invert_exclusion_case
	)

	skip_non_hdd_efficient : BoolProperty(
		name='Skip Non-Storage Efficient Conversions',
		description=""" The image file size on disk doesn't actually corelate to the amount of VRAM used.
		For instance, a BW 4k .png image with the file size of 9mb would still use 100mb of VRAM.
		This can be solved by optimizing the image, BUT the filesize of the converted image would actually grow a lot and this may be inconvenient at times.
		If this checkbox is checked, then such conversions are discarded""",
		default=True
	)

	generate_mips : BoolProperty(
		name='Mipmaps',
		description="""Whether to generate mipmaps or not""",
		default=True
	)

	saved_space : IntProperty(
		name='Saved Space',
		description="""Total gb VRAM saved""",
		default=0
	)

	scene_vram_total : IntProperty(
		name='Total VRAM taken',
		description="""VRAM taken by all the images in every material""",
		default=0
	)

	comp_level : EnumProperty(
		items=[
			('Regular', 'Regular', 'Regular'),
			('Increased', 'Increased', 'Try different methods when compressing'),
			('DOOM 1996', 'DOOM 1996', 'Use the highest sane compression possible')
		],
		name='Compression Level',
		description='Compression Level',
		default='Regular'
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


		dumpster.row().operator('mesh.hobo_optimize',
			text='I want my scene to look rubbish',
		)
		# dumpster.label(text='')
		dumpster.row().operator('mesh.hobo_optimize_force',
			text='Force regenerate'
		)
		dumpster.row().operator('mesh.hobo_restore_originals',
			text='Restore original filepaths'
		)
		dumpster.label(text=f'VRAM saved: {round(context.scene.hobo_config.saved_space / (1024*1024*1024), 3)} GB')
		dumpster.label(text='Compression Level')
		comp_level_row = dumpster.row()
		comp_level_row.prop(context.scene.hobo_config, 'comp_level', expand=True)
		dumpster.prop(context.scene.hobo_config, 'as_exclusion')
		dumpster.prop(context.scene.hobo_config, 'generate_mips')




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



#
# Node editor
#
class NODE_PT_blender_hobo_image_params_from_node_gui(bpy.types.Panel):
	bl_space_type = 'NODE_EDITOR'
	bl_region_type = 'UI'
	bl_category = 'Hobo'
	bl_label = 'Hobo'
	# https://youtu.be/sT3joXENOb0

	def draw(self, context):
		node = context.active_node

		if node.type == 'TEX_IMAGE':
			layout = self.layout

			dumpster = layout.column(align=True)
			# dumpster.use_property_split = True
			# dumpster.use_property_decorate = False

			dumpster.prop(node.image.hobo_image_params, 'do_convert', text=('Exclude' if context.scene.hobo_config.as_exclusion else 'Include'))






















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
	blender_hobo_addon_prefs,
	OBJECT_OT_hobo_exec_opt_force,
	NODE_PT_blender_hobo_image_params_from_node_gui,
	OBJECT_OT_hobo_exec_restore_originals
)

register_, unregister_ = bpy.utils.register_classes_factory(rclasses)

def register():
	register_()

	# Image params
	# Like exclusion/inclusion, info, etc
	bpy.types.Image.hobo_image_params = PointerProperty(type=blender_hobo_image_property_declaration)

	# Global Config per scene
	bpy.types.Scene.hobo_config = PointerProperty(type=blender_hobo_scene_property_declaration)

	# Config per material
	bpy.types.Material.hobo_config = PointerProperty(type=blender_hobo_scene_property_declaration)





def unregister():
	unregister_()
	# bpy.utils.unregister_class(blfoilvtf)

