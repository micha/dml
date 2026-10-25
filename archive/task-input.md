# Discussion: agent-design

## User intent
The user wants to pivot DML from being primarily human-focused to optimizing for AI agents using DML. This tab is for a direct design discussion with the user, not an autonomous implementation task.

## Roles and scope
You are the design discussion partner. The coordinator stays in a separate tab and manages implementation/coordination. Explore what agent-first should mean, question assumptions, and develop options with the user. Do not treat a design proposal as an approved decision.
No code/documentation edits, commits, tool installation, system changes, delegation, or Herdr control are authorized. Read-only project inspection is allowed when useful. Do not perform a broad audit before engaging the user. Start with a concise framing and one high-value question rather than a large unsolicited redesign.

## Initial context
- Project checkout: /work/repos/micha/dml
- Current HEAD observed by coordinator: 638cc42, clean worktree.
- Native C core implements canonical datums/content IDs and transactional LMDB storage.
- Node/DAG/tree/commit/ref layer, execution, remotes, repository-facing CLI, and real public Python bindings remain unimplemented.
- Relevant docs: docs/architecture.md, docs/spec/overview.md and its linked specifications. Specs are drafts, not an obligation to preserve the current user-facing design.
- Recent local validation: 4 C and 22 Python tests passed; Valgrind clean; strict C coverage incomplete; mutation testing now produces real mutants with survivors.
- Local tool environment, if relevant later: nix develop path:/work/repos/micha/dml-build-tools. Do not run builds as part of discussion without authorization.
- Consider agent workflows and failure modes (discoverability, structured contracts, uncertainty/errors, provenance, resumability, idempotence, concurrency, context/tool-call costs, verification), but use these as prompts, not predefined requirements. Clarify which agents/workflows and actual user problems matter first.

## Input/output locations and acknowledgement
- Input: /tmp/dml-tasks/agent-design/input.md
- Acknowledgement: /tmp/dml-tasks/agent-design/ack.md
- Discussion notes/handoff: /tmp/dml-tasks/agent-design/output.md
- Completion marker, when the user actually ends the discussion or requests handoff: /tmp/dml-tasks/agent-design/done.json
- Supporting artifacts: /tmp/dml-tasks/agent-design/

First read applicable machine/project instructions and this input. Write ack.md confirming scope, exact paths, and understanding that this is a user-led design discussion. Reply briefly that you are ready, then STOP until the coordinator sends GO. Do not write done.json merely because you are ready.
After GO, give a concise opening and one useful question, then discuss directly with the user. Capture notes in output.md when useful or requested, clearly separating questions/options from agreed decisions and preserving uncertainty. Do not use task artifacts to imply implementation approval.
When the user ends the discussion or requests a coordinator handoff, finish output.md first, then atomically publish done.json via done.json.tmp + rename with status (completed or blocked), report (absolute output.md path), and summary (short string). Do not mark an ongoing discussion done.
