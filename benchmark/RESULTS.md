# Benchmark results

openmoderate 1.0.0 · model `ViT-B-32 / laion2b_s34b_b79k` · policy: default · split: test

| Category | Images | Recall | Precision (vs. safe set) | Flagged as anything |
|---|---:|---:|---:|---:|
| `alcohol` | 19 | 84% | 100% | 84% |
| `drugs` | 26 | 85% | 82% | 88% |
| `hate_symbols` | 18 | 61% | 100% | 61% |
| `tobacco` | 27 | 59% | 89% | 63% |
| `violence` | 11 | 82% | 100% | 82% |
| `weapons` | 28 | 79% | 100% | 82% |

**Safe images flagged:** 6 of 107 (6% false-positive rate).

| Safe group | Images | Flagged | Flagged as |
|---|---:|---:|---|
| hard_negatives: Coffee cups | 3 | 0 | – |
| hard_negatives: Flags of the United States | 3 | 0 | – |
| hard_negatives: Glasses of milk | 1 | 0 | – |
| hard_negatives: Glasses of orange juice | 4 | 0 | – |
| hard_negatives: Kitchen knives | 6 | 0 | – |
| hard_negatives: Medicine bottles | 5 | 1 | drugs, tobacco |
| hard_negatives: Tablets (pharmacy) | 4 | 0 | – |
| safe: Beaches | 7 | 1 | self_harm |
| safe: Bicycles | 7 | 1 | drugs, tobacco |
| safe: Birthday parties | 4 | 0 | – |
| safe: Business meetings | 6 | 0 | – |
| safe: Children playing | 7 | 1 | drugs |
| safe: Dogs | 6 | 0 | – |
| safe: Food | 5 | 2 | drugs |
| safe: Hiking | 3 | 0 | – |
| safe: Living rooms | 4 | 0 | – |
| safe: Markets | 7 | 0 | – |
| safe: Offices | 5 | 0 | – |
| safe: Portrait photographs of men | 9 | 0 | – |
| safe: Portrait photographs of women | 8 | 0 | – |
| safe: Weddings | 3 | 0 | – |
