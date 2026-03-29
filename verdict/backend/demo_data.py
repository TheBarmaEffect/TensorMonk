"""Pre-cached demo data for DEMO_MODE — used when Groq API is unavailable.

Decision: "Should I pivot my SaaS from B2C to B2B?"
"""

DEMO_DECISION = {
    "id": "demo-001",
    "question": "Should I pivot my SaaS from B2C to B2B?",
    "context": "We have a productivity SaaS with 12,000 free users, 400 paying B2C customers at $12/mo, $4,800 MRR. Several enterprise teams have reached out asking for team features. Our runway is 8 months.",
}

DEMO_RESEARCH_PACKAGE = {
    "market_context": "The B2B SaaS market is projected at $908B by 2030 (Fortune Business Insights), growing at 13.7% CAGR. B2C SaaS companies frequently pivot to B2B as they discover enterprise demand — notable examples include Slack (gaming to enterprise), Figma (individual designers to enterprise design teams), and Notion (personal productivity to team workspace). The current macro environment favors B2B due to higher LTV, lower churn, and more predictable revenue. However, B2B sales cycles are 3-9 months longer and require dedicated sales infrastructure.",
    "key_data_points": [
        "Average B2B SaaS contract value is 10-50x higher than B2C equivalents",
        "B2B SaaS churn rates average 5-7% annually vs 5-7% monthly for B2C",
        "B2B requires 60-90 day average sales cycle vs instant B2C conversion",
        "Enterprise customers demand SOC2, SSO, admin controls — 3-6 month engineering investment",
        "Companies that successfully pivot B2C→B2B see 3-5x revenue growth within 18 months",
        "Current MRR of $4,800 with 400 customers = $12 ARPU, well below B2B benchmarks of $50-500 ARPU"
    ],
    "precedents": [
        "Slack pivoted from a gaming company (Glitch) to enterprise messaging, reaching $1B ARR",
        "Dropbox moved from consumer to Dropbox Business, now 80%+ of revenue is B2B",
        "Canva added Canva for Teams/Enterprise while maintaining B2C, now valued at $26B",
        "Evernote attempted B2B pivot too late, lost consumer base without gaining enterprise traction",
        "Trello maintained freemium B2C while adding Business/Enterprise tiers successfully"
    ],
    "stakeholders": [
        "Current 400 paying B2C customers who may feel deprioritized",
        "12,000 free users who serve as product evangelists and potential B2B leads",
        "Enterprise teams that have proactively reached out (warm leads)",
        "Engineering team that must build enterprise features (SOC2, SSO, RBAC)",
        "Investors who need to see a path to profitability within 8-month runway"
    ],
    "risk_landscape": [
        "8-month runway creates urgency — B2B sales cycles may exceed runway",
        "Enterprise feature requirements (SOC2, SSO) consume significant engineering resources",
        "Risk of alienating existing B2C customers during transition",
        "B2B competitors already established with mature enterprise features",
        "Team may lack enterprise sales expertise and relationships"
    ],
    "summary": "The B2C to B2B pivot is well-precedented in SaaS with significant upside in revenue, LTV, and churn metrics. However, the 8-month runway creates a critical timing constraint, as B2B sales cycles and enterprise feature requirements may consume more time and resources than available. The inbound enterprise interest is a strong signal but must be validated against the execution risk."
}

DEMO_PROSECUTOR_ARGUMENT = {
    "agent": "prosecutor",
    "opening": "The evidence overwhelmingly supports this pivot. With $4,800 MRR and 8 months of runway, the current B2C model is a slow death. Enterprise teams are literally knocking on your door — this is the market telling you where the money is. Every successful SaaS company in the last decade has made this exact move, and the ones that didn't are dead.",
    "claims": [
        {
            "id": "pro-1",
            "statement": "Inbound enterprise interest is the strongest possible market signal for B2B demand",
            "evidence": "Multiple enterprise teams have proactively reached out requesting team features. Inbound enterprise interest has a 5-10x higher conversion rate than outbound sales, dramatically shortening the typical 60-90 day B2B sales cycle. This eliminates the cold-start problem that kills most B2C-to-B2B pivots.",
            "confidence": 0.92,
            "verified": None
        },
        {
            "id": "pro-2",
            "statement": "B2B unit economics are 10-50x superior to current B2C metrics",
            "evidence": "Current ARPU is $12/month. B2B SaaS averages $50-500/month per seat with multi-seat contracts. A single 50-seat enterprise deal at $30/seat = $1,500/month, equivalent to 125 current B2C customers. Three enterprise deals would 10x MRR. B2B annual churn is 5-7% vs B2C monthly churn of 5-7%, creating fundamentally more sustainable revenue.",
            "confidence": 0.95,
            "verified": None
        },
        {
            "id": "pro-3",
            "statement": "The 12,000 free user base is a built-in enterprise lead pipeline",
            "evidence": "Free users already using the product within companies are the most effective B2B sales channel — bottom-up SaaS adoption. Slack, Dropbox, and Figma all leveraged existing individual users to land enterprise contracts. These 12,000 users represent potential champions within their organizations who can drive procurement decisions.",
            "confidence": 0.85,
            "verified": None
        },
        {
            "id": "pro-4",
            "statement": "Maintaining the status quo guarantees failure within 8 months",
            "evidence": "At $4,800 MRR with typical B2C growth rates of 5-10% monthly, reaching profitability before runway expires is mathematically improbable. B2C customer acquisition costs in SaaS average $150-400 per customer, making the $12/month ARPU unsustainable. The pivot isn't optional — it's the only viable path to survival.",
            "confidence": 0.88,
            "verified": None
        }
    ],
    "confidence": 0.90,
    "timestamp": "2026-03-28T14:00:00Z"
}

DEMO_DEFENSE_ARGUMENT = {
    "agent": "defense",
    "opening": "This pivot is a death trap disguised as opportunity. You have 8 months of runway and you want to rebuild your entire product, sales motion, and customer base? Enterprise sales cycles alone take 3-9 months. You'll burn through your runway building SOC2 compliance and SSO while your existing revenue churns. The graveyard of startups is full of companies that chased enterprise revenue they couldn't close in time.",
    "claims": [
        {
            "id": "def-1",
            "statement": "B2B sales cycles will exceed the 8-month runway, creating existential risk",
            "evidence": "Average B2B SaaS sales cycles are 60-90 days for SMB and 6-9 months for enterprise. Factor in 2-3 months to build minimum enterprise features (SSO, RBAC, admin panel), and you're looking at first enterprise revenue no earlier than month 5-6. That leaves 2-3 months of margin — any delay in procurement, legal review, or security audit means death.",
            "confidence": 0.88,
            "verified": None
        },
        {
            "id": "def-2",
            "statement": "Enterprise feature requirements will consume all engineering resources and delay revenue",
            "evidence": "SOC2 Type II compliance alone takes 3-6 months and $50-100K. SSO integration (SAML/OIDC) is 2-4 weeks of engineering. Role-based access control, audit logging, admin dashboards — these are table-stakes for enterprise buyers but months of engineering work. Every sprint spent on compliance is a sprint not spent on revenue-generating features.",
            "confidence": 0.85,
            "verified": None
        },
        {
            "id": "def-3",
            "statement": "Abandoning B2C revenue will accelerate cash burn during the transition",
            "evidence": "The $4,800 MRR from B2C is small but real. Shifting focus to B2B signals to existing customers that they're deprioritized, accelerating churn. If B2C churn increases from 5% to 10% monthly during the pivot, you lose $2,400/month in existing revenue before any B2B revenue materializes. Net cash position deteriorates precisely when you need stability.",
            "confidence": 0.82,
            "verified": None
        },
        {
            "id": "def-4",
            "statement": "Inbound enterprise interest does not validate ability to close enterprise deals",
            "evidence": "Inquiries are not contracts. Enterprise procurement involves security reviews, legal negotiations, budget approval cycles, and competitive evaluations. Without a dedicated sales team, enterprise sales playbook, and customer success infrastructure, converting interest to revenue is extremely difficult. The team has zero B2B sales experience — this is learned, not intuited.",
            "confidence": 0.87,
            "verified": None
        }
    ],
    "confidence": 0.86,
    "timestamp": "2026-03-28T14:00:00Z"
}

DEMO_CONTESTED_CLAIMS = [
    {
        "claim_id": "pro-1",
        "from_agent": "prosecutor",
        "statement": "Inbound enterprise interest is the strongest possible market signal for B2B demand",
        "conflict_reason": "Defense argues inbound interest doesn't validate ability to close deals",
        "witness_type": "precedent"
    },
    {
        "claim_id": "def-1",
        "from_agent": "defense",
        "statement": "B2B sales cycles will exceed the 8-month runway",
        "conflict_reason": "Prosecution claims inbound interest shortens cycles to viable timeline",
        "witness_type": "data"
    },
    {
        "claim_id": "def-2",
        "from_agent": "defense",
        "statement": "Enterprise feature requirements will consume all engineering resources",
        "conflict_reason": "Prosecution implicitly claims pivot is achievable within runway",
        "witness_type": "fact"
    }
]

DEMO_WITNESS_REPORTS = [
    {
        "claim_id": "pro-1",
        "witness_type": "precedent",
        "resolution": "SUSTAINED with qualification. Historical precedents strongly support that inbound enterprise interest converts at 5-10x outbound rates. Slack, Figma, and Notion all converted inbound interest into enterprise contracts within 30-60 days when minimum enterprise features existed. However, the precedent also shows that companies with no enterprise features at all faced 90+ day conversion even with warm leads. The claim is valid but conversion speed depends on feature readiness.",
        "confidence": 0.78,
        "verdict_on_claim": "sustained"
    },
    {
        "claim_id": "def-1",
        "witness_type": "data",
        "resolution": "PARTIALLY SUSTAINED. Industry data confirms average B2B sales cycles of 60-90 days (Salesforce State of Sales 2025). However, bottom-up SaaS motions with existing users in-organization have documented cycles as short as 14-30 days (ProductLed Growth benchmarks). The 8-month runway is tight but not impossible IF the company pursues a product-led growth strategy rather than traditional enterprise sales. The Defense's claim overstates the risk by assuming a traditional sales motion.",
        "confidence": 0.72,
        "verdict_on_claim": "inconclusive"
    },
    {
        "claim_id": "def-2",
        "witness_type": "fact",
        "resolution": "OVERRULED in part. While SOC2 Type II does take 3-6 months, SOC2 Type I can be achieved in 4-8 weeks and is sufficient for initial enterprise contracts. SSO via third-party providers (WorkOS, Auth0) can be integrated in days, not weeks. The Defense's claim inflates the engineering cost by assuming everything must be built from scratch. A pragmatic approach using third-party compliance and auth tooling reduces the enterprise-readiness timeline to 6-8 weeks, not 3-6 months.",
        "confidence": 0.83,
        "verdict_on_claim": "overruled"
    }
]

DEMO_VERDICT = {
    "decision_id": "demo-001",
    "ruling": "conditional",
    "reasoning": "The evidence supports a B2B pivot, but not an all-or-nothing transition. The Prosecution correctly identifies that inbound enterprise interest and existing free users create a viable bottom-up sales motion with superior unit economics. However, the Defense raises legitimate concerns about runway constraints and the risk of abandoning existing revenue. The witness findings reveal that enterprise readiness is achievable faster than the Defense claims (6-8 weeks vs 3-6 months), but the Prosecution underestimates the operational challenge of running dual motions. The ruling is CONDITIONAL: proceed with the B2B pivot using a hybrid strategy that maintains B2C revenue while pursuing the warm enterprise leads, using third-party tooling for rapid enterprise feature deployment.",
    "key_factors": [
        "Inbound enterprise interest validated as strong signal (Witness: sustained)",
        "Enterprise readiness achievable in 6-8 weeks with third-party tooling (Witness: Defense overruled)",
        "8-month runway is tight but viable with product-led growth motion (Witness: inconclusive)",
        "B2B unit economics are 10-50x superior and necessary for survival",
        "Maintaining B2C revenue during transition is critical risk mitigation"
    ],
    "confidence": 0.82,
    "timestamp": "2026-03-28T14:00:00Z"
}

DEMO_SYNTHESIS = {
    "decision_id": "demo-001",
    "improved_idea": "Execute a staged B2B pivot using a product-led growth (PLG) strategy that maintains B2C revenue as a stabilizing base while aggressively pursuing enterprise contracts through existing users.\n\nPhase 1 (Weeks 1-6): Build minimum enterprise features using third-party infrastructure — integrate WorkOS for SSO/SCIM, begin SOC2 Type I with Vanta or Drata, add basic team admin and RBAC. Do NOT build from scratch. Maintain all B2C features and pricing.\n\nPhase 2 (Weeks 4-10): Activate the enterprise pipeline. Reach out to every enterprise team that contacted you with a beta enterprise tier at $25-50/seat/month. Use existing free users within those organizations as champions. Target 3-5 pilot contracts with 60-day close timeline. Offer annual prepaid discounts to accelerate cash collection.\n\nPhase 3 (Weeks 8-16): Based on pilot results, either double down on enterprise (if 2+ contracts close) or retreat to an enhanced B2C model with team features as premium upsell. This creates a clear decision point at month 4 with data, not speculation.\n\nThis hybrid approach addresses the Defense's runway concern by not abandoning B2C revenue, addresses the Prosecution's urgency argument by pursuing B2B immediately, and de-risks the pivot by creating an explicit checkpoint with real data.",
    "addressed_objections": [
        "OBJECTION: B2B sales cycles exceed runway → ADDRESSED: PLG motion with existing in-org users shortens cycle to 14-30 days; enterprise beta targets warm leads only",
        "OBJECTION: Enterprise features consume all engineering → ADDRESSED: Third-party tooling (WorkOS, Vanta) reduces build time to 6-8 weeks, freeing engineering for product work",
        "OBJECTION: B2C revenue loss during transition → ADDRESSED: Hybrid model explicitly maintains B2C tier and pricing; B2B is additive, not replacement",
        "OBJECTION: No enterprise sales expertise → ADDRESSED: PLG strategy leverages product adoption, not traditional sales; founder-led sales sufficient for first 3-5 deals",
        "OBJECTION: Inbound interest doesn't validate close ability → ADDRESSED: Structured beta program with clear pricing and timeline converts interest into commitment with low friction"
    ],
    "recommended_actions": [
        "Week 1: Sign up for WorkOS (SSO) and Vanta (SOC2) — begin compliance and enterprise auth immediately",
        "Week 1: Email every enterprise inquiry with a personalized beta offer at $30/seat/month, annual prepaid option",
        "Week 2: Ship basic team workspace, admin panel, and RBAC using existing user model",
        "Week 3: Identify top 50 free users by engagement who work at companies with 50+ employees — these are your enterprise champions",
        "Week 4: Begin SOC2 Type I audit with Vanta (4-8 week process)",
        "Week 6: Enterprise beta launch with SSO, team features, and SOC2 Type I in progress",
        "Week 10: Decision checkpoint — evaluate enterprise pipeline, close rates, and B2C retention to determine full pivot vs hybrid continuation",
        "Ongoing: Do NOT reduce B2C investment until enterprise revenue exceeds $10K MRR"
    ],
    "strength_score": 0.88,
    "timestamp": "2026-03-28T14:00:00Z"
}

# Ordered stream events for demo replay
DEMO_STREAM_EVENTS = [
    {"event_type": "research_start", "agent": "research", "content": "Initiating neutral research analysis on B2C to B2B SaaS pivot..."},
    {"event_type": "research_start", "agent": "research", "content": "Analyzing market data: B2B SaaS market projected at $908B by 2030, growing 13.7% CAGR. Examining historical pivot precedents including Slack, Dropbox, Figma, and Notion. Evaluating runway constraints against typical B2B sales cycles. Cross-referencing enterprise feature requirements with available third-party tooling options..."},
    {"event_type": "research_complete", "agent": "research", "content": "Research analysis complete.", "data": DEMO_RESEARCH_PACKAGE},
    {"event_type": "prosecutor_thinking", "agent": "prosecutor", "content": "Building the case FOR pivoting B2C to B2B. The market signals are unmistakable — inbound enterprise interest combined with unsustainable B2C unit economics creates an overwhelming argument for this pivot. Let me structure the four strongest claims with irrefutable evidence..."},
    {"event_type": "prosecutor_complete", "agent": "prosecutor", "content": "Prosecution rests.", "data": DEMO_PROSECUTOR_ARGUMENT},
    {"event_type": "defense_thinking", "agent": "defense", "content": "Analyzing the execution risks of this pivot. The 8-month runway is the critical constraint that the Prosecution is glossing over. Enterprise sales cycles, compliance requirements, and the risk of destroying existing revenue during transition all point to catastrophic failure if not executed perfectly. Building my counter-case..."},
    {"event_type": "defense_complete", "agent": "defense", "content": "Defense rests.", "data": DEMO_DEFENSE_ARGUMENT},
    {"event_type": "judge_start", "agent": "judge", "content": "Cross-examining both arguments. Identifying the 3 most contested claims where Prosecution and Defense make directly opposing assertions with evidence..."},
    {"event_type": "witness_spawned", "agent": "witness_precedent", "content": "Spawning precedent witness to verify claim...", "data": {"witness_type": "precedent", "claim": "Inbound enterprise interest is the strongest possible market signal"}},
    {"event_type": "witness_spawned", "agent": "witness_data", "content": "Spawning data witness to verify claim...", "data": {"witness_type": "data", "claim": "B2B sales cycles will exceed the 8-month runway"}},
    {"event_type": "witness_spawned", "agent": "witness_fact", "content": "Spawning fact witness to verify claim...", "data": {"witness_type": "fact", "claim": "Enterprise feature requirements will consume all engineering resources"}},
    {"event_type": "witness_complete", "agent": "witness_precedent", "content": "Witness (precedent): SUSTAINED", "data": DEMO_WITNESS_REPORTS[0]},
    {"event_type": "witness_complete", "agent": "witness_data", "content": "Witness (data): INCONCLUSIVE", "data": DEMO_WITNESS_REPORTS[1]},
    {"event_type": "witness_complete", "agent": "witness_fact", "content": "Witness (fact): OVERRULED", "data": DEMO_WITNESS_REPORTS[2]},
    {"event_type": "cross_examination_complete", "agent": "judge", "content": "Cross-examination complete. Witness findings received. Proceeding to final verdict..."},
    {"event_type": "verdict_start", "agent": "judge", "content": "All evidence received. Deliberating on final ruling..."},
    {"event_type": "verdict_complete", "agent": "judge", "content": "Verdict: CONDITIONAL", "data": DEMO_VERDICT},
    {"event_type": "synthesis_start", "agent": "synthesis", "content": "Synthesizing battle-tested version from full proceeding. Integrating the strongest Prosecution arguments, addressing every Defense objection validated by witnesses, and producing an evolved strategy that survives every attack raised during this proceeding..."},
    {"event_type": "synthesis_complete", "agent": "synthesis", "content": "Synthesis complete. Battle-tested version ready.", "data": DEMO_SYNTHESIS},
]
