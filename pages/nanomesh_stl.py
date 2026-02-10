import streamlit as st

from pathlib import Path
import os
import tempfile

from streamlit_stl import stl_from_file, stl_from_text

from lib.nanomesh import generate_nanomesh_stl


# @st.cache_data(scope ="session")
def generate_nanomesh_stl_bytes(**kwargs) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "nanomesh.stl"
        generate_nanomesh_stl(out_path, **kwargs)
        with open(out_path, "rb") as src_file:
            data = src_file.read()
    return data


color = st.color_picker("Preview color", "#FFAA00")
sheet_w = st.number_input("Sheet width (μm)", min_value=1.0, value=50.0, step=1.0)
sheet_d = st.number_input("Sheet depth (μm)", min_value=1.0, value=20.0, step=1.0)
sheet_t = st.number_input("Sheet thickness (μm)", min_value=0.1, value=0.5, step=0.1)
fiber_diam = st.number_input(
    "Fiber diameter (μm)", min_value=0.01, value=0.2, step=0.01
)
n_fibers = st.number_input("Number of fibers", min_value=1, value=500, step=1)


stl_file = generate_nanomesh_stl_bytes(
    sheet_w=sheet_w,
    sheet_d=sheet_d,
    sheet_t=sheet_t,
    fiber_diam=fiber_diam,
    n_fibers=n_fibers,
)

success = stl_from_text(
    text=stl_file,  # Path to the STL file
    color=color,
    material="material",  # Material of the STL file ('material', 'flat', or 'wireframe')
    # auto_rotate=True,                # Enable auto-rotation of the STL model
    opacity=1,  # Opacity of the STL model (0 to 1)
    shininess=50,  # How shiny the specular highlight is, when using the 'material' style.
    cam_v_angle=60,  # Vertical angle (in degrees) of the camera
    cam_h_angle=-90,  # Horizontal angle (in degrees) of the camera
)

st.download_button(
    label="Download STL file",
    data=stl_file,
    file_name="nanomesh.stl",
    mime="application/sla",
)
