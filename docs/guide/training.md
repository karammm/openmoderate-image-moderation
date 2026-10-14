# Train on your own data

Zero-shot works out of the box, but a head trained on *your* images is more accurate for your domain, and lets you add labels that are hard to describe in words.

**1. Arrange images in folders.** One folder per label, plus `safe/` for acceptable images:

```
dataset/
├── weapons/        # images that should be flagged as "weapons"
├── counterfeit/    # a brand-new label of your own
└── safe/           # a broad sample of your normal, acceptable traffic
```

An image that belongs to several labels can be copied into several folders.

**2. Train** (CPU is fine; a few hundred images takes about a minute):

```bash
openmoderate train ./dataset -o my_head.omh
```

This prints precision and recall on a held-out split, then saves a head trained on all the images.

**3. Use it:**

```python
mod = Moderator(head="my_head.omh")
```

```bash
openmoderate scan ./uploads --head my_head.omh
```

Labels that exist in both the head and the zero-shot categories (like `weapons` above) use the trained score by default. Pass `head_weight=0.5` (or `--head-weight 0.5`) to blend the two. New labels (like `counterfeit`) are added to the results.

**4. Evaluate** on a separate labelled folder that was not used for training:

```bash
openmoderate evaluate ./holdout --head my_head.omh
openmoderate evaluate ./holdout                 # measure the zero-shot defaults on your data
```

> **The `safe/` folder matters most.** The head learns what is *not* a violation from it. In our tests, a `dog` head trained with only cats and city photos in `safe/` scored 100% on held-out validation, yet flagged 6 of 20 unrelated photos (people, a meeting, a boxing match) as dogs. After adding 24 varied everyday photos to `safe/`, it flagged none. Fill `safe/` with a broad, representative sample of the images your users actually upload, and evaluate on images from outside the training set.

Heads are saved as `.omh` files: a NumPy archive with no pickle, so loading a head from someone else cannot run code.
