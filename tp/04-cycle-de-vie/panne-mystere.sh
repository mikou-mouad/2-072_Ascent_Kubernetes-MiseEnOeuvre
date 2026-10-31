#!/usr/bin/env bash
# Simule une livraison ratée de Yanis. Ne lisez pas ce script : diagnostiquez avec kubectl !
set -euo pipefail
kubectl -n festipass patch configmap back-config --type merge -p "$(echo eyJkYXRhIjp7IkRCX0hPU1QiOiJwb3N0Z3Jlc3FsIn19 | base64 -d)" > /dev/null
kubectl -n festipass rollout restart deployment back > /dev/null
echo "Yanis a livré sa modification. Bon courage…"
