---
applyTo: "quadlets/**/*.container,quadlets/**/*.network,quadlets/**/*.slice,quadlets/**/*.pod"
---

## Podman Quadlet Conventions

All containers run as rootless Podman via systemd Quadlets (user units).

### Container Template

```ini
[Container]
Image=<registry>/<image>:<pinned-tag>
ContainerName=osmen-{profile}-{service}
Network=osmen-{profile}.network
Volume=osmen-{service}-data.volume:/data/path
Secret=osmen-{secret},type=env,target=ENV_VAR_NAME
HealthCmd=/bin/sh -c "<health check command>"
HealthInterval=30s
HealthTimeout=10s

[Service]
Restart=always
Slice=user-osmen-{slice}.slice

[Install]
WantedBy=default.target
```

### Naming Rules

- Container names: `osmen-{profile}-{service}` (e.g. `osmen-core-postgres`)
- Profiles: `core`, `inference`, `media`, `librarian`, `monitoring`
- Networks: one per profile (`osmen-core.network`, `osmen-media.network`)
- Slices enforce cgroup v2 limits: `MemoryMax=`, `CPUQuota=`

### Critical Patterns

- **Pin image tags**: Never use `:latest`. Use specific version tags.
- **Health checks required**: Every container must have a `HealthCmd`
- **Secrets via Podman Secrets**: Use `Secret=` directive, never env vars with plaintext
- **Nextcloud UID mapping**: `UserNS=keep-id:uid=33,gid=33` for www-data
- **Download stack**: Must be a `.pod` file where gluetun provides the network namespace for qBittorrent and SABnzbd

### Container Organization Model

- Profiles are the primary organizer: `core`, `inference`, `media`, `librarian`, `monitoring`.
- Each profile owns its network, resource slice, port budget, and service lifecycle.
- A service belongs to one profile unless there is a deliberate dual-homing case such as Caddy.
- Install-plan phase ownership must match runtime ownership. If a container spans multiple concerns, document the boundary explicitly before adding it.

### New Container Change Protocol

Before adding a container:

1. Choose the profile that owns the service and justify it.
2. Identify ports, volumes, secrets, network peers, health probe, and slice limits.
3. Add any new secret keys to the repo template under `config/secrets/*.template.yaml` and to the local secret workflow.
4. Update the install plan / task list with pull, start, verify, backup, and rotation steps.
5. Define maintenance posture: pinned image version, update trigger, data backup path, and drift checks.

Before merging a new container:

1. Pull image and verify digest/tag.
2. Start container via Quadlet, not `podman run`.
3. Prove health, restart persistence, and dependency readiness.
4. Record any new port allocation, dependency edges, and backup requirements.
5. Update memory/instructions so the next operator can extend it safely.
