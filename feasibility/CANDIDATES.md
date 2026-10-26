# Candidate approaches for morning review

These are experimental responses to the feasibility findings, not approved DML
policies or a specification. The user authorized evolving and trying the design.

## A. Durable obligations, immutable history, and admission projections

Try a local transactional journal that preserves identity/ownership and derives
retention from stored commits and heads. Pending adoption/disposal survives head
removal. Operational dependencies and historical provenance have different
availability implications, without deleting associations from research history.

Versioned research facts should remain immutable; any mutable journal tables in the
prototype are operational projections/indexes, not permission to mutate research
records. The exact boundary between durable coordination metadata and versioned
DML data needs review. SQLite is only a substrate for concurrency/crash experiments.

Start with a deliberately coarse reservation that blocks cooperating publication
while destruction is in flight. This makes the safety/availability tradeoff visible.
A finer per-resource fence may be desirable later, but must not conceal membership,
shared-dependency, or stale-plan races.

## B. Deployment freedom with a generic admission contract

The user chooses local CLI, GitHub Actions, or another deployment mechanism. DML
need not know which. A generic pre-apply gate can bind the saved plan, exact resource
identities, config/state receipt, and research-retention reservation.

This does not constrain deployment *technology*, but does constrain cooperative
behavior if strong safety is required. Direct ungated applies remain an explicit
bypass. Alternatives are weaker guarantees or restricting which authority holds
destructive credentials; neither is selected here.

## C. Artifact-specific resource semantics inside OpenTofu

Try a small actual OpenTofu provider for immutable sandbox files. Adoption must
register an existing artifact without recreating it; metadata edits must not upload
new bytes; mismatch and path escape must fail safely; disposal must target the
recorded artifact rather than an unrelated replacement.

This tests whether OpenTofu can remain the first concrete manager while provider
semantics align with research artifacts. It does not prove the generic AWS provider
is safe for version-specific adoption, nor require a new production provider.
A direct artifact adapter is a fallback experiment, not a hidden backend change.

## Unresolved policy choices

- Which binding fields define a closure versus incidental installation metadata?
- May a new historical reference mention an excised resource, and how is that
  distinguished from acquiring it for new execution?
- Who can authorize excision across shared consumers/dependencies?
- How complete must member/dependency discovery be before destruction?
- Is coarse publication blocking acceptable during slow or failed deployment?
- What trust/capability contract permits full HCL expressiveness safely?
- Which management observations must be retained as research history, and which
  coordination structures are operational projections?

The follow-up prototypes will give concrete evidence and failures for these
questions. They do not resolve them merely by choosing one behavior in code.
