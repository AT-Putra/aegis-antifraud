"""ADR-021: deteksi behavioral-collision (device farm replay) — signature + velocity."""

from aegis.schemas.scoring import Behavior
from aegis.services import velocity

# Template behavior dari 7-suspect2 (identik di seluruh farm).
_FARM = {
    "timing": {"time_to_cta_ms": 170112, "dwell_ms": 172205, "interaction_count": 1},
    "mouse": {"move_count": 1, "velocity_mean": 0, "direction_changes": 0},
    "scroll": {"depth_pct": 100},
    "touch": {"tap_count": 1},
}


def test_signature_deterministic_and_distinguishing() -> None:
    a = velocity.behavior_signature(Behavior(**_FARM))
    b = velocity.behavior_signature(Behavior(**_FARM))
    assert a == b and a is not None
    other = dict(_FARM, timing={**_FARM["timing"], "dwell_ms": 99999})
    assert velocity.behavior_signature(Behavior(**other)) != a  # timing beda → sig beda


def test_signature_none_without_timing() -> None:
    # FP guard: tanpa timing entropi → tak diklaster (None).
    assert velocity.behavior_signature(Behavior(timing={}, mouse={"move_count": 1})) is None
    assert velocity.behavior_signature(
        Behavior(timing={"time_to_cta_ms": 0, "dwell_ms": 0})
    ) is None


class _FakePipe:
    def __init__(self, store):
        self.store = store
        self.ops: list[tuple] = []

    def zadd(self, k, mapping):
        self.ops.append(("zadd", k, mapping))
        return self

    def zremrangebyscore(self, k, lo, hi):
        self.ops.append(("zrem", k, lo, hi))
        return self

    def zcard(self, k):
        self.ops.append(("zcard", k))
        return self

    def expire(self, k, s):
        self.ops.append(("expire", k, s))
        return self

    def execute(self):
        res = []
        for op in self.ops:
            if op[0] == "zadd":
                self.store.setdefault(op[1], {}).update(op[2])
                res.append(1)
            elif op[0] == "zrem":
                d = self.store.get(op[1], {})
                for m in [m for m, sc in d.items() if op[2] <= sc <= op[3]]:
                    del d[m]
                res.append(0)
            elif op[0] == "zcard":
                res.append(len(self.store.get(op[1], {})))
            else:
                res.append(True)
        return res


class _FakeRedis:
    def __init__(self):
        self.store = {}

    def pipeline(self):
        return _FakePipe(self.store)


def test_cluster_counts_distinct_devices(monkeypatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(velocity, "get_redis", lambda: fake)
    sig = velocity.behavior_signature(Behavior(**_FARM))
    # 3 device BERBEDA, signature identik → cluster tumbuh 1→2→3.
    assert velocity.cluster_size("gg1", sig, "devA", now=1000) == 1
    assert velocity.cluster_size("gg1", sig, "devB", now=1001) == 2
    assert velocity.cluster_size("gg1", sig, "devC", now=1002) == 3
    # Device sama reload → tak menambah (dedup).
    assert velocity.cluster_size("gg1", sig, "devA", now=1003) == 3


def test_cluster_window_prunes_old(monkeypatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(velocity, "get_redis", lambda: fake)
    sig = velocity.behavior_signature(Behavior(**_FARM))
    velocity.cluster_size("gg1", sig, "devA", now=0)
    # devB jauh di luar window (60m) → devA ter-prune, hanya devB tersisa.
    assert velocity.cluster_size("gg1", sig, "devB", now=velocity.WINDOW_SECONDS + 10) == 1


def test_cluster_zero_without_signature(monkeypatch) -> None:
    monkeypatch.setattr(velocity, "get_redis", lambda: _FakeRedis())
    assert velocity.cluster_size("gg1", None, "devA") == 0
