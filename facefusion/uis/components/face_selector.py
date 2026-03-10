from typing import List, Optional, Tuple

import cv2
import gradio
import numpy
import os
from gradio_rangeslider import RangeSlider

import facefusion.choices
from facefusion import state_manager, translator
from facefusion.common_helper import calculate_float_step, calculate_int_step, get_first
from facefusion.face_analyser import get_many_faces
from facefusion.face_selector import sort_and_filter_faces
from facefusion.face_store import clear_static_faces
from facefusion.filesystem import filter_image_paths, is_image, is_video
from facefusion.types import FaceSelectorMode, FaceSelectorOrder, Gender, Race, VisionFrame
from facefusion.uis.core import get_ui_component, get_ui_components, register_ui_component
from facefusion.uis.types import ComponentOptions
from facefusion.uis.ui_helper import convert_str_none
from facefusion.vision import fit_cover_frame, read_static_image, read_video_frame

FACE_SELECTOR_MODE_DROPDOWN : Optional[gradio.Dropdown] = None
FACE_SELECTOR_ORDER_DROPDOWN : Optional[gradio.Dropdown] = None
FACE_SELECTOR_GENDER_DROPDOWN : Optional[gradio.Dropdown] = None
FACE_SELECTOR_RACE_DROPDOWN : Optional[gradio.Dropdown] = None
FACE_SELECTOR_AGE_RANGE_SLIDER : Optional[RangeSlider] = None
REFERENCE_FACE_POSITION_GALLERY : Optional[gradio.Gallery] = None
REFERENCE_FACE_DISTANCE_SLIDER : Optional[gradio.Slider] = None
REFERENCE_FACE_PATHS_FILE : Optional[gradio.File] = None
MULTI_FACE_PAIRS_GALLERY : Optional[gradio.Gallery] = None


def render() -> None:
	global FACE_SELECTOR_MODE_DROPDOWN
	global FACE_SELECTOR_ORDER_DROPDOWN
	global FACE_SELECTOR_GENDER_DROPDOWN
	global FACE_SELECTOR_RACE_DROPDOWN
	global FACE_SELECTOR_AGE_RANGE_SLIDER
	global REFERENCE_FACE_POSITION_GALLERY
	global REFERENCE_FACE_DISTANCE_SLIDER
	global REFERENCE_FACE_PATHS_FILE
	global MULTI_FACE_PAIRS_GALLERY

	reference_face_gallery_options : ComponentOptions =\
	{
		'label': translator.get('uis.reference_face_gallery'),
		'object_fit': 'cover',
		'columns': 7,
		'allow_preview': False,
		'elem_classes': 'box-face-selector',
		'visible': 'reference' in state_manager.get_item('face_selector_mode')
	}
	if is_image(state_manager.get_item('target_path')):
		target_vision_frame = read_static_image(state_manager.get_item('target_path'))
		reference_face_gallery_options['value'] = extract_gallery_frames(target_vision_frame)
	if is_video(state_manager.get_item('target_path')):
		target_vision_frame = read_video_frame(state_manager.get_item('target_path'), state_manager.get_item('reference_frame_number'))
		reference_face_gallery_options['value'] = extract_gallery_frames(target_vision_frame)
	FACE_SELECTOR_MODE_DROPDOWN = gradio.Dropdown(
		label = translator.get('uis.face_selector_mode_dropdown'),
		choices = facefusion.choices.face_selector_modes,
		value = state_manager.get_item('face_selector_mode')
	)
	REFERENCE_FACE_POSITION_GALLERY = gradio.Gallery(**reference_face_gallery_options)
	with gradio.Group():
		with gradio.Row():
			FACE_SELECTOR_ORDER_DROPDOWN = gradio.Dropdown(
				label = translator.get('uis.face_selector_order_dropdown'),
				choices = facefusion.choices.face_selector_orders,
				value = state_manager.get_item('face_selector_order')
			)
			FACE_SELECTOR_GENDER_DROPDOWN = gradio.Dropdown(
				label = translator.get('uis.face_selector_gender_dropdown'),
				choices = [ 'none' ] + facefusion.choices.face_selector_genders,
				value = state_manager.get_item('face_selector_gender') or 'none'
			)
			FACE_SELECTOR_RACE_DROPDOWN = gradio.Dropdown(
				label = translator.get('uis.face_selector_race_dropdown'),
				choices = [ 'none' ] + facefusion.choices.face_selector_races,
				value = state_manager.get_item('face_selector_race') or 'none'
			)
		with gradio.Row():
			face_selector_age_start = state_manager.get_item('face_selector_age_start') or facefusion.choices.face_selector_age_range[0]
			face_selector_age_end = state_manager.get_item('face_selector_age_end') or facefusion.choices.face_selector_age_range[-1]
			FACE_SELECTOR_AGE_RANGE_SLIDER = RangeSlider(
				label = translator.get('uis.face_selector_age_range_slider'),
				minimum = facefusion.choices.face_selector_age_range[0],
				maximum = facefusion.choices.face_selector_age_range[-1],
				value = (face_selector_age_start, face_selector_age_end),
				step = calculate_int_step(facefusion.choices.face_selector_age_range)
			)
	REFERENCE_FACE_DISTANCE_SLIDER = gradio.Slider(
		label = translator.get('uis.reference_face_distance_slider'),
		value = state_manager.get_item('reference_face_distance'),
		step = calculate_float_step(facefusion.choices.reference_face_distance_range),
		minimum = facefusion.choices.reference_face_distance_range[0],
		maximum = facefusion.choices.reference_face_distance_range[-1],
		visible = 'reference' in state_manager.get_item('face_selector_mode')
	)
	reference_face_paths = state_manager.get_item('reference_face_paths')
	REFERENCE_FACE_PATHS_FILE = gradio.File(
		label = 'Multi-Face Reference Images (one per target face, paired with source images in order)',
		file_count = 'multiple',
		file_types = [ 'image' ],
		value = reference_face_paths if reference_face_paths else None,
		visible = 'reference' in state_manager.get_item('face_selector_mode')
	)
	is_multi_face = bool(reference_face_paths) and 'reference' in state_manager.get_item('face_selector_mode')
	MULTI_FACE_PAIRS_GALLERY = gradio.Gallery(
		label = 'Multi-Face Pairs Preview (Reference → Source)',
		value = extract_multi_face_pairs_preview() if is_multi_face else None,
		object_fit = 'cover',
		columns = 4,
		allow_preview = True,
		visible = is_multi_face
	)
	register_ui_component('face_selector_mode_dropdown', FACE_SELECTOR_MODE_DROPDOWN)
	register_ui_component('face_selector_order_dropdown', FACE_SELECTOR_ORDER_DROPDOWN)
	register_ui_component('face_selector_gender_dropdown', FACE_SELECTOR_GENDER_DROPDOWN)
	register_ui_component('face_selector_race_dropdown', FACE_SELECTOR_RACE_DROPDOWN)
	register_ui_component('face_selector_age_range_slider', FACE_SELECTOR_AGE_RANGE_SLIDER)
	register_ui_component('reference_face_position_gallery', REFERENCE_FACE_POSITION_GALLERY)
	register_ui_component('reference_face_distance_slider', REFERENCE_FACE_DISTANCE_SLIDER)
	register_ui_component('reference_face_paths_file', REFERENCE_FACE_PATHS_FILE)
	register_ui_component('multi_face_pairs_gallery', MULTI_FACE_PAIRS_GALLERY)


def listen() -> None:
	FACE_SELECTOR_MODE_DROPDOWN.change(update_face_selector_mode, inputs = FACE_SELECTOR_MODE_DROPDOWN, outputs = [ REFERENCE_FACE_POSITION_GALLERY, REFERENCE_FACE_DISTANCE_SLIDER, REFERENCE_FACE_PATHS_FILE, MULTI_FACE_PAIRS_GALLERY ])
	FACE_SELECTOR_ORDER_DROPDOWN.change(update_face_selector_order, inputs = FACE_SELECTOR_ORDER_DROPDOWN, outputs = REFERENCE_FACE_POSITION_GALLERY)
	FACE_SELECTOR_GENDER_DROPDOWN.change(update_face_selector_gender, inputs = FACE_SELECTOR_GENDER_DROPDOWN, outputs = REFERENCE_FACE_POSITION_GALLERY)
	FACE_SELECTOR_RACE_DROPDOWN.change(update_face_selector_race, inputs = FACE_SELECTOR_RACE_DROPDOWN, outputs = REFERENCE_FACE_POSITION_GALLERY)
	FACE_SELECTOR_AGE_RANGE_SLIDER.release(update_face_selector_age_range, inputs = FACE_SELECTOR_AGE_RANGE_SLIDER, outputs = REFERENCE_FACE_POSITION_GALLERY)
	REFERENCE_FACE_DISTANCE_SLIDER.release(update_reference_face_distance, inputs = REFERENCE_FACE_DISTANCE_SLIDER)
	REFERENCE_FACE_PATHS_FILE.change(update_reference_face_paths, inputs = REFERENCE_FACE_PATHS_FILE, outputs = MULTI_FACE_PAIRS_GALLERY)

	preview_frame_slider = get_ui_component('preview_frame_slider')
	if preview_frame_slider:
		REFERENCE_FACE_POSITION_GALLERY.select(update_reference_frame_number, inputs = preview_frame_slider)
		REFERENCE_FACE_POSITION_GALLERY.select(update_reference_face_position)

	for ui_component in get_ui_components(
	[
		'target_image',
		'target_video'
	]):
		for method in [ 'change', 'clear' ]:
			getattr(ui_component, method)(clear_reference_frame_number)
			getattr(ui_component, method)(clear_reference_face_position)
			getattr(ui_component, method)(update_reference_position_gallery, outputs = REFERENCE_FACE_POSITION_GALLERY)

	for ui_component in get_ui_components(
	[
		'face_detector_model_dropdown',
		'face_detector_size_dropdown',
		'face_detector_angles_checkbox_group'
	]):
		ui_component.change(clear_and_update_reference_position_gallery, outputs = REFERENCE_FACE_POSITION_GALLERY)

	face_detector_score_slider = get_ui_component('face_detector_score_slider')
	if face_detector_score_slider:
		face_detector_score_slider.release(update_reference_position_gallery, outputs = REFERENCE_FACE_POSITION_GALLERY)

	preview_frame_slider = get_ui_component('preview_frame_slider')
	if preview_frame_slider:
		for method in [ 'change', 'release' ]:
			getattr(preview_frame_slider, method)(update_reference_position_gallery_and_pairs, inputs = preview_frame_slider, outputs = [ REFERENCE_FACE_POSITION_GALLERY, MULTI_FACE_PAIRS_GALLERY ], show_progress = 'hidden')


def update_face_selector_mode(face_selector_mode : FaceSelectorMode) -> Tuple[gradio.Gallery, gradio.Slider, gradio.File, gradio.Gallery]:
	state_manager.set_item('face_selector_mode', face_selector_mode)
	if face_selector_mode == 'many':
		return gradio.Gallery(visible = False), gradio.Slider(visible = False), gradio.File(visible = False), gradio.Gallery(visible = False)
	if face_selector_mode == 'one':
		return gradio.Gallery(visible = False), gradio.Slider(visible = False), gradio.File(visible = False), gradio.Gallery(visible = False)
	if face_selector_mode == 'reference':
		reference_face_paths = state_manager.get_item('reference_face_paths')
		is_multi = bool(reference_face_paths)
		pairs_value = extract_multi_face_pairs_preview() if is_multi else None
		return gradio.Gallery(visible = True), gradio.Slider(visible = True), gradio.File(visible = True), gradio.Gallery(value = pairs_value, visible = is_multi)


def update_face_selector_order(face_analyser_order : FaceSelectorOrder) -> gradio.Gallery:
	state_manager.set_item('face_selector_order', convert_str_none(face_analyser_order))
	return update_reference_position_gallery()


def update_face_selector_gender(face_selector_gender : Gender) -> gradio.Gallery:
	state_manager.set_item('face_selector_gender', convert_str_none(face_selector_gender))
	return update_reference_position_gallery()


def update_face_selector_race(face_selector_race : Race) -> gradio.Gallery:
	state_manager.set_item('face_selector_race', convert_str_none(face_selector_race))
	return update_reference_position_gallery()


def update_face_selector_age_range(face_selector_age_range : Tuple[float, float]) -> gradio.Gallery:
	face_selector_age_start, face_selector_age_end = face_selector_age_range
	state_manager.set_item('face_selector_age_start', int(face_selector_age_start))
	state_manager.set_item('face_selector_age_end', int(face_selector_age_end))
	return update_reference_position_gallery()


def update_reference_face_position(event : gradio.SelectData) -> None:
	state_manager.set_item('reference_face_position', event.index)


def clear_reference_face_position() -> None:
	state_manager.set_item('reference_face_position', 0)


def update_reference_face_distance(reference_face_distance : float) -> None:
	state_manager.set_item('reference_face_distance', reference_face_distance)


def update_reference_face_paths(files : List) -> gradio.Gallery:
	if files:
		file_names = [ file.name for file in files ]
		state_manager.set_item('reference_face_paths', file_names)
		pairs = extract_multi_face_pairs_preview()
		return gradio.Gallery(value = pairs, visible = True)
	else:
		state_manager.set_item('reference_face_paths', None)
		return gradio.Gallery(value = None, visible = False)


def update_reference_frame_number(reference_frame_number : int = 0) -> None:
	state_manager.set_item('reference_frame_number', reference_frame_number)


def clear_reference_frame_number() -> None:
	state_manager.set_item('reference_frame_number', 0)


def clear_and_update_reference_position_gallery() -> gradio.Gallery:
	clear_static_faces()
	return update_reference_position_gallery()


def update_reference_position_gallery(frame_number : int = 0) -> gradio.Gallery:
	gallery_vision_frames = []
	if is_image(state_manager.get_item('target_path')):
		target_vision_frame = read_static_image(state_manager.get_item('target_path'))
		gallery_vision_frames = extract_gallery_frames(target_vision_frame)
	if is_video(state_manager.get_item('target_path')):
		target_vision_frame = read_video_frame(state_manager.get_item('target_path'), frame_number)
		gallery_vision_frames = extract_gallery_frames(target_vision_frame)
	if gallery_vision_frames:
		return gradio.Gallery(value = gallery_vision_frames)
	return gradio.Gallery(value = None)


def update_reference_position_gallery_and_pairs(frame_number : int = 0) -> Tuple[gradio.Gallery, gradio.Gallery]:
	position_gallery = update_reference_position_gallery(frame_number)
	reference_face_paths = state_manager.get_item('reference_face_paths')
	if reference_face_paths:
		pairs = extract_multi_face_pairs_preview(frame_number)
		return position_gallery, gradio.Gallery(value = pairs, visible = True)
	return position_gallery, gradio.Gallery(value = None, visible = False)


def extract_gallery_frames(target_vision_frame : VisionFrame) -> List[VisionFrame]:
	gallery_vision_frames = []
	faces = get_many_faces([ target_vision_frame ])
	faces = sort_and_filter_faces(faces)

	for face in faces:
		start_x, start_y, end_x, end_y = map(int, face.bounding_box)
		padding_x = int((end_x - start_x) * 0.25)
		padding_y = int((end_y - start_y) * 0.25)
		start_x = max(0, start_x - padding_x)
		start_y = max(0, start_y - padding_y)
		end_x = max(0, end_x + padding_x)
		end_y = max(0, end_y + padding_y)
		crop_vision_frame = target_vision_frame[start_y:end_y, start_x:end_x]
		crop_vision_frame = fit_cover_frame(crop_vision_frame, (128, 128))
		crop_vision_frame = cv2.cvtColor(crop_vision_frame, cv2.COLOR_BGR2RGB)
		gallery_vision_frames.append(crop_vision_frame)
	return gallery_vision_frames


def extract_multi_face_pairs_preview(frame_number : int = 0) -> List[Tuple[VisionFrame, str]]:
	"""Build a flat list of (image, caption) pairs: for each index,
	show the matched face crop from the target frame followed by the
	source face crop, so users can visually verify every ref→source pair."""
	from facefusion.face_analyser import get_one_face
	from facefusion.face_selector import find_match_faces, sort_faces_by_order

	reference_face_paths = state_manager.get_item('reference_face_paths')
	source_paths = filter_image_paths(state_manager.get_item('source_paths') or [])
	reference_face_distance = state_manager.get_item('reference_face_distance') or 0.3

	if not reference_face_paths:
		return []

	# read target frame
	target_vision_frame = None
	if is_image(state_manager.get_item('target_path')):
		target_vision_frame = read_static_image(state_manager.get_item('target_path'))
	elif is_video(state_manager.get_item('target_path')):
		target_vision_frame = read_video_frame(state_manager.get_item('target_path'), frame_number)

	target_faces = get_many_faces([ target_vision_frame ]) if target_vision_frame is not None else []

	gallery_frames = []
	for index, ref_path in enumerate(reference_face_paths):
		if not os.path.isfile(ref_path):
			continue

		# reference face crop (from the ref image itself, not the video)
		ref_vision_frame = read_static_image(ref_path)
		ref_faces = get_many_faces([ ref_vision_frame ])
		ref_faces = sort_faces_by_order(ref_faces, state_manager.get_item('face_selector_order') or 'large-small')
		ref_face = get_one_face(ref_faces, 0)

		ref_thumb = _crop_face_thumb(ref_vision_frame, ref_face) if ref_face else _placeholder_thumb()
		gallery_frames.append((ref_thumb, f'#{index + 1} Reference (target char)'))

		# matched face from the current target frame
		if ref_face and target_faces:
			matched = find_match_faces([ ref_face ], target_faces, reference_face_distance)
			matched_face = get_first(matched)
			matched_thumb = _crop_face_thumb(target_vision_frame, matched_face) if (matched_face and target_vision_frame is not None) else _placeholder_thumb()
		else:
			matched_thumb = _placeholder_thumb()
		gallery_frames.append((matched_thumb, f'#{index + 1} Matched in video'))

		# source face (the face to swap in)
		if index < len(source_paths) and os.path.isfile(source_paths[index]):
			src_frame = read_static_image(source_paths[index])
			src_faces = get_many_faces([ src_frame ])
			src_faces = sort_faces_by_order(src_faces, 'large-small')
			src_face = get_first(src_faces)
			src_thumb = _crop_face_thumb(src_frame, src_face) if src_face else _placeholder_thumb()
		else:
			src_thumb = _placeholder_thumb()
		gallery_frames.append((src_thumb, f'#{index + 1} Source (swap in)'))

	return gallery_frames


def _crop_face_thumb(vision_frame : VisionFrame, face) -> VisionFrame:
	start_x, start_y, end_x, end_y = map(int, face.bounding_box)
	padding_x = int((end_x - start_x) * 0.25)
	padding_y = int((end_y - start_y) * 0.25)
	start_x = max(0, start_x - padding_x)
	start_y = max(0, start_y - padding_y)
	end_x = max(0, end_x + padding_x)
	end_y = max(0, end_y + padding_y)
	crop = vision_frame[start_y:end_y, start_x:end_x]
	crop = fit_cover_frame(crop, (128, 128))
	return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)


def _placeholder_thumb() -> VisionFrame:
	placeholder = numpy.zeros((128, 128, 3), dtype = numpy.uint8)
	cv2.putText(placeholder, '?', (48, 80), cv2.FONT_HERSHEY_SIMPLEX, 2, (128, 128, 128), 3)
	return placeholder
