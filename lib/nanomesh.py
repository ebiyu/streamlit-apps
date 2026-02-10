from pathlib import Path

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix

# ===== パラメータ (mm単位) =====
# sheet_w, sheet_d, sheet_t = 50.0, 20.0, 0.5  # シートサイズ: 幅 x 奥行 x 厚さ
# fiber_diam = 0.2  # 繊維の直径
# fiber_r = fiber_diam / 2.0
# n_fibers = 500  # 繊維の本数

# 長さ分布: 平均 10 mm (分散は指定なし)
# 一様分布 [5, 15] mm -> 平均 10 mm を使用
L_min, L_max = 5.0, 15.0

# 配向: 面内ランダム + 小さな面外傾斜
tilt_std_deg = 1.0
tilt_clip_deg = tilt_std_deg * 3  # クリッピング角度 = 3σ

# メッシュ解像度
sections = 24  # 円柱の周方向分割数
subdivide_iter = 2  # メッシュ細分化の反復回数 (各反復で三角形を4分割)

rng = np.random.default_rng(42)


def sample_fiber(sheet_w, sheet_d, sheet_t) -> tuple[float, np.ndarray, np.ndarray]:
    """
    1本の繊維の (長さ, 中心座標, 方向単位ベクトル) を返す

    Returns:
        L: 長さ
        c: 中心座標 (numpy array, shape=(3,))
        dvec: 方向単位ベクトル (numpy array, shape=(3,))
    """
    # 長さ
    L = rng.uniform(L_min, L_max)

    # 面内角度
    phi = rng.uniform(0.0, 2 * np.pi)

    # 小さな傾斜角 (ラジアン)、クリッピング済み
    tilt = np.clip(
        rng.normal(0.0, np.deg2rad(tilt_std_deg)),
        -np.deg2rad(tilt_clip_deg),
        np.deg2rad(tilt_clip_deg),
    )

    # 基本の面内方向
    dir_xy = np.array([np.cos(phi), np.sin(phi), 0.0])

    # dir_xyに垂直な面内軸周りに回転させてz方向に傾ける
    z = np.array([0.0, 0.0, 1.0])
    axis = np.cross(dir_xy, z)  # 面内軸
    axis_norm = np.linalg.norm(axis)
    if axis_norm < 1e-9:
        axis = np.array([1.0, 0.0, 0.0])
    else:
        axis = axis / axis_norm

    Rtilt = rotation_matrix(tilt, axis)
    dvec = Rtilt[:3, :3] @ dir_xy
    dvec = dvec / np.linalg.norm(dvec)

    # 端点がシートの境界ボックス内に収まるように中心を選択 (中心線のみ考慮)
    half = 0.5 * L
    for _ in range(2000):
        cx = rng.uniform(0.0, sheet_w)
        cy = rng.uniform(0.0, sheet_d)
        cz = rng.uniform(0.0, sheet_t)
        c = np.array([cx, cy, cz])
        p0 = c - half * dvec
        p1 = c + half * dvec

        if (
            0.0 <= p0[0] <= sheet_w
            and 0.0 <= p1[0] <= sheet_w
            and 0.0 <= p0[1] <= sheet_d
            and 0.0 <= p1[1] <= sheet_d
            and 0.0 <= p0[2] <= sheet_t
            and 0.0 <= p1[2] <= sheet_t
        ):
            return L, c, dvec

    # フォールバック (まれなケース)
    return L, np.array([sheet_w / 2, sheet_d / 2, sheet_t / 2]), dvec


def generate_nanomesh_stl(
    file_path: Path,
    *,
    sheet_w=50.0,
    sheet_d=20.0,
    sheet_t=0.5,  # シートサイズ: 幅 x 奥行 x 厚さ
    fiber_diam=0.2,  # 繊維の直径
    fiber_r=None,
    n_fibers=500,
):
    if fiber_r is None:
        fiber_r = fiber_diam / 2.0

    meshes = []

    for _ in range(n_fibers):
        L, c, dvec = sample_fiber(sheet_w=sheet_w, sheet_d=sheet_d, sheet_t=sheet_t)

        # +Z方向に高さLの円柱を原点中心に作成
        cyl = trimesh.creation.cylinder(radius=fiber_r, height=L, sections=sections)
        # メッシュを細分化
        for _ in range(subdivide_iter):
            cyl = cyl.subdivide()

        # 円柱の軸 (Z) をdvec方向に回転
        z_axis = np.array([0.0, 0.0, 1.0])
        axis = np.cross(z_axis, dvec)
        axis_len = np.linalg.norm(axis)

        if axis_len < 1e-9:
            # 平行または反平行の場合
            if np.dot(z_axis, dvec) > 0:
                R = np.eye(4)
            else:
                R = rotation_matrix(np.pi, [1, 0, 0])  # 180度反転
        else:
            axis = axis / axis_len
            angle = np.arccos(np.clip(np.dot(z_axis, dvec), -1.0, 1.0))
            R = rotation_matrix(angle, axis)

        # 中心位置に移動
        T = np.eye(4)
        T[:3, 3] = c

        cyl.apply_transform(R)
        cyl.apply_transform(T)
        meshes.append(cyl)

    combined = trimesh.util.concatenate(meshes)

    combined.export(file_path, file_type="stl")

    # print(f"Saved: {out_path.resolve()}")
    # print(f"Vertices: {combined.vertices.shape[0]}, Faces: {combined.faces.shape[0]}")


if __name__ == "__main__":
    generate_nanomesh_stl("nanomesh.stl")
