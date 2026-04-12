"""
LLM few-shot жишээнүүд.
prompt_builder.py-с тусгаарласан (SRP + мөрийн хязгаар).
"""

import json

ANALYSIS_FEW_SHOT: list[dict] = [
    {
        "role": "user",
        "content": (
            "Surface: Уулзалтад буруу зүйл хэлчихлээ, мартаж чадахгүй.\n"
            "Inner Reaction: Дахин бодохоор улам л муу санагдаад"
            " зайлсхийж байна.\n"
            "Meaning: Хүмүүс чадваргүй гэж бодоосой гэхгүй,"
            " хүндлэгдэхийг хүсч байна."
        ),
    },
    {
        "role": "assistant",
        "content": json.dumps(
            {
                "maslow": [
                    {
                        "category": "esteem",
                        "values": [
                            {"хүлээн зөвшөөрөгдөх": 0.85},
                            {"нэр хүнд": 0.65},
                        ],
                    },
                    {
                        "category": "safety",
                        "values": [{"тогтвортой байдал": 0.40}],
                    },
                ],
                "plutchik": {
                    "primary": "fear",
                    "primary_score": 0.72,
                    "secondary": "sadness",
                    "secondary_score": 0.58,
                    "dyad": "despair",
                    "dyad_score": 0.62,
                    "conflict_flag": False,
                    "intensity": "medium",
                },
                "hawkins": {
                    "emotion": "grief",
                    "level": 162,
                    "score": 0.70,
                    "zone": "below_200",
                    "crisis_flag": False,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
    },
]
