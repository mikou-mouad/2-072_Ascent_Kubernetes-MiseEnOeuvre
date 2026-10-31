#!/usr/bin/env bash
# Crée un utilisateur Kubernetes signé par la CA du cluster et son kubeconfig.
# Usage : ./creer-utilisateur.sh <nom> <groupe>
# Résultat : ~/utilisateurs/<nom>/<nom>.kubeconfig
set -euo pipefail

NOM=${1:?usage: $0 <nom> <groupe>}
GROUPE=${2:?usage: $0 <nom> <groupe>}
DIR=~/utilisateurs/$NOM
mkdir -p "$DIR" && cd "$DIR"

# 1. Clé privée et demande de certificat : CN = utilisateur, O = groupe
openssl genrsa -out "$NOM.key" 2048
openssl req -new -key "$NOM.key" -out "$NOM.csr" -subj "/CN=$NOM/O=$GROUPE"

# 2. Demande de signature à l'API Kubernetes
kubectl delete csr "$NOM" --ignore-not-found
cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: $NOM
spec:
  request: $(base64 -w0 < "$NOM.csr")
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: 604800   # 7 jours
  usages: ["client auth"]
EOF

# 3. Approbation (en vrai : par un administrateur, après vérification)
kubectl certificate approve "$NOM"
until [ -n "$(kubectl get csr "$NOM" -o jsonpath='{.status.certificate}')" ]; do sleep 1; done
kubectl get csr "$NOM" -o jsonpath='{.status.certificate}' | base64 -d > "$NOM.crt"

# 4. Kubeconfig dédié
SERVEUR=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}' | base64 -d > ca.crt
KC=$NOM.kubeconfig
kubectl config set-cluster festipass --server="$SERVEUR" --certificate-authority=ca.crt --embed-certs=true --kubeconfig="$KC"
kubectl config set-credentials "$NOM" --client-certificate="$NOM.crt" --client-key="$NOM.key" --embed-certs=true --kubeconfig="$KC"
kubectl config set-context "$NOM" --cluster=festipass --user="$NOM" --namespace=festipass --kubeconfig="$KC"
kubectl config use-context "$NOM" --kubeconfig="$KC"

echo "Kubeconfig prêt : $DIR/$KC"
echo "Test : KUBECONFIG=$DIR/$KC kubectl auth whoami"
