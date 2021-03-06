import os
import shutil
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from CMOSMetalBayerFilter2DParameters import *
import CMOSMetalBayerFilter2D

import RadialLevelSet

import lumapi

import functools
import h5py
import matplotlib.pyplot as plt
import numpy as np
import time

def permittivity_to_index( permittivity ):
	eps_real = np.real( permittivity )
	eps_imag = np.imag( permittivity )

	eps_mag = np.sqrt( eps_real**2 + eps_imag**2 )

	n = np.sqrt( ( eps_mag + eps_real ) / 2. )
	kappa = np.sqrt( ( eps_mag - eps_real ) / 2. )

	return ( n + 1j * kappa )

#
# Create FDTD hook
#
fdtd_hook = lumapi.FDTD()


#
# Create project folder and save out the parameter file for documentation for this optimization
#
project_subfolder = ""
if len(sys.argv) > 1:
	project_subfolder = "/" + sys.argv[1] + "/"

use_random_design_seed = False
if len(sys.argv) > 3:
	random_seed = int( sys.argv[2] )
	np.random.seed( random_seed )
	use_random_design_seed = True
	step_size_multiplier = float( sys.argv[3] )
	adaptive_step_size *= step_size_multiplier

python_src_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
projects_directory_location = os.path.abspath(os.path.join(os.path.dirname(__file__), '../projects/')) + project_subfolder

if not os.path.isdir(projects_directory_location):
	os.mkdir(projects_directory_location)

projects_directory_location += "/" + project_name

if not os.path.isdir(projects_directory_location):
	os.mkdir(projects_directory_location)

log_file = open(projects_directory_location + "/log.txt", 'w')
log_file.write("Log\n")
log_file.close()

fdtd_hook.newproject()
fdtd_hook.save(projects_directory_location + "/optimization")

shutil.copy2(python_src_directory + "/CMOSMetalBayerFilter2DParameters.py", projects_directory_location + "/ArchiveCMOSMetalBayerFilter.py")

def get_non_struct_data(monitor_name, monitor_field):
	lumerical_data_name = "monitor_data_" + monitor_name + "_" + monitor_field
	data_transfer_filename = projects_directory_location + "/data_transfer_" + monitor_name + "_" + monitor_field

	command_read_monitor = lumerical_data_name + " = getresult(\'" + monitor_name + "\', \'" + monitor_field + "\');"
	command_save_data_to_file = "matlabsave(\'" + data_transfer_filename + "\', " + lumerical_data_name + ");"

	lumapi.evalScript(fdtd_hook.handle, command_read_monitor)

	# start_time = time.time()

	lumapi.evalScript(fdtd_hook.handle, command_save_data_to_file)
	monitor_data = {}
	load_file = h5py.File(data_transfer_filename + ".mat", 'r')

	monitor_data = np.array(load_file[lumerical_data_name])

	# end_time = time.time()

	# print("\nIt took " + str(end_time - start_time) + " seconds to transfer the monitor data\n")

	return monitor_data['real']

#
# Consolidate the data transfer functionality for getting data from Lumerical FDTD process to
# python process.  This is much faster than going through Lumerical's interop library
#
def get_monitor_data(monitor_name, monitor_field):
	lumerical_data_name = "monitor_data_" + monitor_name + "_" + monitor_field
	extracted_data_name = lumerical_data_name + "_data"
	data_transfer_filename = projects_directory_location + "/data_transfer_" + monitor_name + "_" + monitor_field

	command_read_monitor = lumerical_data_name + " = getresult(\'" + monitor_name + "\', \'" + monitor_field + "\');"
	command_extract_data = extracted_data_name + " = " + lumerical_data_name + "." + monitor_field + ";"
	command_save_data_to_file = "matlabsave(\'" + data_transfer_filename + "\', " + extracted_data_name + ");"

	lumapi.evalScript(fdtd_hook.handle, command_read_monitor)
	lumapi.evalScript(fdtd_hook.handle, command_extract_data)

	# start_time = time.time()

	lumapi.evalScript(fdtd_hook.handle, command_save_data_to_file)
	monitor_data = {}
	load_file = h5py.File(data_transfer_filename + ".mat", 'r')

	monitor_data = np.array(load_file[extracted_data_name])

	# end_time = time.time()

	# print("\nIt took " + str(end_time - start_time) + " seconds to transfer the monitor data\n")

	return monitor_data

def get_complex_monitor_data(monitor_name, monitor_field):
	data = get_monitor_data(monitor_name, monitor_field)
	return (data['real'] + np.complex(0, 1) * data['imag'])

#
# Set up the FDTD region and mesh
#
fdtd = fdtd_hook.addfdtd()
fdtd['dimension'] = '2D'
fdtd['x span'] = fdtd_region_size_lateral_um * 1e-6
fdtd['y max'] = fdtd_region_maximum_vertical_um * 1e-6
fdtd['y min'] = fdtd_region_minimum_vertical_um * 1e-6
fdtd['mesh type'] = 'uniform'
fdtd['define x mesh by'] = 'number of mesh cells'
fdtd['define y mesh by'] = 'number of mesh cells'
fdtd['mesh cells x'] = fdtd_region_minimum_lateral_voxels
fdtd['mesh cells y'] = fdtd_region_minimum_vertical_voxels
fdtd['simulation time'] = fdtd_simulation_time_fs * 1e-15
fdtd['background index'] = background_index

#
# General polarized source information
#
xy_phi_rotations = [0, 90]
xy_names = ['x', 'y']


#
# Add a TFSF plane wave forward source at normal incidence
#
forward_sources = []
# source_polarization_angles = [ 0, 90 ]
# affected_coords_by_polarization = [ [ 0, 1 ], [ 2 ] ]
source_polarization_angles = [ 90, 0 ]
affected_coords_by_polarization = [ [ 2 ], [ 0, 1 ] ]

for pol_idx in range( 0, num_polarizations ):
	forward_src = fdtd_hook.addtfsf()
	forward_src['name'] = 'forward_src_' + str( pol_idx )
	forward_src['polarization angle'] = source_polarization_angles[ pol_idx ]
	forward_src['direction'] = 'Backward'
	forward_src['x span'] = lateral_aperture_um * 1e-6
	forward_src['y max'] = src_maximum_vertical_um * 1e-6
	forward_src['y min'] = src_minimum_vertical_um * 1e-6
	forward_src['wavelength start'] = lambda_min_um * 1e-6
	forward_src['wavelength stop'] = lambda_max_um * 1e-6

	forward_sources.append( forward_src )

#
# Disable all sources in the simulation, so that we can selectively turn single sources on at a time
#
def disable_all_sources():
	fdtd_hook.switchtolayout()

	for pol_idx in range( 0, num_polarizations ):
		forward_sources[ pol_idx ].enabled = 0

	for coord_idx in range( 0, 3 ):
		for adj_src_idx in range(0, num_adjoint_sources):
			(adjoint_sources[ coord_idx ][ adj_src_idx ]).enabled = 0


#
# Place dipole adjoint sources at the focal plane that can ring in both
# x-axis and y-axis
#
adjoint_sources = [ [] for i in range( 0, 3 ) ]
coord_to_phi = [ 0, 90, 0 ]
coord_to_theta = [ 90, 90, 0 ]

for coord_idx in range( 0, 3 ):
	for adj_src_idx in range(0, num_adjoint_sources):
		adj_src = fdtd_hook.adddipole()
		adj_src['name'] = 'adj_src_' + str(adj_src_idx) + "_" + str( coord_idx )
		adj_src['x'] = adjoint_x_positions_um[adj_src_idx] * 1e-6
		adj_src['y'] = adjoint_vertical_um * 1e-6
		adj_src['theta'] = coord_to_theta[ coord_idx ]
		adj_src['phi'] = coord_to_phi[ coord_idx ]
		adj_src['wavelength start'] = lambda_min_um * 1e-6
		adj_src['wavelength stop'] = lambda_max_um * 1e-6

		adjoint_sources[ coord_idx ].append( adj_src )

#
# Set up the volumetric electric field monitor inside the design region.  We will need this compute
# the adjoint gradient
#
design_efield_monitor = fdtd_hook.addprofile()
design_efield_monitor['name'] = 'design_efield_monitor'
design_efield_monitor['x span'] = device_size_lateral_um * 1e-6
design_efield_monitor['y min'] = designable_device_vertical_minimum_um * 1e-6
design_efield_monitor['y max'] = designable_device_vertical_maximum_um * 1e-6
design_efield_monitor['override global monitor settings'] = 1
design_efield_monitor['use linear wavelength spacing'] = 1
design_efield_monitor['use source limits'] = 0
design_efield_monitor['minimum wavelength'] = lambda_min_um * 1e-6
design_efield_monitor['maximum wavelength'] = lambda_max_um * 1e-6
design_efield_monitor['frequency points'] = num_design_frequency_points
design_efield_monitor['output Hx'] = 0
design_efield_monitor['output Hy'] = 0
design_efield_monitor['output Hz'] = 0

design_index_monitor = fdtd_hook.addindex()
design_index_monitor['name'] = 'design_index_monitor'
design_index_monitor['x span'] = device_size_lateral_um * 1e-6
design_index_monitor['y min'] = designable_device_vertical_minimum_um * 1e-6
design_index_monitor['y max'] = designable_device_vertical_maximum_um * 1e-6

#
# Set up adjoint point monitors to get electric field strength at focus spots.  This will allow us to
# compute the figure of merit as well as weight the adjoint simulations properly in calculation of the
# gradient.
#
focal_monitors = []

for adj_src in range(0, num_adjoint_sources):
	focal_monitor = fdtd_hook.addpower()
	focal_monitor['name'] = 'focal_monitor' + str(adj_src)
	focal_monitor['monitor type'] = 'point'
	focal_monitor['x'] = adjoint_x_positions_um[adj_src] * 1e-6
	focal_monitor['y'] = adjoint_vertical_um * 1e-6
	focal_monitor['override global monitor settings'] = 1
	focal_monitor['use linear wavelength spacing'] = 1
	focal_monitor['use source limits'] = 0
	focal_monitor['minimum wavelength'] = lambda_min_um * 1e-6
	focal_monitor['maximum wavelength'] = lambda_max_um * 1e-6
	focal_monitor['frequency points'] = num_design_frequency_points

	focal_monitors.append(focal_monitor)


for adj_src in range(0, num_adjoint_sources):
	transmission_monitor = fdtd_hook.addpower()
	transmission_monitor['name'] = 'transmission_monitor_' + str(adj_src)
	transmission_monitor['monitor type'] = 'Linear X'
	transmission_monitor['x'] = adjoint_x_positions_um[adj_src] * 1e-6
	transmission_monitor['x span'] = ( 1.0 / num_focal_spots ) * device_size_lateral_um * 1e-6
	transmission_monitor['y'] = adjoint_vertical_um * 1e-6
	transmission_monitor['override global monitor settings'] = 1
	transmission_monitor['use linear wavelength spacing'] = 1
	transmission_monitor['use source limits'] = 1
	transmission_monitor['frequency points'] = num_eval_frequency_points

#
# Add device region and create device permittivity
#

min_device_permittivity = min_real_permittivity + 1j * min_imag_permittivity
max_device_permittivity = max_real_permittivity + 1j * max_imag_permittivity

#
# Here, many devices will actually be added, one for each actually designable region.  When the region is not
# designable, we will just add a block of material there.  This applies for things like the via and capping layers
#
number_device_layers = len( layer_thicknesses_um )

bayer_filters = []
bayer_filter_regions_y = []
design_imports = []
lock_design_to_reflective = []

lsfs_by_layer = []

bayer_filter_region_x = 1e-6 * np.linspace(-0.5 * device_size_lateral_um, 0.5 * device_size_lateral_um, device_voxels_lateral)
bayer_filter_region_z = 1e-6 * np.linspace(-0.51, 0.51, 2)

for device_layer_idx in range( 0, number_device_layers ):
	layer_vertical_maximum_um = designable_device_vertical_maximum_um - np.sum( layer_thicknesses_um[ 0 : device_layer_idx ] )
	layer_vertical_minimum_um = layer_vertical_maximum_um - layer_thicknesses_um[ device_layer_idx ]

	if is_layer_designable[ device_layer_idx ]:

		one_vertical_layer = 1
		layer_bayer_filter_size_voxels = np.array([device_voxels_lateral, layer_thicknesses_voxels[device_layer_idx], 1])

		num_vertical_layers = layer_thicknesses_voxels[device_layer_idx]
		if enforce_layering:
			num_vertical_layers = one_vertical_layer

		init_design = init_permittivity_0_1_scale
		layer_bayer_filter = CMOSMetalBayerFilter2D.CMOSMetalBayerFilter2D(
			layer_bayer_filter_size_voxels, [min_device_permittivity, max_device_permittivity], init_design, num_vertical_layers)

		if init_from_random:
		 	random_design_seed = init_max_random_0_1_scale * np.random.random( layer_bayer_filter_size_voxels )
		 	layer_bayer_filter.set_design_variable( random_design_seed )

		bayer_filter_region_y = 1e-6 * np.linspace(layer_vertical_minimum_um, layer_vertical_maximum_um, layer_thicknesses_voxels[device_layer_idx])

		# bayer_filter.set_design_variable( np.load( projects_directory_location + "/cur_design_variable.npy" ) )

		layer_import = fdtd_hook.addimport()
		layer_import['name'] = 'layer_import_' + str( device_layer_idx )
		layer_import['x span'] = device_size_lateral_um * 1e-6
		layer_import['y min'] = layer_vertical_minimum_um * 1e-6
		layer_import['y max'] = layer_vertical_maximum_um * 1e-6
		layer_import['z min'] = -0.51 * 1e-6
		layer_import['z max'] = 0.51 * 1e-6

		# print("For layer " + str( device_layer_idx ), " the min um spot is " + str( layer_vertical_minimum_um ) + " and max um spot is " + str( layer_vertical_maximum_um ) )

		bayer_filters.append( layer_bayer_filter )
		bayer_filter_regions_y.append( bayer_filter_region_y )
		design_imports.append( layer_import )
		lock_design_to_reflective.append( fix_layer_permittivity_to_reflective[ device_layer_idx ] )


	else:
		blank_layer = fdtd_hook.addrect()
		blank_layer['name'] = 'device_layer_' + str(device_layer_idx)
		blank_layer['x span'] = device_size_lateral_um * 1e-6
		blank_layer['y min'] = layer_vertical_minimum_um * 1e-6
		blank_layer['y max'] = layer_vertical_maximum_um * 1e-6
		blank_layer['z span'] = 1.02 * 1e-6
		blank_layer['index'] = layer_background_index[ device_layer_idx ]



#
# Add blocks of dielectric on the side of the designable region because we will be leaving those as blank, unpatterned dielectric material
# Would it be better to have this be a part of the bayer filter material inmport and jus tnot modify it (i.e. - mask out any changes to it).  I'm
# thinking of how the mesh behaves here between these interacting objects.  For now, we will add the blocks around the side because this will make
# it simpler at first and then we can move towards making a more sophisticated device class or subclass.
# Further, in reality, this may be a stack of material in general.  However, it will be mostly the low-K dielctric background material so we will assume
# this is not a stratified stack and is actaully just a single piece of low index material background.
#
extra_lateral_space_per_side_um = 0.5 * ( fdtd_region_size_lateral_um - device_size_lateral_um )
extra_lateral_space_offset_um = 0.5 * ( device_size_lateral_um + extra_lateral_space_per_side_um )

def side_to_string( side_number ):
	side_integer = int( side_number )
	if side_integer < 0:
		return ( "n" + str( np.abs( side_integer ) ) )
	else:
		return str( side_integer )

device_background_side_x = [ -1, 1 ]#, 0, 0 ]
# device_background_side_y = [ 0, 0, -1, 1 ]

for device_background_side_idx in range( 0, 2 ):
	side_x = device_background_side_x[ device_background_side_idx ]

	side_block = fdtd_hook.addrect()

	side_block['name'] = 'device_background_' + side_to_string( side_x )
	side_block['y min'] = designable_device_vertical_minimum_um * 1e-6
	side_block['y max'] = designable_device_vertical_maximum_um * 1e-6
	side_block['x'] = side_x * extra_lateral_space_offset_um * 1e-6
	side_block['x span'] = (
		np.abs( side_x ) * extra_lateral_space_per_side_um +
		( 1 - np.abs( side_x ) ) * fdtd_region_size_lateral_um ) * 1e-6
	side_block['z span'] = 1.02 * 1e-6

	side_block['index'] = device_background_index



#
# Set up some numpy arrays to handle all the data we will pull out of the simulation.
#
forward_e_fields = {}
focal_data = {}

if optimize_via_level_set:
	num_epochs = 1
if optimize_via_level_set:
	num_iterations_per_epoch = num_iterations_level_set

figure_of_merit_evolution = np.zeros((num_epochs, num_iterations_per_epoch))
average_binarization_evolution = np.zeros((num_epochs, num_iterations_per_epoch))
step_size_evolution = np.zeros((num_epochs, num_iterations_per_epoch))
average_design_variable_change_evolution = np.zeros((num_epochs, num_iterations_per_epoch))
max_design_variable_change_evolution = np.zeros((num_epochs, num_iterations_per_epoch))

step_size_start = fixed_step_size


def interpolate_nearest( x, spacing, minimum ):
	interpolate_index = int( round( ( x - minimum ) / spacing ) )
	return interpolate_index

def reinterpolate_nearest_1d( input_data, output_data ):
	input_width = len( input_data )
	output_width = len( output_data )

	for idx in range( 0, output_width ):
		output_data[ idx ] = input_data[ interpolate_nearest( idx / ( output_width - 1. ), 1. / ( input_width - 1 ), 0. ) ]

def update_lsfs( device_step_real, device_step_imag ):
	lsf_grid_width = 1 + int( device_size_verical_um / lsf_mesh_spacing_um )

	density_step = ( max_real_permittivity - min_real_permittivity ) * device_step_real

	for device_layer_idx in range( 0, len( bayer_filters ) ):
		design_height_voxels = len( bayer_filter_regions_y[ device_layer_idx ] )
		
		layer_vertical_minimum_um = 1e6 * bayer_filter_regions_y[ device_layer_idx ][ 0 ]
		layer_vertical_maximum_um = 1e6 * bayer_filter_regions_y[ device_layer_idx ][ -1 ]

		layer_vertical_minimum_voxels = int( ( layer_vertical_minimum_um - designable_device_vertical_minimum_um ) / mesh_spacing_um )
		layer_vertical_maximum_voxels = layer_vertical_minimum_voxels + len( bayer_filter_regions_y[ device_layer_idx ] )

		get_density_step = device_step_real[ :, layer_vertical_minimum_voxels : layer_vertical_maximum_voxels, 0 ]
		average_density_step = np.mean( get_density_step, axis=1 )

		interpolate_average_density_step = np.zeros( lsf_grid_width )
		reinterpolate_nearest_1d( average_density_step, interpolate_average_density_step )

		layer_lsf = lsfs_by_layer[ device_layer_idx ]
		layer_lsf.step( interpolate_average_density_step, 5.0 )#0.5 )

def import_lsfs():
	fdtd_hook.switchtolayout()

	lsf_grid_width = 1 + int( device_size_verical_um / lsf_mesh_spacing_um )

	for device_layer_idx in range( 0, len( bayer_filters ) ):
		layer_lsf = lsfs_by_layer[ device_layer_idx ]

		get_lsf_density = layer_lsf.compute_density()
		design_import = design_imports[ device_layer_idx ]
		x_region = np.linspace( -0.5 * device_size_lateral_um * 1e-6, 0.5 * device_size_lateral_um * 1e-6, lsf_grid_width )
		y_region = np.linspace( design_import[ 'y min' ], design_import[ 'y max' ], len( bayer_filter_regions_y[ device_layer_idx ] ) )

		cur_permittivity = np.zeros( ( lsf_grid_width, len( bayer_filter_regions_y[ device_layer_idx ] ) ) )

		for y_idx in range( 0, len( bayer_filter_regions_y[ device_layer_idx ] ) ):
			cur_permittivity[ :, y_idx ] = min_real_permittivity + ( max_real_permittivity - min_real_permittivity ) * get_lsf_density
		cur_index = np.sqrt( cur_permittivity )

		import_index = np.zeros( ( cur_index.shape[ 0 ], cur_index.shape[ 1 ], 2 ), dtype=np.complex )
		import_index[ :, :, 0 ] = cur_index[ :, : ]
		import_index[ :, :, 1 ] = cur_index[ :, : ]

		fdtd_hook.select( design_import[ "name" ] )
		fdtd_hook.importnk2( import_index, x_region, y_region, bayer_filter_region_z )

def import_density_and_create_lsfs():
	fdtd_hook.switchtolayout()

	lsf_grid_width = 1 + int( device_size_verical_um / lsf_mesh_spacing_um )

	for device_layer_idx in range( 0, len( bayer_filters ) ):
		cur_density = np.load( projects_directory_location + "/cur_design_variable_" + str( device_layer_idx ) + "_" + str( level_set_starting_epoch ) + ".npy" )
		reinterpolate_density = np.zeros( lsf_grid_width )

		reinterpolate_nearest_1d( np.squeeze( cur_density[ :, 0 ] ), reinterpolate_density )

		sin_input = np.linspace( -1.5, 1.5, lsf_grid_width )
		reinterpolate_density = 0.5 * ( 1 + np.sin( 2 * np.pi * sin_input / 0.15 ) )

		layer_lsf = RadialLevelSet.RadialLevelSet( lsf_grid_width )
		layer_lsf.initialize_lsf( reinterpolate_density )

		penalty = layer_lsf.compute_fabrication_penalty()
		print("Current fabrication penalty = " + str( penalty ) )

		for fab_iter in range( 0, 25 ):
			layer_lsf.fabrication_penalty_sensitivity()
			layer_lsf.compute_gap_sizes()

		layer_lsf.compute_gap_sizes()

		lsfs_by_layer.append( layer_lsf )

		get_lsf_density = layer_lsf.compute_density()
		design_import = design_imports[ device_layer_idx ]
		x_region = np.linspace( -0.5 * device_size_lateral_um * 1e-6, 0.5 * device_size_lateral_um * 1e-6, lsf_grid_width )
		y_region = np.linspace( design_import[ 'y min' ], design_import[ 'y max' ], cur_density.shape[ 1 ] )

		cur_permittivity = np.zeros( ( lsf_grid_width, cur_density.shape[ 1 ] ) )

		for y_idx in range( 0, cur_density.shape[ 1 ] ):
			cur_permittivity[ :, y_idx ] = min_real_permittivity + ( max_real_permittivity - min_real_permittivity ) * get_lsf_density
		cur_index = np.sqrt( cur_permittivity )

		import_index = np.zeros( ( cur_index.shape[ 0 ], cur_index.shape[ 1 ], 2 ), dtype=np.complex )
		import_index[ :, :, 0 ] = cur_index[ :, : ]
		import_index[ :, :, 1 ] = cur_index[ :, : ]

		fdtd_hook.select( design_import[ "name" ] )
		fdtd_hook.importnk2( import_index, x_region, y_region, bayer_filter_region_z )

def import_bayer_filters():
	fdtd_hook.switchtolayout()

	for device_layer_idx in range( 0, len( bayer_filters ) ):
		bayer_filter = bayer_filters[ device_layer_idx ]

		cur_permittivity = bayer_filter.get_permittivity()
		cur_index = permittivity_to_index( cur_permittivity )

		import_index = np.zeros( ( cur_index.shape[ 0 ], cur_index.shape[ 1 ], 2 ), dtype=np.complex )
		import_index[ :, :, 0 ] = cur_index[ :, :, 0 ]
		import_index[ :, :, 1 ] = cur_index[ :, :, 0 ]

		design_import = design_imports[ device_layer_idx ]

		fdtd_hook.select( design_import[ "name" ] )
		fdtd_hook.importnk2( import_index, bayer_filter_region_x, bayer_filter_regions_y[ device_layer_idx ], bayer_filter_region_z )

def import_previous():
	for device_layer_idx in range( 0, len( bayer_filters ) ):
		if lock_design_to_reflective[ device_layer_idx ]:
			continue

		bayer_filter = bayer_filters[ device_layer_idx ]

		# cur_design_variable = np.load(projects_directory_location + "/cur_design_variable_" + str( device_layer_idx ) + ".npy")
		load_old_design_index = np.maximum( 0, start_epoch - 1 )
		cur_design_variable = np.load(projects_directory_location + "/cur_design_variable_" + str( device_layer_idx ) + "_" + str( load_old_design_index ) + ".npy")

		if eval_binarized:
			cur_design_variable = np.load( projects_directory_location + "/cur_design_variable_" + str( device_layer_idx ) + ".npy" )
			cur_design_variable = 1.0 * np.greater( cur_design_variable, 0.5 )

		bayer_filter.set_design_variable( cur_design_variable )

	import_bayer_filters()


def update_bayer_filters( device_step_real, device_step_imag, step_size, do_simulated_annealing, current_temperature ):
	max_max_design_variable_change = 0
	min_max_design_variable_change = 1.0
	
	log_file = open(projects_directory_location + "/log.txt", 'a+')


	max_all_changes = -1
	for device_layer_idx in range( 0, len( bayer_filters ) ):
		layer_vertical_minimum_um = 1e6 * bayer_filter_regions_y[ device_layer_idx ][ 0 ]
		layer_vertical_maximum_um = 1e6 * bayer_filter_regions_y[ device_layer_idx ][ -1 ]

		layer_vertical_minimum_voxels = int( ( layer_vertical_minimum_um - designable_device_vertical_minimum_um ) / mesh_spacing_um )
		layer_vertical_maximum_voxels = layer_vertical_minimum_voxels + len( bayer_filter_regions_y[ device_layer_idx ] )

		step_size_real = device_step_real[ :, layer_vertical_minimum_voxels : layer_vertical_maximum_voxels, : ],

		max_all_changes = np.maximum( max_all_changes, np.max( np.abs( step_size_real ) ) )
	
	set_step_size = step_size / max_all_changes


	for device_layer_idx in range( 0, len( bayer_filters ) ):
		bayer_filter = bayer_filters[ device_layer_idx ]

		cur_design_variable = bayer_filter.get_design_variable()

		np.save(projects_directory_location + "/cur_design_variable_" + str( device_layer_idx ) + ".npy", cur_design_variable)

		if lock_design_to_reflective[ device_layer_idx ]:
			continue

		last_design_variable = cur_design_variable.copy()

		layer_vertical_minimum_um = 1e6 * bayer_filter_regions_y[ device_layer_idx ][ 0 ]
		layer_vertical_maximum_um = 1e6 * bayer_filter_regions_y[ device_layer_idx ][ -1 ]

		layer_vertical_minimum_voxels = int( ( layer_vertical_minimum_um - designable_device_vertical_minimum_um ) / mesh_spacing_um )
		layer_vertical_maximum_voxels = layer_vertical_minimum_voxels + len( bayer_filter_regions_y[ device_layer_idx ] )

		
		if epoch >= start_binarization_epoch:
			bayer_filter.step(
				device_step_real[ :, layer_vertical_minimum_voxels : layer_vertical_maximum_voxels, : ],
				device_step_imag[ :, layer_vertical_minimum_voxels : layer_vertical_maximum_voxels, : ],
				set_step_size,
				do_simulated_annealing,
				current_temperature,
				True,
				0.01,
				0.01 )
		else:
			bayer_filter.step(
				device_step_real[ :, layer_vertical_minimum_voxels : layer_vertical_maximum_voxels, : ],
				device_step_imag[ :, layer_vertical_minimum_voxels : layer_vertical_maximum_voxels, : ],
				set_step_size,
				do_simulated_annealing,
				current_temperature,
				False,
				0.0,
				0.0 )

		cur_design_variable = bayer_filter.get_design_variable()

		average_design_variable_change = np.mean( np.abs( last_design_variable - cur_design_variable ) )
		max_design_variable_change = np.max( np.abs( last_design_variable - cur_design_variable ) )

		max_max_design_variable_change = np.maximum( max_max_design_variable_change, max_design_variable_change )
		min_max_design_variable_change = np.maximum( min_max_design_variable_change, max_design_variable_change )

		log_file.write("The layer number is " + str( device_layer_idx ) + " and thickness is " + str( layer_vertical_maximum_um - layer_vertical_minimum_um )  + "\n")
		log_file.write( "This bayer filter is expecting something of size " + str( bayer_filter.size ) + " and it has been fed something of size " +
			str( device_step_real[ :, layer_vertical_minimum_voxels : layer_vertical_maximum_voxels, : ].shape )  + "\n")
		log_file.write( "The gradient information is being taken between " + str( layer_vertical_minimum_voxels ) + " and " + str( layer_vertical_maximum_voxels )
			+ "\nout of total number height of " + str( designable_device_voxels_vertical ) + " (voxels)\n")
		log_file.write( "The max amount the density is changing for layer " + str( device_layer_idx ) + " is " + str( max_design_variable_change ) + "\n")
		log_file.write( "The mean amount the density is changing for layer " + str( device_layer_idx ) + " is " + str( average_design_variable_change ) + "\n")
		log_file.write("\n")


	log_file.write("\n\n")
	log_file.close()

	if max_max_design_variable_change > desired_max_max_design_change:
		return 0.5
	elif min_max_design_variable_change < desired_min_max_design_change:
		return 2

	return 1

# if use_mirrored_seed_point:
# 	import_previous_seed( 'cur_design_variable_mirrored_' )
# elif start_from_previous:
# 	import_previous_seed( 'cur_design_variable_' )

# update_bayer_filters( -test_change, -test_change, 0.25 )
# import_bayer_filters()

if init_from_old or eval_binarized:
	import_previous()

if optimize_via_level_set:
	import_density_and_create_lsfs()

def splitting_difference_fom(
	normalized_intensity_focal_point_wavelength ):

	num_total_points = num_design_frequency_points
	total_norm = 1.0 / num_total_points
	contrast_low = 0
	contrast_high = 0

	contrasts = np.zeros( 2 * num_points_per_band )

	for wl_idx in range( 0, num_points_per_band ):
		contrasts[ wl_idx ] = ( normalized_intensity_focal_point_wavelength[ 0, wl_idx ] - normalized_intensity_focal_point_wavelength[ 1, wl_idx ] )
		contrasts[ wl_idx + num_points_per_band ] = ( normalized_intensity_focal_point_wavelength[ 1, num_points_per_band + wl_idx ] - normalized_intensity_focal_point_wavelength[ 0, num_points_per_band + wl_idx ] )

	print(contrasts)

	return total_norm * contrasts

def splitting_difference_gradient(
	cur_fom,
	conjugate_weighting_focal_point_wavelength,
	normalized_intensity_focal_point_wavelength,
	forward_e_fields_wavelength,
	adjoint_e_fields_focal_point_wavelength ):

	num_fom = len( cur_fom )
	fom_weighting = ( 2.0 / num_fom ) - cur_fom**2 / np.sum( cur_fom**2 )
	if np.min( fom_weighting ) < 0:
		fom_weighting -= np.min( fom_weighting )
		fom_weighting /= np.sum( fom_weighting )

	print(fom_weighting)
	print("\n\n")

	num_total_points = num_design_frequency_points
	total_norm = 1.0 / num_total_points

	fields_shape = forward_e_fields_wavelength.shape
	gradient_base = np.zeros( fields_shape[ 2 : ], dtype=np.complex )

	for wl_idx in range( 0, num_points_per_band ):
		gradient_base += fom_weighting[ wl_idx ] * np.sum(
			( conjugate_weighting_focal_point_wavelength[ 0, wl_idx ] * adjoint_e_fields_focal_point_wavelength[ 0, wl_idx ] * forward_e_fields_wavelength[ wl_idx ] ),
			axis=0 )
		gradient_base -= fom_weighting[ wl_idx ] * np.sum(
			( conjugate_weighting_focal_point_wavelength[ 1, wl_idx ] * adjoint_e_fields_focal_point_wavelength[ 1, wl_idx ] * forward_e_fields_wavelength[ wl_idx ] ),
			axis=0 )

		gradient_base += fom_weighting[ wl_idx + num_points_per_band ] * np.sum(
			( conjugate_weighting_focal_point_wavelength[ 1, num_points_per_band + wl_idx ] * adjoint_e_fields_focal_point_wavelength[ 1, num_points_per_band + wl_idx ] *
			forward_e_fields_wavelength[ num_points_per_band + wl_idx ] ),
			axis=0 )
		gradient_base -= fom_weighting[ wl_idx + num_points_per_band ] * np.sum(
			( conjugate_weighting_focal_point_wavelength[ 0, num_points_per_band + wl_idx ] * adjoint_e_fields_focal_point_wavelength[ 0, num_points_per_band + wl_idx ] *
			forward_e_fields_wavelength[ num_points_per_band + wl_idx ] ),
			axis=0 )

	return ( total_norm * gradient_base )


def splitting_fom(
	normalized_intensity_focal_point_wavelength ):

	num_total_points = num_design_frequency_points
	total_norm = 1.0 / num_total_points
	contrast_low = 0
	contrast_high = 0
	for wl_idx in range( 0, num_points_per_band ):
		contrast_high += normalized_intensity_focal_point_wavelength[ 0, wl_idx ]
		contrast_low += normalized_intensity_focal_point_wavelength[ 1, num_points_per_band + wl_idx ]

	print(contrast_high)
	print(contrast_low)
	print()

	return total_norm * np.array( [ contrast_high, contrast_low ] )

	# return ( total_norm * ( contrast_low + contrast_high ) )

def splitting_gradient(
	cur_fom,
	conjugate_weighting_focal_point_wavelength,
	normalized_intensity_focal_point_wavelength,
	forward_e_fields_wavelength,
	adjoint_e_fields_focal_point_wavelength ):

	num_fom = len( cur_fom )
	fom_weighting = ( 2.0 / num_fom ) - cur_fom**2 / np.sum( cur_fom**2 )
	if np.min( fom_weighting ) < 0:
		fom_weighting -= np.min( fom_weighting )
		fom_weighting /= np.sum( fom_weighting )

	print(fom_weighting)
	print("\n\n")

	num_total_points = num_design_frequency_points
	total_norm = 1.0 / num_total_points

	fields_shape = forward_e_fields_wavelength.shape
	gradient_base = np.zeros( fields_shape[ 2 : ], dtype=np.complex )

	for wl_idx in range( 0, num_points_per_band ):
		gradient_base += fom_weighting[ 0 ] * np.sum(
			( conjugate_weighting_focal_point_wavelength[ 0, wl_idx ] * adjoint_e_fields_focal_point_wavelength[ 0, wl_idx ] * forward_e_fields_wavelength[ wl_idx ] ),
			axis=0 )

		gradient_base += fom_weighting[ 1 ] * np.sum(
			( conjugate_weighting_focal_point_wavelength[ 1, num_points_per_band + wl_idx ] * adjoint_e_fields_focal_point_wavelength[ 1, num_points_per_band + wl_idx ] *
			forward_e_fields_wavelength[ num_points_per_band + wl_idx ] ),
			axis=0 )

	return ( total_norm * gradient_base )


def splitting_contrast_fom(
	normalized_intensity_focal_point_wavelength ):

	num_total_points = 2 * num_points_per_band
	total_norm = 1.0 / num_total_points

	num_wavelengths = num_points_per_band

	contrast_low = 0
	contrast_high = 0
	for wl_idx in range( 0, num_wavelengths ):
		contrast_low += normalized_intensity_focal_point_wavelength[ 0, wl_idx ] / ( normalized_intensity_focal_point_wavelength[ 0, wl_idx + num_points_per_band ] + regularization )
		contrast_high += normalized_intensity_focal_point_wavelength[ 1, wl_idx + num_points_per_band ] / ( normalized_intensity_focal_point_wavelength[ 1, wl_idx ] + regularization )

	print(contrast_low)
	print(contrast_high)
	print()

	return total_norm * np.array( [ contrast_low, contrast_high ] )

def splitting_contrast_gradient(
	cur_fom,
	conjugate_weighting_focal_point_wavelength,
	normalized_intensity_focal_point_wavelength,
	forward_e_fields_wavelength,
	adjoint_e_fields_focal_point_wavelength ):

	num_fom = len( cur_fom )
	fom_weighting = ( 2.0 / num_fom ) - cur_fom**2 / np.sum( cur_fom**2 )
	if np.min( fom_weighting ) < 0:
		fom_weighting -= np.min( fom_weighting )
		fom_weighting /= np.sum( fom_weighting )

	print(fom_weighting)
	print("\n\n")

	num_total_points = num_design_frequency_points
	total_norm = 1.0 / num_total_points

	fields_shape = forward_e_fields_wavelength.shape
	gradient_base_low = np.zeros( fields_shape[ 2 : ], dtype=np.complex )
	gradient_base_high = np.zeros( fields_shape[ 2 : ], dtype=np.complex )

	num_wavelengths = num_points_per_band

	for wl_idx in range( 0, num_wavelengths ):
		gradient_base_low += np.sum(
			( conjugate_weighting_focal_point_wavelength[ 0, wl_idx ] * adjoint_e_fields_focal_point_wavelength[ 0, wl_idx ] * forward_e_fields_wavelength[ wl_idx ] ) /
			( normalized_intensity_focal_point_wavelength[ 0, wl_idx + num_points_per_band ] + regularization ), axis=0 )

		gradient_base_low += np.sum(
			( ( -1 ) * normalized_intensity_focal_point_wavelength[ 1, wl_idx + num_points_per_band ] *
			conjugate_weighting_focal_point_wavelength[ 1, wl_idx ] * adjoint_e_fields_focal_point_wavelength[ 1, wl_idx ] * forward_e_fields_wavelength[ wl_idx + num_points_per_band ] ) /
			( normalized_intensity_focal_point_wavelength[ 1, wl_idx ] + regularization )**2, axis=0 )

		gradient_base_high += np.sum(
			( conjugate_weighting_focal_point_wavelength[ 1, wl_idx + num_points_per_band ] * adjoint_e_fields_focal_point_wavelength[ 1, wl_idx + num_points_per_band ] * forward_e_fields_wavelength[ wl_idx + num_points_per_band ] ) /
			( normalized_intensity_focal_point_wavelength[ 1, wl_idx ] + regularization ), axis=0 )

		gradient_base_high += np.sum(
			( ( -1 ) * normalized_intensity_focal_point_wavelength[ 0, wl_idx ] *
			conjugate_weighting_focal_point_wavelength[ 0, wl_idx + num_points_per_band ] * adjoint_e_fields_focal_point_wavelength[ 0, wl_idx + num_points_per_band ] * forward_e_fields_wavelength[ wl_idx ] ) /
			( normalized_intensity_focal_point_wavelength[ 0, wl_idx + num_points_per_band ] + regularization )**2, axis=0 )

	return ( total_norm * ( fom_weighting[ 0 ] * gradient_base_low + fom_weighting[ 1 ] * gradient_base_high ) )

def contrast_figure_of_merit( normalized_intensity_focal_point_wavelength ):
	norm_intensity_shape = normalized_intensity_focal_point_wavelength.shape
	num_focal_spots = norm_intensity_shape[ 0 ]
	num_wavelengths = norm_intensity_shape[ 1 ]

	contrast = 0
	for wl_idx in range( 0, num_wavelengths ):
		contrast_wl = 0
		for focal_pt in range( 0, num_focal_spots ):
			
			contrast_denominator = 0
			for other_focal_pt in range( 0, num_focal_spots ):
				if other_focal_pt == focal_pt:
					continue

				contrast_denominator += normalized_intensity_focal_point_wavelength[ other_focal_pt, wl_idx ]
			
			contrast_denominator += regularization

			contrast_numerator = normalized_intensity_focal_point_wavelength[ focal_pt, wl_idx ]
		
			contrast_wl += np.exp( alpha * ( contrast_numerator / contrast_denominator ) )

		contrast += ( 1.0 / alpha ) * np.log( contrast_wl )
		
	return contrast

def contrast_gradient(
	conjugate_weighting_focal_point_wavelength,
	normalized_intensity_focal_point_wavelength,
	forward_e_fields_wavelength,
	adjoint_e_fields_focal_point_wavelength ):

	conjugate_weighting_shape = conjugate_weighting_focal_point_wavelength.shape
	num_focal_spots = conjugate_weighting_shape[ 0 ]
	num_wavelengths = conjugate_weighting_shape[ 1 ]

	fields_shape = forward_e_fields.shape
	
	gradient_base = np.zeros( fields_shape[ 2 : ], dtype=np.complex )

	gradient_weightings = np.zeros( ( num_focal_spots, num_wavelengths ) )
	contrast_denominators = np.zeros( ( num_focal_spots, num_wavelengths ) )

	for wl_idx in range( 0, num_wavelengths ):
		contrast_wl = 0
		for focal_pt in range( 0, num_focal_spots ):
			
			contrast_denominator = 0
			for other_focal_pt in range( 0, num_focal_spots ):
				if other_focal_pt == focal_pt:
					continue

				contrast_denominator += normalized_intensity_focal_point_wavelength[ other_focal_pt, wl_idx ]
			
			contrast_denominator += regularization
			contrast_denominators[ focal_pt, wl_idx ] = contrast_denominator

			contrast_numerator = normalized_intensity_focal_point_wavelength[ focal_pt, wl_idx ]
			contrast_wl += np.exp( alpha * ( contrast_numerator / contrast_denominator ) )
			gradient_weightings[ focal_pt, wl_idx ] = np.exp( alpha * ( contrast_numerator / contrast_denominator ) )

		gradient_weightings[ :, wl_idx ] /= contrast_wl

	for wl_idx in range( 0, num_wavelengths ):	
		for focal_pt in range( 0, num_focal_spots ):
			
			contrast_denominator = contrast_denominators[ focal_pt, wl_idx ]

			gradient_base += gradient_weightings[ focal_pt, wl_idx ] * np.sum(
				( conjugate_weighting_focal_point_wavelength[ focal_pt, wl_idx ] * forward_e_fields_wavelength[ wl_idx ] * adjoint_e_fields_focal_point_wavelength[ focal_pt, wl_idx ] ) /
				contrast_denominator,
				axis=0 )

			for other_focal_pt in range( 0, num_focal_spots ):
				if other_focal_pt == focal_pt:
					continue

				gradient_base += (-1) * gradient_weightings[ other_focal_pt, wl_idx ] * np.sum(
					( conjugate_weighting_focal_point_wavelength[ focal_pt, wl_idx ] * normalized_intensity_focal_point_wavelength[ other_focal_pt, wl_idx ] *
					forward_e_fields_wavelength[ wl_idx ] * adjoint_e_fields_focal_point_wavelength[ focal_pt, wl_idx ] ) /
					contrast_denominators[ other_focal_pt, wl_idx ]**2,
					axis=0 )

	return gradient_base


gaussian_normalization = np.zeros( num_points_per_band )
middle_point = num_points_per_band / 2.
spacing = 1. / ( num_points_per_band - 1 )
half_bandwidth = 0.4 * num_points_per_band

for wl_idx in range( 0, num_points_per_band ):
	gaussian_normalization[ wl_idx ] =  ( 1. / half_bandwidth ) * np.sqrt( 1 / ( 2 * np.pi ) ) * np.exp( -0.5 * ( wl_idx - middle_point )**2 / ( half_bandwidth**2 ) )
	
gaussian_normalization /= np.sum( gaussian_normalization )
gaussian_normalization_all = np.array( [ gaussian_normalization for i in range( 0, num_bands ) ] ).flatten()

#
# Run the optimization
#
if eval_binarized:
	disable_all_sources()
	forward_sources[ 0 ].enabled = 1
	fdtd_hook.run()
	sys.exit( 0 )

# reversed_field_shape = [device_voxels_lateral, designable_device_voxels_vertical, 1]
# random_gradient = np.random.random( reversed_field_shape )

# update_lsfs( random_gradient, random_gradient )


for epoch in range(start_epoch, num_epochs):

	for device_layer_idx in range( 0, len( bayer_filters ) ):
		bayer_filters[ device_layer_idx ].update_filters( epoch )

	for iteration in range(0, num_iterations_per_epoch):

		average_binarization = 0
		for device_layer_idx in range( 0, len( bayer_filters ) ):
			bayer_filter_density = bayer_filters[ device_layer_idx ].get_design_variable()
			average_binarization += ( 1. / len( bayer_filters ) ) * np.mean( np.abs( bayer_filter_density - 0.5 ) ) / 0.5

		average_binarization_evolution[ epoch, iteration ] = average_binarization

		print("Working on epoch " + str(epoch) + " and iteration " + str(iteration))

		reversed_field_shape = [1, designable_device_voxels_vertical, device_voxels_lateral]
		reversed_field_shape_with_pol = [num_polarizations, 1, designable_device_voxels_vertical, device_voxels_lateral]
		xy_polarized_gradients_by_pol = np.zeros(reversed_field_shape_with_pol, dtype=np.complex)
		xy_polarized_gradients = np.zeros(reversed_field_shape, dtype=np.complex)
		figure_of_merit_by_pol = np.zeros( num_polarizations )

		# Import all the bayer filters
		if optimize_via_level_set:
			import_lsfs()
		else:
			import_bayer_filters()

		for pol_idx in range( 0, num_polarizations ):

			affected_coords = affected_coords_by_polarization[ pol_idx ]

			#
			# Step 1: Run the forward optimization for both x- and y-polarized plane waves.
			#
			disable_all_sources()
			forward_sources[ pol_idx ].enabled = 1
			fdtd_hook.run()

			# if iteration > 4:
			# 	print(figure_of_merit_evolution)
			# 	sys.exit(0)

			forward_e_fields = get_complex_monitor_data(design_efield_monitor['name'], 'E')

			focal_data = []
			for adj_src_idx in range(0, num_adjoint_sources):
				focal_data.append(
					get_complex_monitor_data(focal_monitors[adj_src_idx]['name'], 'E') )

			#
			# Step 2: Compute the figure of merit
			#
			normalized_intensity_focal_point_wavelength = np.zeros( ( num_focal_spots, num_design_frequency_points ) )
			conjugate_weighting_focal_point_wavelength = np.zeros( ( 3, num_focal_spots, num_design_frequency_points ), dtype=np.complex )

			figure_of_merit_total = np.zeros( num_design_frequency_points )
			conjugate_weighting_wavelength = np.zeros( ( 3, num_design_frequency_points ), dtype=np.complex )

			for focal_idx in range(0, num_focal_spots):
				spectral_indices = spectral_focal_plane_map[ focal_idx ]

				for wl_idx in range( 0, num_points_per_band ):

					for coord_idx in range( 0, len( affected_coords ) ):
						current_coord = affected_coords[ coord_idx ]

						figure_of_merit_total[ wl_idx + spectral_indices[ 0 ] ] += (
							np.sum( np.abs( focal_data[ focal_idx ][ current_coord, wl_idx + spectral_indices[ 0 ], 0, 0, 0 ])**2 )
						) / max_intensity_by_wavelength[ wl_idx + spectral_indices[ 0 ] ]

						conjugate_weighting_wavelength[ current_coord, wl_idx + spectral_indices[ 0 ] ] = np.conj(
							focal_data[ focal_idx ][ current_coord, wl_idx + spectral_indices[ 0 ], 0, 0, 0 ] / max_intensity_by_wavelength[ wl_idx + spectral_indices[ 0 ] ] )
		
			fom_weighting = ( 2. / len( figure_of_merit_total ) ) - figure_of_merit_total**2 / np.sum( figure_of_merit_total**2 )
			fom_weighting = np.maximum( fom_weighting, 0 )
			fom_weighting /= np.sum( fom_weighting )

			figure_of_merit = np.sum( gaussian_normalization_all * figure_of_merit_total )
			print('figure of merit = ' + str( figure_of_merit ) )

			figure_of_merit_by_pol[ pol_idx ] = figure_of_merit

			# print(figure_of_merit)

			figure_of_merit_evolution[epoch, iteration] += ( 1. / num_polarizations ) * figure_of_merit
			np.save(projects_directory_location + "/figure_of_merit.npy", figure_of_merit_evolution)
			np.save(projects_directory_location + "/average_binarization_evolution.npy", average_binarization_evolution)

			#
			# Step 3: Run all the adjoint optimizations for both x- and y-polarized adjoint sources and use the results to compute the
			# gradients for x- and y-polarized forward sources.
			#
			polarized_gradient = np.zeros(xy_polarized_gradients.shape, dtype=np.complex)

			current_index = np.real( get_non_struct_data( design_index_monitor[ 'name' ], 'index_x' ) )
			current_permittivity = np.sqrt( np.squeeze( current_index ) )

			for coord_idx in range( 0, len( affected_coords ) ):
				current_coord = affected_coords[ coord_idx ]
				for adj_src_idx in range( 0, num_adjoint_sources ):
					disable_all_sources()
					(adjoint_sources[current_coord][adj_src_idx]).enabled = 1
					fdtd_hook.run()

					adjoint_e_fields = get_complex_monitor_data(design_efield_monitor['name'], 'E')

					spectral_indices = spectral_focal_plane_map[ adj_src_idx ]

					if optimize_via_level_set:
						for spectral_idx in range(0, num_points_per_band):
							for polarization_idx in range( 0, 3 ):
								# x-coordinate is the perpendicular coorinate to the level set boundary that can be actually changed
								if polarization_idx == 0:
									polarized_gradient += ( ( ( 1. / min_real_permittivity ) - ( 1. / max_real_permittivity ) ) *
										gaussian_normalization_all[ spectral_idx % num_points_per_band ] * ( conjugate_weighting_wavelength[current_coord, spectral_indices[0] + spectral_idx] * fom_weighting[spectral_indices[0] + spectral_idx] ) *
										current_permittivity * adjoint_e_fields[polarization_idx, spectral_indices[0] + spectral_idx, :, :, :] *
										current_permittivity * forward_e_fields[polarization_idx, spectral_indices[0] + spectral_idx, :, :, :]
									)
								else:
									polarized_gradient += ( ( max_real_permittivity - min_real_permittivity ) *
										gaussian_normalization_all[ spectral_idx % num_points_per_band ] * (conjugate_weighting_wavelength[current_coord, spectral_indices[0] + spectral_idx] * fom_weighting[spectral_indices[0] + spectral_idx]) *
										current_permittivity * adjoint_e_fields[polarization_idx, spectral_indices[0] + spectral_idx, :, :, :] *
										current_permittivity * forward_e_fields[polarization_idx, spectral_indices[0] + spectral_idx, :, :, :]
									)
					else:
						for spectral_idx in range(0, num_points_per_band):
							polarized_gradient += np.sum(
								gaussian_normalization_all[ spectral_idx % num_points_per_band ] * (conjugate_weighting_wavelength[current_coord, spectral_indices[0] + spectral_idx] * fom_weighting[spectral_indices[0] + spectral_idx]) *
								adjoint_e_fields[:, spectral_indices[0] + spectral_idx, :, :, :] *
								forward_e_fields[:, spectral_indices[0] + spectral_idx, :, :, :],
								axis=0)
				
			xy_polarized_gradients_by_pol[ pol_idx ] = polarized_gradient
		

		weight_grad_by_pol = ( 2. / num_polarizations ) - figure_of_merit_by_pol**2 / np.sum( figure_of_merit_by_pol**2 )
		weight_grad_by_pol = np.maximum( weight_grad_by_pol, 0 )
		weight_grad_by_pol /= np.sum( weight_grad_by_pol )
		# weight_grad_by_pol = [ 1, 0 ]
		# weight_grad_by_pol = [ 0, 1 ]

		print(figure_of_merit_by_pol)
		print(weight_grad_by_pol)
		print()

		for pol_idx in range( 0, num_polarizations ):
			xy_polarized_gradients += weight_grad_by_pol[ pol_idx ] * xy_polarized_gradients_by_pol[ pol_idx ]

		#
		# Step 4: Step the design variable.
		#
		device_gradient_real = 2 * np.real( xy_polarized_gradients )
		device_gradient_imag = 2 * np.imag( xy_polarized_gradients )
		# Because of how the data transfer happens between Lumerical and here, the axes are ordered [z, y, x] when we expect them to be
		# [x, y, z].  For this reason, we swap the 0th and 2nd axes to get them into the expected ordering.
		device_gradient_real = np.swapaxes(device_gradient_real, 0, 2)
		device_gradient_imag = np.swapaxes(device_gradient_imag, 0, 2)

		step_size = step_size_start

		if use_adaptive_step_size:
			step_size = adaptive_step_size

		do_simulated_annealing = use_simulated_annealing and ( iteration < simulated_annealing_cutoff_iteration )
		current_temperature = temperature_scaling / np.log( iteration + 2 )

		max_density_change = max_density_change_epoch_start + ( iteration / ( num_iterations_per_epoch - 1 ) ) * ( max_density_change_epoch_end - max_density_change_epoch_start )
		print("max density change is " + str(max_density_change))

		if optimize_via_level_set:
			update_lsfs( -device_gradient_real, -device_gradient_imag )
		else:
			adaptive_step_size *= update_bayer_filters( -device_gradient_real, -device_gradient_imag, max_density_change, do_simulated_annealing, current_temperature )

		# adaptive_step_size *= update_bayer_filters( -device_gradient_real, -device_gradient_imag, step_size, do_simulated_annealing, current_temperature )

		step_size_evolution[epoch][iteration] = step_size

		if not optimize_via_level_set:
			np.save(projects_directory_location + '/device_gradient_real.npy', device_gradient_real)
			np.save(projects_directory_location + '/device_gradient_imag.npy', device_gradient_imag)
			np.save(projects_directory_location + "/step_size_evolution.npy", step_size_evolution)

	if not optimize_via_level_set:
		shutil.copy( projects_directory_location + "/optimization.fsp", projects_directory_location + "/optimization_" + str( epoch ) + ".fsp" )
		for device_layer_idx in range( 0, len( bayer_filters ) ):
			shutil.copy( projects_directory_location + "/cur_design_variable_" + str(device_layer_idx) + ".npy", projects_directory_location + "/cur_design_variable_" + str( device_layer_idx ) + "_" + str( epoch ) + ".npy" )
