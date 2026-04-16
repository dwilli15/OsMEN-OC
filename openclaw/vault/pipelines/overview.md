# OsMEN-OC Pipeline Overview

## Agent Inventory (10 registered)

| Agent | ID | Role | Tools |
|-------|-----|------|-------|
| Boot Hardening | boot_hardening | Security posture | check_ufw_rules, apply_ufw_rules, check_fail2ban, verify_luks_headers, verify_secure_boot |
| Daily Brief | daily_brief | Morning/evening briefings | generate_brief, fetch_task_summary |
| Focus Guardrails | focus_guardrails | Productivity management | get_focus_status, send_break_reminder, get_productivity_report, block_distraction |
| Knowledge Librarian | knowledge_librarian | RAG ingestion + search | ingest_url, transcribe_audio, search_knowledge |
| Media Organization | media_organization | Download → Plex pipeline | transfer_to_plex, audit_vpn, list_downloads, purge_completed, assess_plex_readiness |
| Research | research | Web search + fact-check | web_search, summarize_page, answer_from_knowledge, fact_check |
| Secrets Custodian | secrets_custodian | Credential auditing | audit_secrets, verify_env_file, verify_podman_secrets, verify_sops_files, verify_openclaw_refs |
| System Monitor | system_monitor | Hardware + compute routing | get_hardware_metrics, set_power_profile, set_fan_curve, get/set_compute_routing, intake_compute_routing, get_npu_status |
| Taskwarrior Sync | taskwarrior_sync | TW ↔ Calendar sync | sync_tasks, get_pending_tasks, create_task, complete_task |
| Vision Tools | vision_tools | Image analysis + generation | analyze_image, ocr_extract, generate_image |

## Data Flow
1. **Ingress**: OpenClaw bridge (Telegram/Discord) → EventEnvelope → Event Bus
2. **Processing**: Orchestration router dispatches to agents via compute-routing rules
3. **Storage**: Working memory → Redis, Long-term → PostgreSQL + pgvector, RAG → ChromaDB
4. **Output**: Event Bus → Response → OpenClaw bridge → Telegram/Discord

## Dependencies
- PostgreSQL 17 + pgvector: Memory entries, workflow ledger, audit trail
- Redis 7: Event bus streams, working memory, bridge transport
- ChromaDB: RAG knowledge base (legacy, migrating to MemoryHub)
- Ollama: Local embeddings (nomic-embed-text), local inference fallback
- OpenClaw: Bridge transport, cron scheduler, multi-channel routing
