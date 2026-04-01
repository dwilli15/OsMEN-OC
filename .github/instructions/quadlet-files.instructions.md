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
