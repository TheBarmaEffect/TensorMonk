cat << 'EOF' > app/graph/verdict_graph.py
async def run_verdict_flow(decision_id, question, context=None):
    return {
        "decision_id": decision_id,
        "status": "graph executed"
    }
EOF