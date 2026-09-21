"""Revisão heurística local. Não usa IA nem avalia a validade científica."""

import hashlib
import re

from .models import Review


def analyze_text(text):
    words = re.findall(r"\b\w+(?:[-']\w+)*\b", text, flags=re.UNICODE)
    sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    findings = []
    if len(words) < 50:
        findings.append(
            {
                "code": "short_abstract",
                "message": "Resumo com menos de 50 palavras; confira se apresenta objetivo, método e resultado.",
            }
        )
    if any(len(sentence.split()) > 35 for sentence in sentences):
        findings.append(
            {
                "code": "long_sentence",
                "message": "Há frases com mais de 35 palavras. Considere dividi-las para facilitar a leitura.",
            }
        )
    if re.search(r"\b(\w+)\s+\1\b", text, flags=re.IGNORECASE):
        findings.append(
            {
                "code": "repeated_word",
                "message": "Há palavras consecutivas repetidas. Confira se a repetição é intencional.",
            }
        )
    return {"word_count": len(words), "sentence_count": len(sentences), "findings": findings}


def review_paper(paper):
    # A versão das regras faz parte da chave: mudar o algoritmo permite nova revisão.
    source_hash = hashlib.sha256(f"v1:{paper.language}:{paper.abstract}".encode()).hexdigest()
    return Review.objects.get_or_create(
        paper=paper,
        source_hash=source_hash,
        defaults=analyze_text(paper.abstract),
    )
