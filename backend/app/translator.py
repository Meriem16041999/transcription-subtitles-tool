from transformers import MarianMTModel, MarianTokenizer

MODELS = {
    "en": "Helsinki-NLP/opus-mt-fr-en",
    "es": "Helsinki-NLP/opus-mt-fr-es",
    "ar": "Helsinki-NLP/opus-mt-fr-ar",
    "it": None,
    "en_it": "Helsinki-NLP/opus-mt-en-it",
}

_cache = {}


def get_translator(target_lang: str):
    model_name = MODELS[target_lang]

    if model_name not in _cache:
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
        _cache[model_name] = (tokenizer, model)

    return _cache[model_name]


def translate_text(text: str, target_lang: str) -> str:
    if target_lang == "it":
        # FR → EN
        en = translate_text(text, "en")
        # EN → IT
        tokenizer, model = get_translator("en_it")
        batch = tokenizer([en], return_tensors="pt", padding=True, truncation=True)
        generated = model.generate(**batch, max_new_tokens=256)
        return tokenizer.decode(generated[0], skip_special_tokens=True)

    tokenizer, model = get_translator(target_lang)
    batch = tokenizer([text], return_tensors="pt", padding=True, truncation=True)
    generated = model.generate(**batch, max_new_tokens=256)

    return tokenizer.decode(generated[0], skip_special_tokens=True)

def translate_segments(segments: list[dict], target_lang: str) -> list[dict]:
    translated = []

    for segment in segments:
        translated.append({
            **segment,
            "text": translate_text(segment["text"], target_lang),
        })

    return translated