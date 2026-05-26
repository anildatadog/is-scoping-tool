#!/usr/bin/env bash
# Deploy to Howler.
# Run from the repo root, after the Howler service `is-scoping` is created.
#
#   ./deploy.sh              # build + push (the regular update flow)
#   ./deploy.sh --route      # one-time: also apply the fabric destination + routing-domain
#
# Prereqs: docker, brew-installed `fabric-cli`, AppGate VPN connected.
set -euo pipefail

SERVICE_ID=276
SERVICE_NAME=is-scoping
DOMAIN=us1.staging.dog
NAMESPACE=kiss-app-build

cd "$(dirname "$0")"

echo "==> Packaging context (excluding .git, .venv, .claude/worktrees)…"
tar cfz /tmp/context.tgz \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='.claude/worktrees' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  .

echo "==> Uploading build context to Howler service ${SERVICE_ID}…"
curl --fail-with-body \
  "https://howler.${DOMAIN}/api/services/${SERVICE_ID}/builds/" \
  -F build-context.tgz=@/tmp/context.tgz

echo
echo "==> Build kicked off. Tail logs with:"
echo "    kubectl --context gizmo.${DOMAIN} -n ${NAMESPACE} logs -f -l app=build-${SERVICE_NAME} -c kaniko"

if [[ "${1:-}" == "--route" ]]; then
  echo
  echo "==> Applying fabric destination + routing-domain (one-time exposure to ISP)…"
  command -v fabric >/dev/null || { echo "ERROR: install fabric-cli first: brew install fabric-cli"; exit 1; }

  cat > /tmp/destination.yaml <<EOF
metadata:
    apiVersion: v1
    name: ${SERVICE_NAME}
    namespace: ${NAMESPACE}
    type: destination
spec:
    defaultConnectionConfig:
      activeHealthCheck:
        disable: true
    defaultRouteConfig:
      requestTimeout: 900s
    endpointGroups:
      ${SERVICE_NAME}:
        selector:
          kubernetesServiceSelector:
            name: ${SERVICE_NAME}
            namespace: ${NAMESPACE}
            port: 8000
EOF

  cat > /tmp/domain.yaml <<EOF
metadata:
    name: ${SERVICE_NAME}
    namespace: ${NAMESPACE}
    type: routing_domain
    apiVersion: v1
spec:
    http:
        routes:
            - matcher:
                  path:
                      prefix: /
              target:
                  destination:
                      name: ${SERVICE_NAME}
                      namespace: ${NAMESPACE}
    attachments:
        - dev_gateway:
              fqdn_prefixes:
                  - ${SERVICE_NAME}
EOF

  for zone in us-east-1a us-east-1b us-east-1c; do
    fabric destination apply \
      -d "${DOMAIN}" -n "${NAMESPACE}" \
      --path /tmp/destination.yaml \
      -z "${zone}" \
      --release-name "${SERVICE_NAME}" --release-namespace "${NAMESPACE}"
  done

  for zone in us-east-1a us-east-1b us-east-1c; do
    fabric routing-domain apply \
      -d "${DOMAIN}" -n "${NAMESPACE}" \
      --path /tmp/domain.yaml \
      -z "${zone}" \
      --release-name "${SERVICE_NAME}" --release-namespace "${NAMESPACE}"
  done

  echo
  echo "==> Endpoint debug:"
  fabric endpoints debug -d "${DOMAIN}" -n "${NAMESPACE}" "${SERVICE_NAME}"
fi

echo
echo "==> Once the build finishes, open: https://${SERVICE_NAME}.${DOMAIN}/"
echo "==> Service logs:"
echo "    kubectl --context gizmo.${DOMAIN} -n ${NAMESPACE} logs -f -l app=${SERVICE_NAME} -c ${SERVICE_NAME}"
