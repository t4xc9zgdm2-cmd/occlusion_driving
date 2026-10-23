import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import Config
from src.road import Road
from src.vehicle import Vehicle
from src.tangent import TangentEstimator


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
        lat = road.lateral_offset(car.s, car.x, car.heading, s, ex)
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


if __name__ == "__main__":
    test_tangent_on_inside_edge()
    test_vehicle_moves_forward()
    print("geometry tests ok")
