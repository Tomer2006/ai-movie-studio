from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CharacterProfile:
    """A locked visual/personality profile injected into render prompts."""

    id: str
    name: str
    description: str
    wardrobe: str | None = None
    physical_signature: str | None = None
    face: str | None = None
    hair: str | None = None
    eyes: str | None = None
    body: str | None = None
    movement: str | None = None
    personality: str | None = None
    voice: str | None = None
    consistency_notes: str | None = None
    negative_prompt: str | None = None
    reference_image_url: str | None = None
    seed: int | None = None

    @classmethod
    def from_bible_character(cls, character: dict[str, Any]) -> CharacterProfile:
        profile = character.get("profile") or {}
        return cls(
            id=character["id"],
            name=character["name"],
            description=character["description"],
            wardrobe=character.get("wardrobe") or profile.get("wardrobe"),
            physical_signature=profile.get("physical_signature"),
            face=profile.get("face"),
            hair=profile.get("hair"),
            eyes=profile.get("eyes"),
            body=profile.get("body"),
            movement=profile.get("movement"),
            personality=profile.get("personality"),
            voice=profile.get("voice"),
            consistency_notes=profile.get("consistency_notes"),
            negative_prompt=profile.get("negative_prompt"),
            reference_image_url=profile.get("reference_image_url"),
            seed=profile.get("seed"),
        )

    def prompt_lines(self) -> list[str]:
        lines = [
            f"- {self.name} (character_id: {self.id})",
            f"  Core description: {self.description}",
        ]
        fields = [
            ("Physical signature", self.physical_signature),
            ("Face", self.face),
            ("Hair", self.hair),
            ("Eyes", self.eyes),
            ("Body", self.body),
            ("Wardrobe", self.wardrobe),
            ("Movement", self.movement),
            ("Personality", self.personality),
            ("Voice/dialogue style", self.voice),
            ("Consistency lock", self.consistency_notes),
        ]
        for label, value in fields:
            if value:
                lines.append(f"  {label}: {value}")
        return lines

    def is_mentioned_in(self, prompt: str) -> bool:
        haystack = prompt.lower()
        names = [self.id.replace("_", " "), self.id, self.name]
        return any(_contains_term(haystack, term.lower()) for term in names if term)


def build_character_profiles(bible_doc: dict[str, Any]) -> list[CharacterProfile]:
    return [
        CharacterProfile.from_bible_character(character)
        for character in bible_doc.get("characters", [])
    ]


def build_character_profile_block(bible_doc: dict[str, Any]) -> str:
    profiles = build_character_profiles(bible_doc)
    if not profiles:
        return ""

    lines = [
        "Character consistency profiles (locked):",
        "Use these exact profiles whenever the shot mentions a character by name or id. "
        "Do not change face, age, species, body shape, signature colors, wardrobe, or personality "
        "unless the shot explicitly overrides it. Do not add characters that the shot does not call for.",
    ]
    for profile in profiles:
        lines.extend(profile.prompt_lines())
    return "\n".join(lines)


def apply_character_profiles_to_prompt(prompt: str, bible_doc: dict[str, Any]) -> str:
    block = build_character_profile_block(bible_doc)
    if not block:
        return prompt
    return f"{prompt.strip()}\n\n{block}"


def apply_character_profiles_to_negative_prompt(
    negative_prompt: str | None, bible_doc: dict[str, Any], prompt: str | None = None
) -> str | None:
    parts = [negative_prompt.strip()] if negative_prompt and negative_prompt.strip() else []

    visual_rules = bible_doc.get("visual_rules") or {}
    parts.extend(rule for rule in visual_rules.get("dont", []) if rule)

    for profile in build_character_profiles(bible_doc):
        if profile.negative_prompt:
            if prompt is None or profile.is_mentioned_in(prompt):
                parts.append(profile.negative_prompt)

    if not parts:
        return None
    return ", ".join(dict.fromkeys(parts))


def resolve_character_reference_image_url(
    prompt: str, bible_doc: dict[str, Any], explicit_reference_image_url: str | None
) -> str | None:
    if explicit_reference_image_url:
        return explicit_reference_image_url

    matches = [
        profile.reference_image_url
        for profile in build_character_profiles(bible_doc)
        if profile.reference_image_url and profile.is_mentioned_in(prompt)
    ]
    return matches[0] if len(matches) == 1 else None


def resolve_character_seed(
    prompt: str, bible_doc: dict[str, Any], explicit_seed: int | None
) -> int | None:
    if explicit_seed is not None:
        return explicit_seed

    matches = [
        profile.seed
        for profile in build_character_profiles(bible_doc)
        if profile.seed is not None and profile.is_mentioned_in(prompt)
    ]
    return matches[0] if len(matches) == 1 else None


def _contains_term(haystack: str, term: str) -> bool:
    if not term:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", haystack) is not None
