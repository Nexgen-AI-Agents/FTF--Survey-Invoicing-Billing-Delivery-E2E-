---
name: feedback-sprint-dependencies
description: "Before starting any sprint, identify and surface all blocking dependencies — especially those that could halt work mid-sprint"
metadata: 
  type: feedback
---

Before starting any sprint, resolve all dependencies first. If a major dependency exists that could stop work mid-sprint, highlight it explicitly before the sprint begins. If a dependency can be unblocked using demo/mock data, suggest that as a path forward.

**Why:** Mid-sprint blockers waste planning and context. Better to surface them upfront so the user can decide whether to unblock, swap the sprint order, or proceed with demo data.

**How to apply:** At sprint planning time, scan the sprint tasks for external dependencies (API access, DB credentials, client data, third-party integrations, missing assets). Flag any that are unresolved. For each blocked dependency, state: (1) what's missing, (2) what work it blocks, (3) whether demo data can substitute. Only proceed once the user has acknowledged or resolved the blockers.
