"""
NLI-based Cross-Source Verification

Uses a Natural Language Inference model to detect contradictions
between claims from different sources. This is the core of
Innovation Point #2: Cross-Source Verification.
"""
from __future__ import annotations
from config import NLI_MODEL_NAME, CONTRADICTION_THRESHOLD


class NLIVerifier:
    """
    Detects contradictions between claims using NLI.
    
    Labels:
    - entailment: source supports the claim
    - contradiction: source contradicts the claim
    - neutral: source is unrelated to the claim
    """
    
    def __init__(self):
        self._model = None
    
    def _load_model(self):
        """Lazy-load the NLI model (only when first needed)."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(NLI_MODEL_NAME)
                print(f"[NLI验证器] 已加载模型: {NLI_MODEL_NAME}")
            except Exception as e:
                print(f"[NLI验证器] 模型加载失败: {e}")
                print("[NLI验证器] 回退到 LLM 验证模式")
                self._model = "fallback"
    
    def verify_claim_against_source(self, claim: str, source_text: str) -> dict:
        """
        Check if a source text supports, contradicts, or is neutral to a claim.
        
        Returns:
            {
                "label": "entailment" | "contradiction" | "neutral",
                "scores": {"entailment": float, "contradiction": float, "neutral": float}
            }
        """
        self._load_model()
        
        if self._model == "fallback":
            # Fallback: assume neutral if model not available
            return {
                "label": "neutral",
                "scores": {"entailment": 0.33, "contradiction": 0.33, "neutral": 0.34}
            }
        
        # CrossEncoder 多分类默认返回 logits（如 6.8 / -3.7），不是概率；
        # 下面和 0.75 / 0.9 比较的是概率阈值，所以必须先做 softmax
        scores = self._model.predict([(source_text, claim)], apply_softmax=True)
        # 标签顺序以模型自带的 id2label 为准（nli-deberta-v3-base: contradiction, entailment, neutral）
        id2label = self._model.model.config.id2label
        labels = [id2label[i].lower() for i in range(len(id2label))]
        score_dict = {label: float(score) for label, score in zip(labels, scores[0])}
        predicted_label = max(score_dict, key=score_dict.get)
        
        return {
            "label": predicted_label,
            "scores": score_dict
        }
    
    def cross_verify_claims(
        self,
        claims_by_source: dict[str, list[str]],
        summaries_by_source: dict[str, str] = None,
    ) -> list[dict]:
        """
        Cross-verify claims using claim-to-summary matching.
        
        Instead of comparing claim vs claim (too strict),
        we compare each claim against other sources' full summaries.
        This dramatically improves entailment detection.
        """
        self._load_model()
        
        MAX_SOURCES = 8
        MAX_CLAIMS_PER_SOURCE = 3
        
        limited_sources = dict(list(claims_by_source.items())[:MAX_SOURCES])
        
        # Collect unique claims
        all_claims = {}
        for source_url, claims in limited_sources.items():
            for claim in claims[:MAX_CLAIMS_PER_SOURCE]:
                if claim not in all_claims:
                    all_claims[claim] = {"origin": source_url, "supporters": [source_url], "contradictors": []}
        
        print(f"    验证范围: {len(limited_sources)} 个来源, {len(all_claims)} 条声明")
        
        # Build summary lookup (use claims joined as fallback if no summaries provided)
        source_summaries = {}
        if summaries_by_source:
            source_summaries = {k: v[:500] for k, v in list(summaries_by_source.items())[:MAX_SOURCES]}
        else:
            for src, claims in limited_sources.items():
                source_summaries[src] = ". ".join(claims[:MAX_CLAIMS_PER_SOURCE])[:500]
        
        # Compare each claim against OTHER sources' summaries (not individual claims)
        pairs_checked = 0
        MAX_COMPARISONS = 100
        
        for claim, info in all_claims.items():
            for other_source, summary in source_summaries.items():
                if other_source == info["origin"]:
                    continue
                if pairs_checked >= MAX_COMPARISONS:
                    break
                
                result = self.verify_claim_against_source(claim, summary)
                pairs_checked += 1
                
                if result["label"] == "entailment" and result["scores"]["entailment"] > 0.75:
                    if other_source not in info["supporters"]:
                        info["supporters"].append(other_source)
                elif result["label"] == "contradiction" and result["scores"]["contradiction"] > 0.9:
                    if other_source not in info["contradictors"]:
                        info["contradictors"].append(other_source)
        
        print(f"    NLI 验证完成: {pairs_checked} 对配对已检查 ✅")
        
        # Determine confidence
        results = []
        for claim, info in all_claims.items():
            if len(info["contradictors"]) >= 2:
                confidence = "disputed"
            elif len(info["supporters"]) > 1:
                confidence = "high"
            else:
                confidence = "unverified"
            
            results.append({
                "claim": claim,
                "confidence": confidence,
                "supporting_sources": info["supporters"],
                "contradicting_sources": info["contradictors"],
            })
        
        return results
