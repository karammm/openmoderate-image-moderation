# openmoderate benchmark

A small, reproducible, openly licensed benchmark for the categories the maintainers could
evaluate responsibly. Results for the current release are in [`RESULTS.md`](RESULTS.md).

```bash
pip install openmoderate
python benchmark/run.py                   # downloads the ~240 test images once, then evaluates
python benchmark/run.py --config my.yaml  # measure your own policy
python benchmark/run.py --head my.omh     # measure a trained head
```

## What is in it

`manifest.csv` lists every image: its label, the Wikimedia Commons category it came from,
the download URL (a 320 px thumbnail), the Commons page, licence, author and a SHA-256 of
the thumbnail. The images themselves are **not** committed: each keeps its own licence
(public domain or Creative Commons, as listed per row), and `run.py` downloads them into
`benchmark/data/`, which is git-ignored.

| Label | Source categories on Wikimedia Commons |
|---|---|
| `weapons` | Pistols, Revolvers, Assault rifles, Shotguns, Hunting rifles |
| `hate_symbols` | Nazi flags, Nazi Swastikas, Ku Klux Klan, Ku Klux Klan members |
| `alcohol` | Glasses of beer, Red wine, Cocktails, Beer bottles, Whisky |
| `tobacco` | Cigarettes, Cigarette smoking, Cigars, Electronic cigarettes |
| `drugs` | Cannabis smoking, Cocaine, Heroin, Drug paraphernalia, Joints (cannabis), Bongs |
| `violence` | Fights, Brawls, Riots, Police brutality |
| `safe` | Portraits, dogs, food, offices, beaches, children playing, meetings, living rooms, bicycles, birthday parties, weddings, hiking, markets |
| `hard_negatives` | Benign look-alikes: US flags, kitchen knives, milk, orange juice, coffee, medicine bottles, pharmacy tablets |

## How it was built

1. A fixed-seed random sample of JPEG photos (shorter side ≥ 150 px) was drawn from each
   category above.
2. **Every candidate was reviewed by eye** on numbered contact sheets. Category membership
   on Commons is broad, so roughly half of the candidates were removed, for example:
   - documents, newspaper clippings, charts, logos, adverts and drawings;
   - images where the labelled content is not clearly visible (a portrait of a Klan
     member without regalia, a distant crowd, a gun in a dark display case);
   - content a person could not label either (a joint indistinguishable from a cigarette,
     a vape shaped like a phone);
   - anti-hate imagery ("No KKK" protest signs) and religious look-alikes;
   - safe-set photos that actually contain a moderated category (e.g. champagne at a
     wedding, which is `alcohol`);
   - any image containing nudity, which is out of scope here.
3. Ambiguous groups were left out entirely rather than labelled by guesswork: toy guns,
   boxing as a sport, and religious (Hindu/Buddhist) swastikas.

## Dev and test halves

Each label is split in half by content hash (`split` column in the manifest). Prompts and
thresholds were tuned while looking at the **dev** half only; `run.py` reports the
**test** half by default, so the published numbers come from images the tuning never saw.
Use `--split dev` when you work on prompts, and check `--split test` only at the end.

## What it does not cover

- **Nudity, sexual content, suggestive content, gore and self-harm are not benchmarked.**
  The maintainers chose not to collect such images. If you moderate these categories,
  evaluate on a sample of your own traffic with `openmoderate evaluate` (see the
  [training guide](../docs/guide/training.md)) before relying on the defaults.
- It is small (11–28 positives per category in the test half). Treat the numbers as
  indicative, roughly ±10 percentage points, not as a leaderboard.
- Some labels are narrow: `drugs` is mostly cannabis (buds, joints, bongs) plus a few
  cocaine and heroin photos; `violence` is mostly street clashes and riots.
- Commons skews towards historical photos, museum pieces and well-lit product shots.
  User uploads (screenshots, memes, phone photos, video frames) are harder.

## How metrics are computed

Each image has a single label. For each category, **recall** is the share of its images
flagged with that category, and **precision** counts only the safe images as negatives:
a riot photo that also shows a gun is not a `weapons` false positive just because it was
labelled `violence`. The **safe false-positive rate** is the share of safe and
hard-negative images flagged with *any* category; per-group numbers show which
look-alikes cause trouble.
