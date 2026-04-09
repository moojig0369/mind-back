LLM ээс ирэх хариу.
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


LLM output
   ↓
[ Value Nodes ]  ← maslow
   ↓
[ Emotion Tracker ] ← plutchik (node level)
   ↓
[ Value Edges Tracker ] ← hawkins (relationship / timeline)
   ↓
[ Aggregations ]
   ├── emotion table (overall feeling)
   └── value graph state (direction / growth)