import numpy as np
import pytest
from conftest import ColorEngine, make_dataset, solid

from openmoderate import Moderator
from openmoderate.training import FolderDataset, LinearHead, TrainConfig, train_head


def test_dataset_parsing_and_duplicates(tmp_path):
    make_dataset(tmp_path, n=4)
    # Same file in two label folders -> one image, two labels.
    (tmp_path / "drugs" / "dup.png").write_bytes((tmp_path / "weapons" / "0.png").read_bytes())
    ds = FolderDataset.from_folder(tmp_path)
    assert ds.labels == ["drugs", "weapons"]
    assert len(ds) == 12
    (dup_row,) = [i for i, p in enumerate(ds.paths) if p.name == "dup.png"]
    assert ds.targets[dup_row].tolist() == [1.0, 1.0]
    assert not any(p == tmp_path / "weapons" / "0.png" for p in ds.paths)
    assert ds.summary()["(no label)"] == 4


def test_dataset_requires_label_folder(tmp_path):
    (tmp_path / "safe").mkdir()
    solid((0, 0, 0)).save(tmp_path / "safe" / "a.png")
    with pytest.raises(ValueError):
        FolderDataset.from_folder(tmp_path)


def test_train_learns_and_roundtrips(tmp_path):
    ds = FolderDataset.from_folder(make_dataset(tmp_path / "data"))
    emb = ds.embed(ColorEngine())
    report = train_head(emb, ds.targets, ds.labels, TrainConfig(epochs=200), model_name="ViT-B-32")
    assert report.n_val > 0
    assert all(m["f1"] >= 0.9 for m in report.val_metrics.values()), report.val_metrics

    path = report.head.save(tmp_path / "h.omh")
    loaded = LinearHead.load(path)
    assert loaded.labels == ds.labels
    assert loaded.model_name == "ViT-B-32"
    np.testing.assert_allclose(loaded.predict(emb), report.head.predict(emb), rtol=1e-5)


def _trained_head(tmp_path):
    ds = FolderDataset.from_folder(make_dataset(tmp_path / "data"))
    report = train_head(ds.embed(ColorEngine()), ds.targets, ds.labels, model_name="ViT-B-32")
    return report.head


def test_moderator_with_head_adds_and_blends(tmp_path):
    head = _trained_head(tmp_path)
    head.labels[0] = "contraband"  # drugs -> a head-only label
    mod = Moderator(head=head, engine=ColorEngine())
    assert "contraband" in mod.category_names and "weapons" in mod.category_names

    red = mod.analyze(solid((220, 30, 30)))
    assert [v.name for v in red.violations] == ["weapons"]
    assert "contraband" in [v.name for v in mod.analyze(solid((30, 30, 220))).violations]
    assert mod.analyze(solid((30, 200, 30))).is_safe

    zero_shot_only = Moderator(head=head, head_weight=0.0, engine=ColorEngine())
    assert zero_shot_only.analyze(solid((220, 30, 30))).score("weapons") < red.score("weapons")


def test_head_label_filters_and_thresholds(tmp_path):
    head = _trained_head(tmp_path)
    head.labels[0] = "contraband"
    mod = Moderator(head=head, engine=ColorEngine(), thresholds={"contraband": 1.0})
    assert mod.thresholds["contraband"] == 1.0
    assert mod.analyze(solid((30, 30, 220))).is_safe

    assert (
        "contraband"
        not in Moderator(head=head, engine=ColorEngine(), exclude=["contraband"]).category_names
    )
    only = Moderator(head=head, engine=ColorEngine(), categories=["contraband"])
    assert only.category_names == ["contraband"]
    with pytest.raises(KeyError):
        Moderator(head=head, engine=ColorEngine(), categories=["nope"])


def test_head_model_mismatch(tmp_path):
    head = _trained_head(tmp_path)
    head.model_name = "ViT-L-14"
    with pytest.raises(ValueError, match="ViT-L-14"):
        Moderator(head=head, engine=ColorEngine())


def test_head_file_is_not_pickle(tmp_path):
    path = _trained_head(tmp_path).save(tmp_path / "h.omh")
    with np.load(path, allow_pickle=False) as data:
        assert set(data.files) == {"weights", "bias", "meta"}
