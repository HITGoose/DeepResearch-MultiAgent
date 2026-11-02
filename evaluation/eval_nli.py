"""
NLI 验证器评测：修复前（logits 直接和阈值比较）vs 修复后（softmax 概率和阈值比较）

判定规则与 core/nli_verifier.py 的 cross_verify_claims 一致：
- argmax == contradiction 且分数 > 0.9  → 矛盾
- argmax == entailment    且分数 > 0.75 → 支持
- 其余                                  → 中立（不计入 supporters / contradictors）

用法: python -m evaluation.eval_nli
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NLI_MODEL_NAME

ENT_THRESHOLD, CON_THRESHOLD = 0.75, 0.9
LABELS = ["contradiction", "entailment", "neutral"]


def decide(scores: np.ndarray, id2label: dict) -> str:
    i = int(np.argmax(scores))
    label = id2label[i].lower()
    if label == "contradiction" and scores[i] > CON_THRESHOLD:
        return "contradiction"
    if label == "entailment" and scores[i] > ENT_THRESHOLD:
        return "entailment"
    return "neutral"


def metrics(gold: list[str], pred: list[str]) -> dict:
    n = len(gold)
    acc = sum(g == p for g, p in zip(gold, pred)) / n
    out = {"accuracy": acc}
    for lab in LABELS:
        tp = sum(g == lab and p == lab for g, p in zip(gold, pred))
        n_gold = sum(g == lab for g in gold)
        n_pred = sum(p == lab for p in pred)
        out[f"{lab}_recall"] = tp / n_gold if n_gold else 0.0
        out[f"{lab}_precision"] = tp / n_pred if n_pred else 0.0
    # 误报矛盾：非矛盾的对被判成矛盾（会让 claim 被标成 disputed）
    out["false_contradictions"] = sum(g != "contradiction" and p == "contradiction" for g, p in zip(gold, pred))
    return out


def main():
    from sentence_transformers import CrossEncoder

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nli_testset.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    pairs = data["pairs"]
    inputs = [(data["premises"][p["premise"]], p["hypothesis"]) for p in pairs]
    gold = [p["label"] for p in pairs]

    model = CrossEncoder(NLI_MODEL_NAME)
    id2label = model.model.config.id2label
    logits = model.predict(inputs)                       # 修复前：默认返回 logits
    probs = model.predict(inputs, apply_softmax=True)    # 修复后：概率

    preds = {
        "修复前 (logits+阈值)": [decide(s, id2label) for s in logits],
        "修复后 (概率+阈值)": [decide(s, id2label) for s in probs],
        "参考：只取 argmax": [id2label[int(np.argmax(s))].lower() for s in probs],
    }

    print(f"模型: {NLI_MODEL_NAME} | 测试对: {len(pairs)} | 阈值: 支持>{ENT_THRESHOLD}, 矛盾>{CON_THRESHOLD}\n")
    print(f"{'配置':<22}{'准确率':>8}{'矛盾召回':>10}{'矛盾精确':>10}{'支持召回':>10}{'中立召回':>10}{'误报矛盾':>10}")
    for name, pred in preds.items():
        m = metrics(gold, pred)
        print(f"{name:<22}{m['accuracy']:>8.3f}{m['contradiction_recall']:>10.3f}{m['contradiction_precision']:>10.3f}"
              f"{m['entailment_recall']:>10.3f}{m['neutral_recall']:>10.3f}{m['false_contradictions']:>10d}")

    before, after = preds["修复前 (logits+阈值)"], preds["修复后 (概率+阈值)"]
    print("\n逐条（只列出至少一种配置判错，或修复前后不同的）:")
    for p, b, a, lg, pr in zip(pairs, before, after, logits, probs):
        if b != p["label"] or a != p["label"] or b != a:
            top = int(np.argmax(pr))
            print(f"  #{p['id']:<3} 标注={p['label']:<13} 修复前={b:<13} 修复后={a:<13} "
                  f"最高类={id2label[top]} logit={lg[top]:.2f} 概率={pr[top]:.3f} | {p['hypothesis']}")


if __name__ == "__main__":
    main()
