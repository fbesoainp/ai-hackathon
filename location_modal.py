# location_modal.py
"""
Modal function that extracts a location phrase (e.g. “palo alto”)
from the user’s natural‑language query.

Model: Hugging Face NER – 'dslim/bert‑base‑NER'.
Returns the **first** entity tagged `"LOC"`/`"ORG"`/`"GPE"` as plain text,
or `None` if nothing looks like a place.
"""
from __future__ import annotations
import os, re, modal

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"

app   = modal.App("pairfecto-location-ner")
image = (
    modal.Image.debian_slim(python_version="3.11")   # <‑‑ pin 3.11 wheels exist
         .pip_install(
             "torch==2.3.0",                 # CPU wheel
             "transformers[torch]==4.41.2",
             "sentencepiece",                # required by some HF models
         )
)


@app.function(image=image, max_containers=100, cpu=2)
def extract_location(query: str) -> str | None:
    from transformers import pipeline                                   # inside container
    global _ner
    if "_ner" not in globals():
        _ner = pipeline("token-classification", model="dslim/bert-base-NER", aggregation_strategy="simple")

    # quick heuristic: only keep entities labelled as place‑like
    loc_tags = {"LOC", "ORG", "GPE", "FAC"}
    ents = [e for e in _ner(query) if e["entity_group"] in loc_tags]

    if not ents:
        # fall back to regex “in <place>” pattern
        m = re.search(r"\bin ([A-Za-z][A-Za-z\\s]+)", query, flags=re.I)
        return m.group(1).strip() if m else None

    # return the longest entity string
    return max(ents, key=lambda e: len(e["word"]))["word"]

def get_location(query: str):
    """Call the deployed Modal extractor even when imported locally."""
    import modal
    fn = modal.Function.lookup("pairfecto-location-ner", "extract_location")
    return fn.remote(query)