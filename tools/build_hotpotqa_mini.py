"""Build the committed HotpotQA classroom subset from a rows API response.

Download the response separately; it is intentionally not committed. The generated
corpus includes every gold article and two distractor articles per question.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def slug(title: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{value[:72]}-{hashlib.sha1(title.encode()).hexdigest()[:8]}.md"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("rows_file", type=Path)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("knowledge_base/hotpotqa_mini"))
    parser.add_argument("--benchmark", type=Path, default=Path("benchmark/hotpotqa_mini_questions.json"))
    args = parser.parse_args()

    rows = json.loads(args.rows_file.read_text(encoding="utf-8"))["rows"][: args.count]
    articles: dict[str, list[str]] = {}
    benchmark: list[dict] = []

    for entry in rows:
        item = entry["row"]
        paragraphs = dict(zip(item["context"]["title"], item["context"]["sentences"]))
        gold_titles = list(dict.fromkeys(item["supporting_facts"]["title"]))
        distractors = [title for title in item["context"]["title"] if title not in gold_titles][:2]
        included_titles = list(dict.fromkeys(gold_titles + distractors))
        for title in included_titles:
            articles[title] = paragraphs[title]
        benchmark.append(
            {
                "id": item["id"],
                "question": item["question"],
                "expected_answer": item["answer"],
                "evidence": [slug(title) for title in gold_titles],
                "evidence_titles": gold_titles,
                "type": item["type"],
                "level": item["level"],
            }
        )

    # These questions deliberately have no answer in the fixed, local corpus.
    # They make abstention visible; they are not part of the HotpotQA dataset.
    benchmark.extend(
        {
            "id": f"unanswerable-{number}",
            "question": question,
            "expected_answer": "NOT_FOUND",
            "evidence": None,
            "evidence_titles": [],
            "type": "unanswerable",
            "level": "teaching",
        }
        for number, question in enumerate(
            [
                "What is the annual tuition at the University of Mars?",
                "Which article describes NovaTech's gym-membership reimbursement?",
                "What is the current weather on the moon?",
                "Who won the 2032 World Cup?",
                "What is the customer-support phone number for the fictional company CloudForge?",
            ],
            start=1,
        )
    )

    args.output.mkdir(parents=True, exist_ok=True)
    for title, sentences in articles.items():
        body = " ".join(sentence.strip() for sentence in sentences)
        (args.output / slug(title)).write_text(f"# {title}\n\n{body}\n", encoding="utf-8")

    args.benchmark.parent.mkdir(parents=True, exist_ok=True)
    args.benchmark.write_text(json.dumps(benchmark, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(articles)} articles and {len(benchmark)} questions.")


if __name__ == "__main__":
    main()
