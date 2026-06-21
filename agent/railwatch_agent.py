import os
import duckdb
import pandas as pd
from typing import TypedDict, List
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

DB_PATH = "data/railwatch.duckdb"

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2,
)

# ── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    scorecard: str
    routes: str
    trend_summary: str
    anomalies: List[str]
    briefing: str
    escalations: List[str]

# ── Node 1: Load data from DuckDB ─────────────────────────────────────────────

def load_data_node(state: AgentState) -> AgentState:
    print("  [Node 1] Loading data from DuckDB...")
    con = duckdb.connect(DB_PATH)

    scorecard_df = con.execute("SELECT * FROM host_railroad_scorecard").df()
    routes_df = con.execute("SELECT * FROM route_risk_summary").df()
    trend_df = con.execute("""
        SELECT year, month, host_railroad, avg_fti_per_10k
        FROM monthly_fti_trend
        WHERE year = 2024
        ORDER BY year, month, host_railroad
    """).df()

    con.close()

    scorecard_str = scorecard_df.to_string(index=False)
    routes_str = routes_df.to_string(index=False)

    trend_summary_lines = []
    for rr in trend_df["host_railroad"].unique():
        rr_data = trend_df[trend_df["host_railroad"] == rr]
        avg = rr_data["avg_fti_per_10k"].mean()
        latest = rr_data.iloc[-1]["avg_fti_per_10k"]
        trend_summary_lines.append(
            f"{rr}: avg FTI/10k={avg:.1f}, latest month={latest:.1f}"
        )

    return {
        **state,
        "scorecard": scorecard_str,
        "routes": routes_str,
        "trend_summary": "\n".join(trend_summary_lines),
    }

# ── Node 2: Detect anomalies ──────────────────────────────────────────────────

def detect_anomalies_node(state: AgentState) -> AgentState:
    print("  [Node 2] Detecting anomalies...")
    con = duckdb.connect(DB_PATH)

    df = con.execute("""
        SELECT
            host_railroad,
            route,
            year,
            month,
            fti_per_10k,
            AVG(fti_per_10k) OVER (
                PARTITION BY route
                ORDER BY year, month
                ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
            ) AS rolling_avg
        FROM amtrak_delays
        ORDER BY year, month
    """).df()
    con.close()

    df = df.dropna(subset=["rolling_avg"])
    df["pct_change"] = (df["fti_per_10k"] - df["rolling_avg"]) / (df["rolling_avg"] + 1) * 100

    anomalies = df[df["pct_change"] > 20].sort_values("pct_change", ascending=False).head(5)

    anomaly_list = []
    for _, row in anomalies.iterrows():
        anomaly_list.append(
            f"{row['route']} ({row['host_railroad']}): FTI spiked "
            f"{row['pct_change']:.1f}% above rolling avg in "
            f"{int(row['year'])}-{int(row['month']):02d} "
            f"({row['fti_per_10k']:.0f} vs {row['rolling_avg']:.0f} avg)"
        )

    return {**state, "anomalies": anomaly_list}

# ── Node 3: Generate briefing ─────────────────────────────────────────────────

def generate_briefing_node(state: AgentState) -> AgentState:
    print("  [Node 3] Generating AI briefing with Groq...")

    anomaly_text = "\n".join(state["anomalies"]) if state["anomalies"] else "No major anomalies detected."

    messages = [
        SystemMessage(content="""You are RailWatch, an internal intelligence analyst for Amtrak's 
Office of Public Affairs and Government Relations. You analyze freight railroad interference data 
and write concise, factual briefings for senior leadership. 
Your tone is professional, direct, and evidence-based.
Use the metric FTI (Freight Train Interference) minutes per 10,000 train-miles throughout.
Always recommend escalation when FTI exceeds 900 min/10k mi."""),

        HumanMessage(content=f"""Generate a monthly intelligence briefing based on the following data.

HOST RAILROAD SCORECARD:
{state['scorecard']}

ROUTE RISK SUMMARY:
{state['routes']}

TREND SUMMARY (2024):
{state['trend_summary']}

ANOMALY DETECTION RESULTS:
{anomaly_text}

Write a structured briefing with these sections:
1. Executive Summary (2-3 sentences)
2. Key Findings (bullet points)
3. Anomalies Requiring Attention
4. Escalation Recommendations
5. Next Steps

Keep it under 400 words. Be specific with numbers.""")
    ]

    response = llm.invoke(messages)

    return {**state, "briefing": response.content}

# ── Node 4: Extract escalations ───────────────────────────────────────────────

def extract_escalations_node(state: AgentState) -> AgentState:
    print("  [Node 4] Extracting escalation actions...")

    messages = [
        SystemMessage(content="You extract structured escalation actions from briefings. Return only a numbered list of specific actions, nothing else."),
        HumanMessage(content=f"""From this briefing, extract only the specific escalation actions recommended:

{state['briefing']}

Return as a numbered list of concrete actions only.""")
    ]

    response = llm.invoke(messages)
    escalations = [
        line.strip() for line in response.content.split("\n")
        if line.strip() and line.strip()[0].isdigit()
    ]

    return {**state, "escalations": escalations}

# ── Build graph ───────────────────────────────────────────────────────────────

def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("load_data", load_data_node)
    graph.add_node("detect_anomalies", detect_anomalies_node)
    graph.add_node("generate_briefing", generate_briefing_node)
    graph.add_node("extract_escalations", extract_escalations_node)

    graph.set_entry_point("load_data")
    graph.add_edge("load_data", "detect_anomalies")
    graph.add_edge("detect_anomalies", "generate_briefing")
    graph.add_edge("generate_briefing", "extract_escalations")
    graph.add_edge("extract_escalations", END)

    return graph.compile()

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== RailWatch LangGraph Agent ===\n")

    agent = build_agent()
    result = agent.invoke({
        "scorecard": "",
        "routes": "",
        "trend_summary": "",
        "anomalies": [],
        "briefing": "",
        "escalations": [],
    })

    print("\n" + "="*60)
    print("RAILWATCH MONTHLY INTELLIGENCE BRIEFING")
    print("="*60)
    print(result["briefing"])
    print("\n" + "="*60)
    print("ESCALATION ACTIONS")
    print("="*60)
    for action in result["escalations"]:
        print(action)
