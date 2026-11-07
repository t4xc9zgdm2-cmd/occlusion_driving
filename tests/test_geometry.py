import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import Config
from src.road import Road
from src.vehicle import Vehicle
from src.tangent import TangentEstimator
from src.mask import MaskController
from src.render import Projector


def test_tangent_on_inside_edge():
    cfg = Config()
    road = Road(101, cfg.road_width, cfg.road_length)
    car = Vehicle(cfg)
    est = TangentEstimator(cfg)

    t = est.find(road, car)
    assert 5.0 <= t.z <= 55.0
    assert t.side in (-1, 1)
    assert 0.0 <= t.confidence <= 1.0
    assert abs(t.x - road.edge_x(t.s, t.side)) < 1e-9

    # The tangent point should be a local bearing extremum along the edge.
    for dz in (-1.0, 1.0):
        s = t.s + dz
        ex = road.edge_x(s, t.side)
        lat = road.lateral_offset(car.s, car.x, car.heading, s, ex) - cfg.camera_lateral_offset
        b = math.atan2(lat, s - car.s)
        assert abs(t.bearing) <= abs(b) + 1e-6


def test_vehicle_moves_forward():
    cfg = Config()
    road = Road(202, cfg.road_width, cfg.road_length)
    car = Vehicle(cfg)
    for _ in range(60):
        car.update(0.0, road, 1.0 / 60.0)
    assert car.s > 5.0
    assert abs(car.x) < 2.0  # no steering on a curve -> some drift is expected


def test_control_mask_matches_tangent():
    cfg = Config()
    road = Road(101, cfg.road_width, cfg.road_length)
    car = Vehicle(cfg)
    tangent = TangentEstimator(cfg).find(road, car)
    projector = Projector(cfg)
    ctrl = MaskController(cfg)

    m_t = ctrl.update("tangent", road, car, tangent, projector)
    m_c = ctrl.update("control", road, car, tangent, projector)

    assert m_t.center is not None and m_c.center is not None
    assert m_t.radius == m_c.radius
    assert m_t.radius > 0
    assert abs(m_t.center[1] - m_c.center[1]) <= 2  # same longitudinal position
    assert m_t.center[0] != m_c.center[0]           # opposite edges


def test_left_seat_projection():
    cfg = Config(camera_lateral_offset=0)
    road = Road(101, cfg.road_width, cfg.road_length)
    car = Vehicle(cfg)
    x = road.center_x(20)
    centred = Projector(cfg).project(road, car, 20, x)
    cfg.camera_lateral_offset = -0.35
    left_seat = Projector(cfg).project(road, car, 20, x)
    assert left_seat[0] > centred[0]
    assert left_seat[1] == centred[1]
    assert car.x == 0  # eye offset must not change logged vehicle position


def test_pitched_projection():
    cfg = Config(camera_pitch_deg=0)
    road = Road(101, cfg.road_width, cfg.road_length)
    car = Vehicle(cfg)
    level = Projector(cfg)
    x = road.center_x(20)
    point = level.project(road, car, 20, x)
    assert abs(point[1] - (level.cy + level.f * cfg.camera_height / 20)) <= 0.5
    cfg.camera_pitch_deg = 3
    raised = Projector(cfg)
    pitched = raised.project(road, car, 20, x)
    assert pitched[1] > point[1]  # looking up lowers the road in the image
    q = (pitched[1] - raised.cy) / raised.f
    recovered_z = cfg.camera_height * (raised.cos_pitch + q * raised.sin_pitch) / (q * raised.cos_pitch - raised.sin_pitch)
    assert abs(recovered_z - 20) < 0.3


if __name__ == "__main__":
    test_tangent_on_inside_edge()
    test_vehicle_moves_forward()
    test_control_mask_matches_tangent()
    test_pitched_projection()
    test_left_seat_projection()
    print("geometry tests ok")
