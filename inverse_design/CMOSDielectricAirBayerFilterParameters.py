#
# Parameter file for the Bayer Filter Layered Lithography optimization
#

import numpy as np

#
# Files
#
project_name = 'cmos_dielectric_air_etch_passivation_reflective_no_feature_size_no_layering_rgb_2x2xtsmc_um'

#
# Optical
#
background_index = 1.0
device_background_index = 1.3

min_real_permittivity =  0
max_real_permittivity = 1.3**2

min_imag_permittivity = 0
max_imag_permittivity = 0

init_permittivity_0_1_scale = 0.5

focal_length_um = 0.9

#
# Device
#
mesh_spacing_um = 0.025

device_size_lateral_um = 2
# Metal layers from M7 down to M2 (and we will use M6 as a reflector)
# ( 6 * ( 2200 + 950 + 300 + 500 ) + 300 + 500 ) / 10000 = 2.45
designable_size_vertical_um = 2.45
# We will assume just air below this
bottom_metal_reflector_size_vertical_um = 0.13
# Top dielectric stack size we will not be designing for now because feature
# size is pretty large
# ( 6000 + 4000 + 2500 + 750 + 4000 + 750 + 32300 + 1100 + 7250 + 750 + 7750 + 500 + 6200 + 500 ) / 10000 = 7.435
# top_dielectric_stack_size_vertcial_um = 7.435
# for now, just one of the M8 layers
top_dielectric_stack_size_vertcial_um = 0.62

device_size_verical_um = top_dielectric_stack_size_vertcial_um + designable_size_vertical_um + bottom_metal_reflector_size_vertical_um

bottom_metal_reflector_size_vertical_voxels = 1 + int( bottom_metal_reflector_size_vertical_um / mesh_spacing_um )

device_voxels_lateral = 1 + int(device_size_lateral_um / mesh_spacing_um)
designable_device_voxels_vertical = 2 + int(designable_size_vertical_um / mesh_spacing_um)

designable_device_vertical_maximum_um = designable_size_vertical_um
designable_device_vertical_minimum_um = 0


# Passivation and M8/M9 dielectric stack
# Stacks organized as list with lowest layer coming first in the list
# m8_stack_layer_thickness_um = [
# 	0.62, 0.05, 0.775, 0.075 ]
# m8_stack_layer_refractive_index = [
# 	1.45, 2.0, 1.45, 2.0 ]

m8_stack_layer_thickness_um = [ 0.62 ]
m8_stack_layer_refractive_index = [ 1.45 ]

# m9_stack_layer_thickness_um = [
# 	0.725, 0.11, 3.23 ]
# m9_stack_layer_refractive_index = [
# 	1.45, 2.0, 1.45 ]

m9_stack_layer_thickness_um = []
m9_stack_layer_refractive_index = []

# pass_stack_layer_thickness_um = [
# 	0.075, 0.4, 0.075, 0.65, 0.6 ]
# pass_stack_layer_refractive_index = [
# 	2.0, 1.45, 2.0, 1.45, 2.0 ]

pass_stack_layer_thickness_um = []
pass_stack_layer_refractive_index = []


#
# copy so the extend calls following do not modify the memory for the m8 stack variable
#
top_dielectric_layer_thickness_um = m8_stack_layer_thickness_um.copy()
top_dielectric_layer_thickness_um.extend( m9_stack_layer_thickness_um )
top_dielectric_layer_thickness_um.extend( pass_stack_layer_thickness_um )

top_dielectric_layer_refractice_index = m8_stack_layer_refractive_index.copy()
top_dielectric_layer_refractice_index.extend( m9_stack_layer_refractive_index )
top_dielectric_layer_refractice_index.extend( pass_stack_layer_refractive_index )


bottom_metal_reflector_start_um = -bottom_metal_reflector_size_vertical_um
bottom_metal_reflector_end_um = bottom_metal_reflector_start_um + bottom_metal_reflector_size_vertical_um

m8_stack_start_um = bottom_metal_reflector_end_um + designable_size_vertical_um
m8_stack_end_um = m8_stack_start_um + np.sum( m8_stack_layer_thickness_um )

m9_stack_start_um = m8_stack_end_um
m9_stack_end_um = m9_stack_start_um + np.sum( m9_stack_layer_thickness_um )

pass_stack_start_um = m9_stack_end_um
pass_stack_end_um = pass_stack_start_um + np.sum( pass_stack_layer_thickness_um )

dielectric_stack_start_um = m8_stack_start_um
dielectric_stack_end_um = pass_stack_end_um



#
# Spectral
#
lambda_min_um = 0.4
lambda_max_um = 0.7

num_bands = 3
num_points_per_band = 20
num_design_frequency_points = num_bands * num_points_per_band

lambda_values_um = np.linspace(lambda_min_um, lambda_max_um, num_design_frequency_points)
max_intensity_by_wavelength = (device_size_lateral_um**2)**2 / (focal_length_um**2 * lambda_values_um**2)

#
# Fabrication Constraints
#
min_feature_size_um = 0.08
min_feature_size_voxels = min_feature_size_um / mesh_spacing_um
blur_half_width_voxels = int( np.ceil( (min_feature_size_voxels - 1) / 2. ) )

num_vertical_layers = 8

#
# FDTD
#
vertical_gap_size_um = 0.5
lateral_gap_size_um = 0.5

fdtd_region_size_vertical_um = 2 * vertical_gap_size_um + device_size_verical_um + focal_length_um
fdtd_region_size_lateral_um = 2 * lateral_gap_size_um + device_size_lateral_um
fdtd_region_maximum_vertical_um = device_size_verical_um + vertical_gap_size_um + focal_length_um - bottom_metal_reflector_size_vertical_um
fdtd_region_minimum_vertical_um = bottom_metal_reflector_start_um - vertical_gap_size_um

fdtd_region_minimum_vertical_voxels = int( np.ceil(fdtd_region_size_vertical_um / mesh_spacing_um) )
fdtd_region_minimum_lateral_voxels = int( np.ceil(fdtd_region_size_lateral_um / mesh_spacing_um) )

fdtd_region_size_lateral_voxels = int( np.ceil( fdtd_region_size_lateral_um / mesh_spacing_um ) )


fdtd_simulation_time_fs = 2000

#
# Forward Source
#
lateral_aperture_um = 1.05 * device_size_lateral_um
src_maximum_vertical_um = pass_stack_end_um + focal_length_um + 0.5 * vertical_gap_size_um
src_minimum_vertical_um = bottom_metal_reflector_start_um - 0.5 * vertical_gap_size_um

#
# Spectral and polarization selectivity information
#
polarizations_focal_plane_map = [ ['x', 'y'], ['x', 'y'], ['x', 'y'], ['x', 'y'] ]
weight_focal_plane_map = [ 1.0, 1.0, 1.0, 1.0 ]
polarization_name_to_idx = { 'x':0, 'y':1, 'z':2 }
# We are assuming that the data is organized in order of increasing wavelength (i.e. - blue first, red last)
spectral_focal_plane_map = [
	[0, num_points_per_band],
	[num_points_per_band, 2 * num_points_per_band],
	[2 * num_points_per_band, 3 * num_points_per_band],
	[num_points_per_band, 2 * num_points_per_band]
]

#
# Adjoint sources
#
adjoint_vertical_um = pass_stack_end_um + focal_length_um
num_focal_spots = 4
num_adjoint_sources = num_focal_spots
adjoint_x_positions_um = [device_size_lateral_um / 4., -device_size_lateral_um / 4., -device_size_lateral_um / 4., device_size_lateral_um / 4.]
adjoint_y_positions_um = [device_size_lateral_um / 4., device_size_lateral_um / 4., -device_size_lateral_um / 4., -device_size_lateral_um / 4.]

#
# Optimization
#
num_epochs = 1
num_iterations_per_epoch = 75

use_fixed_step_size = True
fixed_step_size = 0.01 * 3 / 4

epoch_start_permittivity_change_max = 0.1
epoch_end_permittivity_change_max = 0.02
epoch_range_permittivity_change_max = epoch_start_permittivity_change_max - epoch_end_permittivity_change_max

epoch_start_permittivity_change_min = 0.05
epoch_end_permittivity_change_min = 0
epoch_range_permittivity_change_min = epoch_start_permittivity_change_min - epoch_end_permittivity_change_min

