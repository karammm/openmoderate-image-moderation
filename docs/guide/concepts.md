# How it works

openmoderate uses [OpenCLIP](https://github.com/mlfoundations/open_clip), a vision-language model that understands images and text in the same embedding space. Each moderation category is described by a few natural-language prompts (e.g. *"a photo of a gun"*). An image is flagged for a category when it matches that category's prompts clearly better than a pool of ordinary "safe" prompts (portraits, food, landscapes, national flags, logos, kitchen knives...).

Because categories are just text, you can **add your own categories without any training data** — and when you do have data, a [trained head](training.md) sharpens accuracy for your use case.


## Default categories

| Category | Parent | Default threshold |
|---|---|---|
| `nudity` | explicit | 0.50 |
| `sexual_activity` | explicit | 0.50 |
| `suggestive` | suggestive | 0.60 |
| `violence` | violence | 0.50 |
| `gore` | violence | 0.45 |
| `weapons` | violence | 0.50 |
| `hate_symbols` | hate | 0.50 |
| `drugs` | drugs | 0.50 |
| `self_harm` | self_harm | 0.45 |
| `alcohol` | substances | 0.60 |
| `tobacco` | substances | 0.60 |


## Border trimming

Images and video frames have letterbox bars and uniform padding trimmed before scoring, because borders change what the model sees (on a test video, black bars pushed a pistol frame's `sexual_activity` score from 0.01 to 0.65). Set `trim_borders: false` in the policy YAML to turn this off.


## Accuracy and limitations


Be honest with yourself about what zero-shot moderation can do:

- It is **good at clear-cut cases** (a handgun, a swastika, a street fight, someone smoking) and at rejecting common look-alikes (national flags, kitchen knives, medicine).
- It **will miss subtle cases** — small or partly visible symbols, cigarettes at a distance — and can be fooled by adversarial images. See the [benchmarks](../benchmarks.md) for measured recall and precision per category.
- Prompts and thresholds were tuned on the dev half of the benchmark. The explicit-content, gore and self-harm categories could not be validated on real images by the maintainers — **evaluate on a sample of your own traffic before relying on them**, and adjust thresholds.
- For high-stakes moderation, use openmoderate as a first-pass filter and send borderline scores to human review.

[Training a head on your own labelled data](training.md) is the recommended way to get production-grade accuracy for your domain.


## Responsible use


openmoderate is meant to help keep platforms safe. Do not use it to surveil individuals or to profile people by protected characteristics. Moderation models make mistakes; give users a way to appeal automated decisions.
