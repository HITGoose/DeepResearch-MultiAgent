"""
Planner Agent — Simulate-Before-Act

Innovation Point #1:
Instead of generating one search plan and executing it blindly,
the Planner generates multiple candidate plans, simulates their
expected coverage, and selects the best one.
"""
from core.state import ResearchState, CandidatePlan, SubQuery
from core.llm import get_main_llm, get_light_llm, call_llm_json
from prompts.planner_prompt import PLAN_GENERATION_PROMPT, PLAN_SIMULATION_PROMPT
from config import NUM_CANDIDATE_PLANS, COVERAGE_SCORE_THRESHOLD


def planner_node(state: ResearchState) -> dict:
    """
    LangGraph node: Generate and evaluate candidate search plans.
    
    Flow:
    1. Generate N candidate plans (main LLM)
    2. Simulate each plan's coverage (light LLM, parallel-friendly)
    3. Select the plan with highest coverage score
    """
    print("\n" + "=" * 60)
    print("🧠 [规划器] 正在生成候选搜索计划...")
    print("=" * 60)
    
    user_query = state["user_query"]
    failed_strategies = state.get("failed_strategies", [])
    
    # --- 第1步：生成候选计划 ---
    main_llm = get_main_llm()
    
    gen_prompt = PLAN_GENERATION_PROMPT.format(
        user_query=user_query,
        failed_strategies="\n".join(failed_strategies) if failed_strategies else "无（首次迭代）",
        num_plans=NUM_CANDIDATE_PLANS,
    )
    
    plans_data = call_llm_json(main_llm, gen_prompt)
    raw_plans = plans_data.get("plans", [])
    
    if not raw_plans:
        print("[规划器] ⚠️ 未生成计划，使用默认计划")
        raw_plans = [{
            "plan_id": 1,
            "strategy": f"直接搜索: {user_query}",
            "sub_queries": [
                {"query": user_query, "intent": "直接回答", "source": "web"}
            ]
        }]
    
    # --- 第2步：模拟评估每个计划（Simulate-Before-Act）---
    print(f"[规划器] 正在模拟评估 {len(raw_plans)} 个候选计划...")
    light_llm = get_light_llm()
    
    candidate_plans = []
    for plan in raw_plans:
        sub_queries_text = "\n".join(
            f"  - [{sq.get('source', 'web')}] {sq['query']} (意图: {sq.get('intent', '未知')})"
            for sq in plan.get("sub_queries", [])
        )
        
        sim_prompt = PLAN_SIMULATION_PROMPT.format(
            user_query=user_query,
            strategy=plan.get("strategy", ""),
            sub_queries_text=sub_queries_text,
        )
        
        sim_result = call_llm_json(light_llm, sim_prompt)
        
        coverage_score = float(sim_result.get("coverage_score", 0.5))
        reasoning = sim_result.get("reasoning", "")
        
        candidate = CandidatePlan(
            plan_id=plan.get("plan_id", 0),
            strategy=plan.get("strategy", ""),
            sub_queries=[
                SubQuery(
                    query=sq["query"],
                    intent=sq.get("intent", ""),
                    source=sq.get("source", "web"),
                )
                for sq in plan.get("sub_queries", [])
            ],
            coverage_score=coverage_score,
            reasoning=reasoning,
        )
        candidate_plans.append(candidate)
        print(f"  计划 {candidate.plan_id}: 覆盖度={coverage_score:.2f} | {candidate.strategy[:60]}...")
    
    # --- 第3步：选择最优计划 ---
    candidate_plans.sort(key=lambda p: p.coverage_score, reverse=True)
    selected = candidate_plans[0]
    
    print(f"\n✅ [规划器] 选中计划 {selected.plan_id}（覆盖度={selected.coverage_score:.2f}）")
    print(f"   策略: {selected.strategy}")
    print(f"   子查询数: {len(selected.sub_queries)}")
    
    return {
        "candidate_plans": candidate_plans,
        "selected_plan": selected,
        "status": "searching",
    }
