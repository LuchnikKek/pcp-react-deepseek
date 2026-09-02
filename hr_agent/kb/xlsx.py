"""База знаний над bz_cut.xlsx: BM25 по колонке «Вопрос», полный текст инструкции по №."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import openpyxl

from hr_agent.kb.models import STATUS_FALSE, Instruction, InstructionHeader, InstructionType

SHEET = "Инструкции"
TYPES: dict[str, InstructionType] = {"type_RAG": "RAG", "type_API": "API", "type_API_HARD": "API_HARD"}
TOPIC_COLUMNS = ("TAGS отчТематика1", "TAGS отчТематика2", "TAGS отчТематика3")
_WORD = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def load_instructions(path: Path) -> list[Instruction]:
    rows = openpyxl.load_workbook(path, read_only=True)[SHEET].iter_rows(values_only=True)
    header = [str(h) for h in next(rows)]
    out: list[Instruction] = []
    for values in rows:
        row = dict(zip(header, values, strict=False))
        if row.get("№") is None:
            continue
        out.append(
            Instruction(
                id=int(row["№"]),
                question=str(row["Вопрос"] or "").strip(),
                text=str(row["Действия и ответ на вопрос"] or "").strip(),
                type=TYPES[str(row["TAGS_type"])],
                topics=[str(row[c]) for c in TOPIC_COLUMNS if row.get(c)],
                status=str(row["TAGS_status"] or ""),
            )
        )
    return out


class XlsxKb:
    """KbClient над срезом БЗ: top-N заголовков по BM25 близости запроса к вопросу инструкции."""

    def __init__(self, path: str | Path, top_n: int = 10, k1: float = 1.5, b: float = 0.75) -> None:
        self._items = {i.id: i for i in load_instructions(Path(path))}
        self._top_n, self._k1, self._b = top_n, k1, b
        # status_false модели не показываются (§5.1), поэтому в индекс поиска не попадают: топ-N всегда из видимых
        visible = (i for i in self._items.values() if i.status != STATUS_FALSE)
        self._docs = {i.id: Counter(tokenize(i.question)) for i in visible}
        self._avg_len = sum(sum(d.values()) for d in self._docs.values()) / max(len(self._docs), 1)
        df = Counter(term for doc in self._docs.values() for term in doc)
        n = len(self._docs)
        self._idf = {term: math.log(1 + (n - f + 0.5) / (f + 0.5)) for term, f in df.items()}

    def _score(self, doc: Counter[str], query: list[str]) -> float:
        norm = self._k1 * (1 - self._b + self._b * sum(doc.values()) / self._avg_len)
        return sum(self._idf[term] * tf * (self._k1 + 1) / (tf + norm) for term in query if (tf := doc.get(term, 0)))

    async def search(self, query: str) -> list[InstructionHeader]:
        terms = tokenize(query)
        scored = [(self._score(doc, terms), id_) for id_, doc in self._docs.items()]
        ranked = sorted(((s, i) for s, i in scored if s > 0), key=lambda pair: (-pair[0], pair[1]))
        return [self._items[i].header(round(s, 3)) for s, i in ranked[: self._top_n]]

    async def get(self, instruction_id: int) -> Instruction | None:
        return self._items.get(instruction_id)
