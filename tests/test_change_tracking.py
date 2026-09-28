from PIL import Image

from veil.core.change_detection import TileChangeDetector
from veil.models import Box, PrivacyCategory, PrivacyRegion
from veil.tracking import RegionTracker


def test_identical_frame_is_skipped():
    d = TileChangeDetector(tile_size=64, mean_threshold=5)
    frame = Image.new("RGB", (128, 128), "black")
    boxes, fraction = d.detect(frame)
    assert boxes
    boxes2, fraction2 = d.detect(frame.copy())
    assert boxes2 == []
    assert fraction2 == 0


def test_static_region_is_refreshed_when_other_area_changes():
    t = RegionTracker(ttl_seconds=0.01)
    region = PrivacyRegion(box=Box(x=0,y=0,w=20,h=20), category=PrivacyCategory.CONTACT, confidence=1, source="test")
    t.update([region], changed_boxes=[Box(x=0,y=0,w=100,h=100)], now=1.0)
    # Change is elsewhere; static region lifetime should refresh.
    out = t.update([], changed_boxes=[Box(x=50,y=50,w=20,h=20)], now=2.0)
    assert out
