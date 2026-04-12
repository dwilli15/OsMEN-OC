# System Patterns

Containers are organized by profile: core, inference, media, librarian, monitoring.
Each profile owns its Quadlets, network membership, systemd slice, port budget, and verification steps.
Secret flow is local SOPS backup -> Podman secret/runtime env -> Quadlet `Secret=` mapping -> service startup verification.
