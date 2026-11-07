# Occlusion Driving Experiment

遮挡驾驶实验的基线代码：伪 3D 道路 + 键盘平滑转向 + Full / Tangent / Control 三种遮挡条件 + CSV 日志 + 简单分析。

**论文定位**：主选论文是 **Land & Lee (1994)**（切点假设：司机在弯前 1–2 s 注视内侧切点，注视领先转向）；**Land & Horwood (1995)** 只是直接相关的方法参考（遮挡道路区域、测驾驶表现）。本实验是 **Land & Lee 假设的因果扩展**，不是眼动复现。

---

## 快速开始

```bash
cd occlusion_driving

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
python run.py --participant P01
```

运行后会先出现指导语；按 **SPACE** 进入练习说明，可选 **S** 跳过练习。

## 控制

| 按键 | 作用 |
|---|---|
| ← / → 或 A / D | 左/右转向（有平滑） |
| SPACE | 开始 / 下一 trial |
| S / 点击 SKIP | 跳过练习（练习说明或练习 trial 中） |
| ESC | 退出 |

车速固定，不需要油门/刹车。团队内部调试也可以用 `python run.py -p TEST --skip-practice` 直接跳过练习。

## 实验流程

- 练习：2 trials，全可见，20 s；可在练习说明按 **S** 跳过，或练习中按 **S** 提前结束。
- 正式：3 条件 × 3 trials = 9 trials，每个 30 s。
  - `full`：不遮挡。
  - `tangent`：遮住弯道内侧边沿的切点区域。
  - `control`：遮住同一纵向位置的外侧边沿（同大小、同位置）。
- 条件顺序随机；每个条件使用同一组 3 条道路（seeds 101/202/303）。
- 被遮区域默认是**更大的纯黑圆盘**，半径随切点距离/投影路宽自适应（上限 `mask_radius_frac: 0.13`），完全切断该区域视觉信息；`mask_style` 可改为 `mosaic`、`blur` 或 `solid` 做 pilot 对比。
- 画面不再绘制车底虚线中心线；底部加入车头/仪表台遮挡，近处路面不再能作为“压线”参照。

## 数据

每次运行生成：

```
data/<participant>_<timestamp>/
  trials.csv
  metadata.json
```

`trials.csv` 每帧一行：`t, condition, trial, seed, s, x, heading, steer, speed, curvature, tangent_s, tangent_x, tangent_confidence, mask_x, mask_y, off_road, fps`。

## 分析

```bash
python scripts/analyze.py
# 或指定数据目录
python scripts/analyze.py data
```

输出到 `data/analysis/`：

- `trial_metrics.csv`
- `summary.csv`
- `paired_tests.csv`（tangent vs control 的配对 t 检验）
- `summary.png`（RMS 横向误差、出界比例、转向反向率）

分析默认丢弃每个 trial 前 2 s。

## 调试 / 无头测试

```bash
# 显示切点、遮罩中心、横向误差、条件
python run.py --participant TEST --debug

# 不开窗口，跑 3 个 5 s trial，检查代码是否跑通
python run.py --smoke-test
```

## 预览

生成三张条件截图（不需要窗口）：

```bash
python scripts/preview.py
```

输出 `data/preview_full.png` / `preview_tangent.png` / `preview_control.png`。

## 配置

`config.yaml`：

- `speed`：车速（m/s），当前 11.0（约 40 km/h）；提高车速是为了让远处预瞄成为必需。
- `max_steer_deg` / `steer_tau` / `steer_return_tau`：转向幅度与平滑；车速提高后最大转角降到 10°，避免画龙。
- `hood_height_frac` / `hood_top_width_frac` / `hood_bottom_width_frac` / `dashboard_height_frac`：车头与仪表台的遮挡比例。
- `trial_seconds` / `practice_seconds`：trial 时长。
- `conditions` / `seeds`：条件与道路种子。
- `mask_radius_frac` / `mask_min_frac`：遮罩半径的上限/下限（屏幕高度比例）。
- `mask_cover_frac`：遮罩半径相对切点处投影半路宽的比例；默认 1.10，让远处切点不会变成整条路都被遮住。
- `mask_style`：`black`（默认，纯黑切断信息）/ `solid`（用 `mask_color` 的灰色，适合做“灰盘 vs 黑盘”对照）/ `mosaic` / `blur`。
- `fov_deg`：视场角；当前 105°，让切点遮罩在急弯时也不至于被屏幕边缘裁掉。
- `data_dir`：数据目录。

改完直接重跑；不需要重新安装。

## 代码结构

```
occlusion_driving/
├─ run.py                 # 入口
├─ config.yaml
├─ src/
│  ├─ config.py           # 配置
│  ├─ road.py             # 正弦叠加道路、曲率、内外沿
│  ├─ vehicle.py          # 自行车模型 + 键盘转向平滑
│  ├─ tangent.py          # 切点：内侧边沿的方位角极值
│  ├─ mask.py             # full/tangent/control 遮罩
│  ├─ render.py           # 伪 3D 道路、HUD、消息界面
│  ├─ input.py            # 键盘输入
│  ├─ logger.py           # CSV/JSON
│  ├─ experiment.py       # 练习/正式 trial 状态机
│  └─ analysis.py         # 指标、配对检验、画图
├─ scripts/
│  ├─ analyze.py
│  └─ preview.py
└─ tests/
   ├─ test_geometry.py
   └─ test_flow.py
```

伪 3D 渲染是自定义的“逐扫描线道路条带”，思路参考经典 pseudo-3D racer（如 `jakesgordon/javascript-racer`），但这里是独立的 Python/Pygame 实现，没有拷贝外部代码。

## 注意

- 这是**基线**：只做 Full / Tangent / Control 三条件，不含 Control B、Near/Far、眼动。
- Control 用外侧边沿同位置：同边沿纵移 2–3 m 投影后几乎重叠，不能作为有效对照；结论写成“切点所在的内侧边沿区域”。
- 被试在实验前不要被告知具体假设；实验后 debrief。
- 遮罩大小/车速/转向平滑需要 pilot 调；如果键盘太抖，先调 `steer_tau` 或降低 `speed`。
- 纯黑遮罩只是“减少脑补”，不能保证完全阻断；pilot 时必须做 manipulation check（问被试是否能看见遮罩后面的路），并记录遮罩大小/样式/车速。
- 正式收数据前锁定 `mask_style`、`mask_radius_frac`、`speed` 等参数；不要边收边调。
- 晕动/不适时随时 ESC 停止。
- 数据每天备份；正式实验前先跑 `--smoke-test` 和 `--debug` 检查。
