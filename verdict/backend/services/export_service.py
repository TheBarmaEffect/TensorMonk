"""Export service for generating verdict reports in multiple formats."""

import io
import json
from datetime import datetime


def generate_markdown_report(session_data: dict) -> str:
    """Generate a comprehensive markdown report from session data."""
    decision = session_data.get("decision", {})
    research = session_data.get("research_package", {})
    prosecutor = session_data.get("prosecutor_argument", {})
    defense = session_data.get("defense_argument", {})
    witnesses = session_data.get("witness_reports", [])
    verdict = session_data.get("verdict", {})
    synthesis = session_data.get("synthesis", {})
    output_format = session_data.get("output_format", "executive")
    domain = session_data.get("domain", "business")

    lines = []
    lines.append("# VERDICT — AI Courtroom Analysis Report")
    lines.append(f"\n**Decision:** {decision.get('question', 'N/A')}")
    lines.append(f"**Date:** {datetime.utcnow().strftime('%B %d, %Y')}")
    lines.append(f"**Session ID:** {decision.get('id', 'N/A')}")
    lines.append(f"**Output Format:** {output_format.title()}")
    lines.append(f"**Domain:** {domain.title()}")
    lines.append("\n---\n")

    lines.append("## 1. Research Analysis")
    if research:
        if research.get("summary"):
            lines.append(f"\n{research['summary']}\n")
        if research.get("key_data_points"):
            lines.append("### Key Data Points")
            for point in research["key_data_points"]:
                lines.append(f"- {point}")
        if research.get("risk_landscape"):
            lines.append("\n### Risk Landscape")
            for risk in research["risk_landscape"]:
                lines.append(f"- {risk}")

    lines.append("\n---\n")

    lines.append("## 2. Prosecution Arguments (FOR)")
    if prosecutor:
        if prosecutor.get("opening"):
            lines.append(f"\n> {prosecutor['opening']}\n")
        if prosecutor.get("claims"):
            for i, claim in enumerate(prosecutor["claims"], 1):
                lines.append(f"### Claim {i}")
                lines.append(f"**Statement:** {claim.get('statement', '')}")
                lines.append(f"**Evidence:** {claim.get('evidence', '')}")
                lines.append(f"**Confidence:** {round(claim.get('confidence', 0.5) * 100)}%\n")
        lines.append(f"**Overall Confidence:** {round(prosecutor.get('confidence', 0.5) * 100)}%")

    lines.append("\n---\n")

    lines.append("## 3. Defense Arguments (AGAINST)")
    if defense:
        if defense.get("opening"):
            lines.append(f"\n> {defense['opening']}\n")
        if defense.get("claims"):
            for i, claim in enumerate(defense["claims"], 1):
                lines.append(f"### Claim {i}")
                lines.append(f"**Statement:** {claim.get('statement', '')}")
                lines.append(f"**Evidence:** {claim.get('evidence', '')}")
                lines.append(f"**Confidence:** {round(claim.get('confidence', 0.5) * 100)}%\n")
        lines.append(f"**Overall Confidence:** {round(defense.get('confidence', 0.5) * 100)}%")

    lines.append("\n---\n")

    if witnesses:
        lines.append("## 4. Witness Reports")
        for i, w in enumerate(witnesses, 1):
            verdict_emoji = "✅" if w.get("verdict_on_claim") == "sustained" else "❌" if w.get("verdict_on_claim") == "overruled" else "⚠️"
            lines.append(f"\n### Witness {i} ({w.get('witness_type', 'fact').title()}) {verdict_emoji}")
            lines.append(f"**Verdict:** {w.get('verdict_on_claim', 'inconclusive').upper()}")
            lines.append(f"**Resolution:** {w.get('resolution', '')}")
            lines.append(f"**Confidence:** {round(w.get('confidence', 0.5) * 100)}%")
        lines.append("\n---\n")

    lines.append("## 5. Final Verdict")
    if verdict:
        ruling = verdict.get("ruling", "conditional").upper()
        lines.append(f"\n### Ruling: {ruling}")
        lines.append(f"**Confidence:** {round(verdict.get('confidence', 0.5) * 100)}%\n")
        lines.append(f"{verdict.get('reasoning', '')}\n")
        if verdict.get("key_factors"):
            lines.append("### Key Factors")
            for i, factor in enumerate(verdict["key_factors"], 1):
                lines.append(f"{i}. {factor}")

    lines.append("\n---\n")

    lines.append("## 6. Battle-Tested Synthesis")
    if synthesis:
        lines.append(f"\n**Strength Score:** {round(synthesis.get('strength_score', 0.7) * 100)}%\n")
        if synthesis.get("improved_idea"):
            lines.append(synthesis["improved_idea"])
        if synthesis.get("addressed_objections"):
            lines.append("\n### Objections Addressed")
            for obj in synthesis["addressed_objections"]:
                lines.append(f"- ✓ {obj}")
        if synthesis.get("recommended_actions"):
            lines.append("\n### Recommended Actions")
            for i, action in enumerate(synthesis["recommended_actions"], 1):
                lines.append(f"{i}. {action}")

    lines.append("\n\n---")
    lines.append("*Generated by Verdict AI Courtroom*")

    return "\n".join(lines)


def generate_json_report(session_data: dict) -> str:
    """Generate a JSON export of the full session data."""
    return json.dumps(session_data, indent=2, default=str)


def generate_pdf_report(session_data: dict) -> bytes:
    """Generate a formatted PDF report from session data using fpdf2."""
    from fpdf import FPDF, XPos, YPos

    decision = session_data.get("decision", {})
    research = session_data.get("research_package", {})
    prosecutor = session_data.get("prosecutor_argument", {})
    defense = session_data.get("defense_argument", {})
    witnesses = session_data.get("witness_reports", [])
    verdict = session_data.get("verdict", {})
    synthesis = session_data.get("synthesis", {})
    output_format = session_data.get("output_format", "executive")
    domain = session_data.get("domain", "business")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    def safe_text(text: str, max_len: int = 500) -> str:
        """Sanitize text for PDF output."""
        if not text:
            return ""
        # Replace non-latin1 characters
        text = str(text)[:max_len]
        return text.encode("latin-1", errors="replace").decode("latin-1")

    # Title
    pdf.set_font("Helvetica", style="B", size=20)
    pdf.set_text_color(15, 15, 15)
    pdf.cell(0, 12, "VERDICT — AI Courtroom Analysis", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Metadata
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Decision: {safe_text(decision.get('question', 'N/A'), 120)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Date: {datetime.utcnow().strftime('%B %d, %Y')}  |  Format: {output_format.title()}  |  Domain: {domain.title()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # Divider
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
    pdf.ln(6)

    def section_header(title: str):
        pdf.set_font("Helvetica", style="B", size=13)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    def body_text(text: str, indent: int = 0):
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(50, 50, 50)
        if indent:
            pdf.set_x(pdf.get_x() + indent)
        pdf.multi_cell(190 - indent, 5.5, safe_text(text, 600))
        pdf.ln(1)

    def bullet(text: str):
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(80, 80, 80)
        pdf.set_x(pdf.get_x() + 6)
        pdf.multi_cell(183, 5, f"- {safe_text(text, 300)}")

    # 1. Verdict ruling (most important, put first for exec format)
    if verdict:
        ruling = verdict.get("ruling", "conditional").upper()
        ruling_color = (16, 185, 129) if ruling == "PROCEED" else (239, 68, 68) if ruling == "REJECT" else (245, 158, 11)
        section_header("THE RULING")
        pdf.set_font("Helvetica", style="B", size=18)
        pdf.set_text_color(*ruling_color)
        pdf.cell(0, 10, ruling, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(50, 50, 50)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(190, 5.5, safe_text(verdict.get("reasoning", ""), 800))
        pdf.ln(3)
        if verdict.get("key_factors"):
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, "Key Factors:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            for factor in verdict["key_factors"]:
                bullet(factor)
        pdf.ln(4)

    # 2. Research
    if research:
        section_header("RESEARCH ANALYSIS")
        if research.get("summary"):
            body_text(research["summary"])
        if research.get("key_data_points"):
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, "Key Data Points:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            for point in research["key_data_points"][:5]:
                bullet(str(point))
        pdf.ln(4)

    # 3. Prosecution
    if prosecutor:
        section_header("PROSECUTION (FOR)")
        if prosecutor.get("opening"):
            body_text(prosecutor["opening"])
        for i, claim in enumerate(prosecutor.get("claims", [])[:4], 1):
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.set_text_color(239, 68, 68)
            pdf.cell(0, 6, f"Claim {i}: {safe_text(claim.get('statement', ''), 120)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(190, 5, safe_text(claim.get("evidence", ""), 300))
            pdf.ln(1)
        pdf.ln(3)

    # 4. Defense
    if defense:
        section_header("DEFENSE (AGAINST)")
        if defense.get("opening"):
            body_text(defense["opening"])
        for i, claim in enumerate(defense.get("claims", [])[:4], 1):
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.set_text_color(59, 130, 246)
            pdf.cell(0, 6, f"Claim {i}: {safe_text(claim.get('statement', ''), 120)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(190, 5, safe_text(claim.get("evidence", ""), 300))
            pdf.ln(1)
        pdf.ln(3)

    # 5. Witnesses
    if witnesses:
        section_header("WITNESS REPORTS")
        for i, w in enumerate(witnesses, 1):
            w_verdict = w.get("verdict_on_claim", "inconclusive")
            vcolor = (16, 185, 129) if w_verdict == "sustained" else (239, 68, 68) if w_verdict == "overruled" else (245, 158, 11)
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.set_text_color(*vcolor)
            pdf.cell(0, 6, f"Witness {i} ({w.get('witness_type', 'fact').title()}): {w_verdict.upper()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=9)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(190, 5, safe_text(w.get("resolution", ""), 400))
            pdf.ln(2)
        pdf.ln(3)

    # 6. Synthesis
    if synthesis:
        section_header("BATTLE-TESTED SYNTHESIS")
        if synthesis.get("improved_idea"):
            body_text(synthesis["improved_idea"])
        if synthesis.get("recommended_actions"):
            pdf.set_font("Helvetica", style="B", size=10)
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, "Recommended Actions:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            for i, action in enumerate(synthesis["recommended_actions"], 1):
                bullet(f"{i}. {action}")

    # Footer
    pdf.ln(8)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Generated by Verdict AI Courtroom  |  Multi-Agent Adversarial Decision Analysis", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
