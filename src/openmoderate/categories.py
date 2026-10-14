"""Default moderation taxonomy.

Each category is described by natural-language prompts. The zero-shot engine compares an
image against every category's prompts *and* a pool of neutral "safe" prompts, so a
category only scores high when it explains the image better than ordinary content does.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    name: str
    prompts: tuple[str, ...]
    threshold: float = 0.5
    parent: str | None = None
    description: str = ""
    # Category-specific contrast prompts: benign look-alikes that should *not* count
    # for this category but may legitimately count for another (e.g. cigarettes are
    # tobacco, not drugs).
    negatives: tuple[str, ...] = ()


SAFE_PROMPTS: tuple[str, ...] = (
    "a photo of a person wearing normal clothes",
    "a photo of people at work or in a meeting",
    "a portrait photo of a smiling person",
    "a photo of a landscape or nature scene",
    "a photo of a city street",
    "a photo of food on a plate",
    "a photo of an animal or pet",
    "a photo of a building or room interior",
    "a photo of everyday objects on a table",
    "a screenshot of a document or website",
    "a product photo on a white background",
    "a photo of people playing sports",
    "a family photo",
    "a cartoon or illustration for children",
    "a person at the beach wearing a swimsuit",
    # Look-alikes: benign content that resembles a violating category. Without these the
    # engine confuses national flags with hate symbols, kitchen knives with weapons, etc.
    "the national flag of a country",
    "a company logo or brand icon",
    "abstract shapes and a simple geometric graphic",
    "clipart, an icon or an emoji",
    "kitchen knives and cooking utensils",
    "a medical photo of prescription medicine",
    "a doctor or nurse in a hospital",
    "a soldier or police officer in uniform at a parade",
    "people dancing at a party or concert",
    "a red painting or red colored object",
)

DEFAULT_CATEGORIES: tuple[Category, ...] = (
    Category(
        "nudity",
        (
            "a photo of a naked person",
            "a nude photo showing genitals or bare breasts",
            "explicit nudity",
        ),
        threshold=0.5,
        parent="explicit",
        description="Exposed genitals, buttocks or female nipples.",
    ),
    Category(
        "sexual_activity",
        (
            "a pornographic image of people having sex",
            "an explicit sexual act",
            "hardcore pornography",
        ),
        threshold=0.5,
        parent="explicit",
        description="Depictions of sexual acts.",
    ),
    Category(
        "suggestive",
        (
            "a sexually suggestive photo of a person in lingerie",
            "an erotic provocative pose",
        ),
        threshold=0.6,
        parent="suggestive",
        description="Revealing clothing or sexually suggestive poses without explicit nudity.",
    ),
    Category(
        "violence",
        (
            "a photo of people fighting violently",
            "a person being beaten or attacked",
            "a violent assault",
        ),
        threshold=0.5,
        parent="violence",
        description="Physical violence between people.",
        negatives=("a person holding a gun at a shooting range", "a sports match"),
    ),
    Category(
        "gore",
        (
            "a graphic photo of blood and gore",
            "a mutilated dead body",
            "a gruesome bloody wound",
        ),
        threshold=0.45,
        parent="violence",
        description="Graphic blood, injuries, corpses.",
    ),
    Category(
        "weapons",
        (
            "a photo of a gun",
            "a person holding a firearm or rifle",
            "a photo of a knife used as a weapon",
        ),
        threshold=0.5,
        parent="violence",
        description="Firearms, knives and other weapons.",
    ),
    Category(
        "hate_symbols",
        (
            "a nazi swastika flag",
            "a hate symbol or extremist flag",
            "a ku klux klan hood and robe",
            "white supremacist propaganda",
        ),
        threshold=0.5,
        parent="hate",
        description="Symbols and imagery associated with hate groups.",
    ),
    Category(
        "drugs",
        (
            "a photo of illegal drugs and syringes",
            "cocaine lines on a table",
            "a person injecting drugs with a needle",
            "pills and drug paraphernalia",
        ),
        threshold=0.5,
        parent="drugs",
        description="Illegal drugs and drug use.",
        negatives=("a person smoking a cigarette", "a vaccination or medical injection"),
    ),
    Category(
        "self_harm",
        (
            "a photo of self harm cuts on a wrist",
            "a person attempting suicide",
        ),
        threshold=0.45,
        parent="self_harm",
        description="Self-injury or suicide imagery.",
    ),
    Category(
        "alcohol",
        (
            "a photo of alcoholic drinks and beer bottles",
            "a person drinking alcohol",
        ),
        threshold=0.6,
        parent="substances",
        description="Alcoholic beverages (often allowed; off by default via high threshold).",
    ),
    Category(
        "tobacco",
        (
            "a person smoking a cigarette",
            "a photo of cigarettes or vaping",
        ),
        threshold=0.6,
        parent="substances",
        description="Tobacco and vaping products.",
    ),
)


def get_category(name: str, categories: tuple[Category, ...] = DEFAULT_CATEGORIES) -> Category:
    for category in categories:
        if category.name == name:
            return category
    raise KeyError(f"Unknown category: {name!r}")
