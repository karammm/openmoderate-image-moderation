# Python API

## Inputs

`analyze()` accepts a file path, `pathlib.Path`, URL, raw `bytes`, a file-like object (e.g. a Django/Flask upload) or a `PIL.Image`:

```python
mod.analyze("photo.png")
mod.analyze("https://example.com/photo.jpg")
mod.analyze(request.files["avatar"])        # Flask
mod.analyze(uploaded_file.read())           # bytes
results = mod.analyze_batch(["a.jpg", "b.jpg", "c.jpg"])   # faster for many images
```

## Results

```python
result.is_safe           # bool
result.violations        # labels that crossed their threshold
result.labels            # every category with its confidence, highest first
result.score("weapons")  # 0.9612
result.to_dict()         # JSON-serialisable
```


## Choosing a model preset

```python
mod = Moderator(preset="accurate")   # "fast" (default), "balanced" or "accurate"
```

| Preset | Model | Recall | Safe images flagged | CPU per image |
|---|---|---:|---:|---:|
| `fast` | ViT-B/32 | 77.5% | 6.5% | 10 ms |
| `balanced` | ViT-B/16 | 77% | 4.7% | 32 ms |
| `accurate` | ViT-L/14 | 82% | 4.2% | 129 ms |

`accurate` catches the most and flags the fewest safe images; `fast` is the cheapest. Each
preset downloads its own weights on first use. See [benchmarks](../benchmarks.md) for the
per-category numbers. You can also set a preset in a policy file (`preset: accurate`) or with
the `OPENMODERATE_PRESET` environment variable. A trained head only works with the model it was
trained on.

## Tuning your policy

```python
# Stricter on weapons, ignore alcohol and tobacco
mod = Moderator(thresholds={"weapons": 0.3}, exclude=["alcohol", "tobacco"])

# Only check for explicit content
mod = Moderator(categories=["nudity", "sexual_activity"])
```

Or keep the policy in a YAML file:

```yaml
# policy.yaml
thresholds:
  weapons: 0.3
  suggestive: 0.8
disabled: [alcohol, tobacco]
custom_categories:
  - name: gambling
    prompts: ["a casino slot machine", "people gambling at a poker table"]
    negatives: ["people playing a board game"]   # benign look-alikes
    threshold: 0.5
```

```python
mod = Moderator("policy.yaml")
```

`negatives` are category-specific contrast prompts: things that look similar but should not count for *this* category (for example, the built-in `drugs` category treats cigarettes as a negative, because they belong to `tobacco`).

## Configuration via environment

| Variable | Purpose |
|---|---|
| `OPENMODERATE_CACHE_DIR` | Where model weights are cached |
| `OPENMODERATE_MODEL` / `OPENMODERATE_PRETRAINED` | Swap the OpenCLIP model (default `ViT-B-32` / `laion2b_s34b_b79k`) |
| `OPENMODERATE_MAX_BYTES` | Reject uploads larger than this (default 25 MB) |
