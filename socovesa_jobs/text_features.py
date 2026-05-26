from __future__ import annotations

import nltk
import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer


FALLBACK_SPANISH_STOPWORDS = [
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con",
    "contra", "cual", "cuando", "de", "del", "desde", "donde", "durante",
    "e", "el", "ella", "ellas", "ellos", "en", "entre", "era", "erais",
    "eran", "eras", "eres", "es", "esa", "esas", "ese", "eso", "esos",
    "esta", "estaba", "estaban", "estado", "estais", "estamos", "estan",
    "estar", "estas", "este", "esto", "estos", "estoy", "fue", "fueron",
    "ha", "hace", "hacen", "hacer", "hacia", "han", "hasta", "hay", "la",
    "las", "le", "les", "lo", "los", "mas", "me", "mi", "mis", "mucho",
    "muy", "no", "nos", "o", "para", "pero", "por", "porque", "que",
    "se", "sea", "ser", "si", "sin", "sobre", "son", "su", "sus", "tambien",
    "te", "tiene", "tienen", "todo", "un", "una", "uno", "unos", "y", "ya",
]


def spanish_stopwords() -> list[str]:
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        return FALLBACK_SPANISH_STOPWORDS
    try:
        return stopwords.words("spanish")
    except LookupError:
        return FALLBACK_SPANISH_STOPWORDS


SPANISH_STOPWORDS = spanish_stopwords()


def build_lenguaje_cliente_global(conversaciones: pd.DataFrame, top_k: int = 15) -> dict:
    textos = conversaciones["conversacion"].dropna().astype(str).tolist()
    if len(textos) < 2:
        return {}

    vectorizer = TfidfVectorizer(
        max_features=300,
        ngram_range=(1, 2),
        min_df=2,
        stop_words=SPANISH_STOPWORDS,
    )
    matrix = vectorizer.fit_transform(textos)
    terms = vectorizer.get_feature_names_out()
    scores = np.asarray(matrix.mean(axis=0)).ravel()
    df_terms = pd.DataFrame({"term": terms, "score": scores}).sort_values("score", ascending=False).head(top_k)
    return {"terminos_dominantes": {row.term: round(float(row.score), 3) for _, row in df_terms.iterrows()}}
