import io
import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing import config


def build_geometry(w, g, L, N, B, margin_top, margin_bottom):
    """
    2電極の櫛歯を、連続した閉じたポリラインとして返す。
    polys: [("E1", [(x,y), ...]), ("E2", [(x,y), ...])]
    """
    pitch = w + g
    active_h = N * pitch - g

    H = margin_bottom + active_h + margin_top
    center_gap = g

    x_left_bus = 0.0
    # フィンガーが噛み合う配置:
    # E1 フィンガー: [B, B+L]
    # E2 フィンガー: [B+g, B+L+g]
    # → オーバーラップ: [B+g, B+L] (長さ L-g)
    # フィンガー先端と対向バスバーの隙間 = g
    x_right_bus = B + L + g

    W = x_right_bus + B
    y0 = margin_bottom

    # フィンガーのy座標を振り分け
    e1_fingers = sorted(y0 + i * pitch for i in range(N) if i % 2 == 0)
    e2_fingers = sorted(y0 + i * pitch for i in range(N) if i % 2 != 0)

    # ── E1: 左バスバー ＋ 右に伸びるフィンガー ──
    e1_pts = [(x_left_bus, 0.0), (x_left_bus + B, 0.0)]
    cur_y = 0.0
    for fy in e1_fingers:
        if fy > cur_y:
            e1_pts.append((x_left_bus + B, fy))
        e1_pts.append((x_left_bus + B + L, fy))
        e1_pts.append((x_left_bus + B + L, fy + w))
        e1_pts.append((x_left_bus + B, fy + w))
        cur_y = fy + w
    if H > cur_y:
        e1_pts.append((x_left_bus + B, H))
    e1_pts.append((x_left_bus, H))

    # ── E2: 右バスバー ＋ 左に伸びるフィンガー ──
    e2_pts = [(x_right_bus + B, 0.0), (x_right_bus + B, H), (x_right_bus, H)]
    cur_y = H
    for fy in sorted(e2_fingers, reverse=True):
        fy_top = fy + w
        if fy_top < cur_y:
            e2_pts.append((x_right_bus, fy_top))
        e2_pts.append((x_right_bus - L, fy_top))
        e2_pts.append((x_right_bus - L, fy))
        e2_pts.append((x_right_bus, fy))
        cur_y = fy
    if cur_y > 0.0:
        e2_pts.append((x_right_bus, 0.0))

    polys = [("E1", e1_pts), ("E2", e2_pts)]
    return polys, W, H


def polys_to_dxf(polys, dxf_version="R2010"):
    """DXF ドキュメントオブジェクトを返す"""
    doc = ezdxf.new(dxf_version)
    msp = doc.modelspace()
    for layer in ["E1", "E2"]:
        if layer not in doc.layers:
            doc.layers.new(layer)

    for layer, pts in polys:
        if dxf_version == "R12":
            # R12 は LWPOLYLINE 非対応のため POLYLINE2D を使用
            msp.add_polyline2d(pts, close=True, dxfattribs={"layer": layer})
        else:
            msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})

    return doc


def dxf_to_bytes(doc):
    sio = io.StringIO()
    doc.write(sio)
    return sio.getvalue().encode("utf-8")


# ---- Streamlit UI ----
st.title("Interdigitated comb DXF")

w = st.number_input("line width w", min_value=0.01, value=1.0, step=0.01, format="%.3f")
g = st.number_input("gap g", min_value=0.01, value=1.0, step=0.01, format="%.3f")
L = st.number_input(
    "finger length L", min_value=0.01, value=10.00, step=0.10, format="%.3f"
)
N = st.number_input("finger count N", min_value=1, value=10, step=1)
B = st.number_input("bus width B", min_value=0.01, value=5.00, step=0.10, format="%.3f")
mt = st.number_input("margin top", min_value=0.0, value=0.0, step=0.10, format="%.3f")
mb = st.number_input(
    "margin bottom", min_value=0.0, value=10.00, step=0.10, format="%.3f"
)

polys, W, H = build_geometry(w, g, L, int(N), B, mt, mb)

# ---- Preview (R2010 + ezdxf drawing addon) ----
doc_preview = polys_to_dxf(polys, dxf_version="R2010")
fig = plt.figure()
ax = fig.add_axes([0, 0, 1, 1])
ctx = RenderContext(doc_preview)
out = MatplotlibBackend(ax)
cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE)
Frontend(ctx, out, config=cfg).draw_layout(doc_preview.modelspace(), finalize=True)
st.pyplot(fig)

# ---- Download (R12) ----
doc_r12 = polys_to_dxf(polys, dxf_version="R12")
dxf_bytes = dxf_to_bytes(doc_r12)
st.download_button(
    "Download DXF (R12)",
    data=dxf_bytes,
    file_name=f"comb_w{w}_g{g}_L{L}_N{N}_B{B}.dxf",
    mime="application/dxf",
)
