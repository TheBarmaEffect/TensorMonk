# ADR-003: Domain-Aware Constitutional Overlays

## Status
Accepted

## Context
Different decision domains (business, legal, medical, financial) require different argumentation patterns, evidence standards, and synthesis formats. A one-size-fits-all prompt produces generic output.

## Decision
Load domain-specific configuration from `config/domains.yaml` at runtime. Each domain defines:

- **Constitutional overlay**: Additional prompt constraints injected into agent system messages
- **Evidence hierarchy**: Ordered list of evidence types by authority (e.g., legal: statutes > case law > expert opinion)
- **Suggested format**: Default output format for the domain
- **Synthesis anchors**: Few-shot examples that ground synthesis output in domain-specific actions

## Domains Supported
| Domain | Overlay Focus | Evidence Priority |
|--------|---------------|-------------------|
| Business | Market data, revenue, competitive benchmarks | Market data > Revenue > Customer research |
| Financial | Valuation models, IRR, risk-adjusted returns | Financial statements > Market data > Comparable transactions |
| Legal | Statutes, precedent, jurisdictional analysis | Statutory law > Case law > Expert testimony |
| Medical | Clinical evidence, FDA guidelines, patient outcomes | RCTs > Meta-analyses > Expert consensus |
| Technology | Architecture patterns, scalability, tech debt | Benchmarks > Architecture reviews > Industry standards |
| Hiring | Role fit, team dynamics, compensation benchmarks | Track record > Skills assessment > Culture fit |

## Consequences
- **Pro**: Domain-appropriate depth and terminology in all agent outputs
- **Pro**: Evidence hierarchy prevents agents from citing weak sources when strong ones exist
- **Pro**: Synthesis anchors produce actionable, domain-specific recommendations
- **Con**: New domains require adding YAML configuration (low effort)
