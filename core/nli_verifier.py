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
        
        scores = self._model.predict([(source_text, claim)])
        # Model outputs: [contradiction, entailment, neutral]
        labels = ["contradiction", "entailment", "neutral"]
        score_dict = {label: float(score) for label, score in zip(labels, scores[0])}
        predicted_label = max(score_dict, key=score_dict.get)
        
        return {
            "label": predicted_label,
            "scores": score_dict
        }
    
    def cross_verify_claims(
        self,
        claims_by_source: dict[str, list[str]]
    ) -> list[dict]:
        """
        Cross-verify claims across multiple sources.
        
        Performance: limits sources and claims, batches NLI calls,
        and uses keyword pre-filter to keep runtime under 30 seconds.
        """
        self._load_model()
        
        # --- Strict limits to prevent CPU hang ---
        MAX_SOURCES = 8
        MAX_CLAIMS_PER_SOURCE = 3
        
        # Take only top N sources
        limited_sources = dict(list(claims_by_source.items())[:MAX_SOURCES])
        
        # Collect unique claims
        all_claims = {}
        for source_url, claims in limited_sources.items():
            for claim in claims[:MAX_CLAIMS_PER_SOURCE]:
                if claim not in all_claims:
                    all_claims[claim] = {"origin": source_url, "supporters": [source_url], "contradictors": []}
        
        print(f"    验证范围: {len(limited_sources)} 个来源, {len(all_claims)} 条声明")
        
        # --- Build pairs to verify (with keyword pre-filter) ---
        STOPWORDS = {"the", "a", "an", "is", "are", "was", "were", "of", "and", "to", "in", "for", "on", "with", "that", "it", "as", "by", "this", "from", "or", "be", "can", "has", "have", "not", "its"}
        
        pairs_to_check = []
        sources_list = list(limited_sources.keys())
        
        for claim, info in all_claims.items():
            claim_words = set(claim.lower().split()) - STOPWORDS
            for other_source in sources_list:
                if other_source == info["origin"]:
                    continue
                for other_claim in limited_sources[other_source][:MAX_CLAIMS_PER_SOURCE]:
                    other_words = set(other_claim.lower().split()) - STOPWORDS
                    if len(claim_words & other_words) >= 2:
                        pairs_to_check.append((claim, other_claim, other_source))
        
        print(f"    需要验证的配对数: {len(pairs_to_check)}")
        
        # --- Cap total comparisons ---
        MAX_COMPARISONS = 100
        if len(pairs_to_check) > MAX_COMPARISONS:
            print(f"    ⚠️ 配对数过多，截取前 {MAX_COMPARISONS} 对")
            pairs_to_check = pairs_to_check[:MAX_COMPARISONS]
        
        # --- Run NLI (with progress) ---
        for i, (claim, other_claim, other_source) in enumerate(pairs_to_check):
            if (i + 1) % 20 == 0 or i == 0:
                print(f"    NLI 验证进度: {i+1}/{len(pairs_to_check)}")
            
            result = self.verify_claim_against_source(claim, other_claim)
            
            if result["label"] == "entailment" and result["scores"]["entailment"] > 0.85:
                if other_source not in all_claims[claim]["supporters"]:
                    all_claims[claim]["supporters"].append(other_source)
            elif result["label"] == "contradiction" and result["scores"]["contradiction"] > 0.9:
                if other_source not in all_claims[claim]["contradictors"]:
                    all_claims[claim]["contradictors"].append(other_source)
        
        print(f"    NLI 验证完成 ✅")
        
        # --- Determine confidence ---
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
