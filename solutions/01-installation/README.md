# Correction du TP 01 – Installation du cluster

1. **Swap :** le kubelet calcule les ressources disponibles et les évictions à partir de la mémoire physique. Avec du swap, ces calculs deviennent faux : il refuse donc de démarrer par défaut (le support du swap existe mais doit être configuré explicitement).
2. **br_netfilter / ip_forward :** `br_netfilter` fait passer le trafic des bridges Linux par iptables (nécessaire à kube-proxy et aux NetworkPolicies). `ip_forward` autorise le nœud à router les paquets entre les interfaces des pods.
3. **Driver cgroup :** si containerd et le kubelet ne gèrent pas les cgroups de la même façon, deux gestionnaires se disputent les ressources. Le kubelet devient instable sous charge (pods tués, nœud qui alterne Ready / NotReady).
4. **apt-mark hold :** une mise à jour système (`apt upgrade`) ne doit jamais changer la version de Kubernetes. Les montées de version se font avec kubeadm, une version mineure à la fois.
5. **Static pods :** kube-apiserver, etcd, kube-scheduler, kube-controller-manager. Le kubelet les démarre directement depuis `/etc/kubernetes/manifests`, sans passer par l'API server (qui n'existe pas encore au démarrage).
6. **NotReady :** aucun CNI n'est installé, le kubelet signale que le réseau des pods n'est pas prêt.
7. **Certificats :** `/etc/kubernetes/pki`. Les certificats des composants sont valides 1 an, l'autorité de certification 10 ans. `kubeadm certs renew` ou `kubeadm upgrade` les renouvellent.
8. **calico-node :** 3, un par nœud : c'est un **DaemonSet** (on y revient au TP 07).
9. **Token :** 24 heures par défaut (`kubeadm token list`). `kubeadm token create --print-join-command` en génère un nouveau.
10. **Sans scheduler :** le Deployment et son ReplicaSet ont bien créé les pods (c'est le travail du **controller-manager**), mais personne ne leur attribue de nœud : `spec.nodeName` reste vide, d'où `Pending`. Les pods déjà placés continuent de tourner : le kubelet de chaque nœud gère ses pods sans avoir besoin du scheduler. Dès que le fichier revient dans `/etc/kubernetes/manifests`, le kubelet relance le scheduler, qui place les pods en attente.
11. **Capacity / Allocatable :** `Capacity` est ce que la machine possède. `Allocatable` est ce qui reste pour les pods, une fois retirées les réservations du système et du kubelet, et le seuil d'éviction. Le scheduler raisonne sur `Allocatable` (TP 05).
12. **Control plane :** il porte le taint `node-role.kubernetes.io/control-plane:NoSchedule`. Seuls les pods qui le tolèrent (composants système) y sont placés. On s'en servira au TP 08 pour « ajouter » un nœud.
13. **DaemonSets :** `drain` ne les évacue pas : un DaemonSet place un pod sur chaque nœud, même cordonné. Sans `--ignore-daemonsets`, `drain` refuse de continuer. Les pods `calico-node` et `kube-proxy` restent sur worker2.
14. **Retour sur worker2 :** non. Kubernetes ne déplace jamais un pod qui tourne. Les nouveaux pods iront de préférence sur worker2 (moins chargé). Pour rééquilibrer : `kubectl rollout restart deployment nginx` (recrée tous les pods), ou le projet *descheduler*.

15. **Labels perdus :** `node-role.kubernetes.io/worker` et `festipass/scene=remparts`. `kubectl delete node` a supprimé l'objet Node, avec ses labels ; au `join`, le kubelet en recrée un neuf, avec seulement les labels automatiques (`kubernetes.io/hostname`, `kubernetes.io/os`…). En production, on déclare ces labels dans la configuration du kubelet ou de l'outil qui crée les nœuds.
16. **Nouvelle commande :** le token du matin n'est valable que 24 heures, et il a pu être supprimé ; `token create --print-join-command` en crée un neuf et affiche la commande complète. Elle contient aussi `--discovery-token-ca-cert-hash` : l'empreinte de la CA du cluster, qui permet au worker de vérifier qu'il rejoint le bon control plane.

## Bonus

- **kube-apiserver.yaml :** `--service-cluster-ip-range=10.96.0.0/12` et `--authorization-mode=Node,RBAC`.
- **nodeSelector :** le pod `plage` tourne sur worker1. Sans nœud correspondant, il resterait `Pending`.
- **Minikube / kind :** une commande (`minikube start`, `kind create cluster`). Pratique pour développer, mais un seul nœud (ou des nœuds simulés dans des conteneurs) : pas de vraie panne de machine, pas de réseau réel entre nœuds, pas de préparation du système. kubeadm, c'est ce que font les distributions et les offres managées pour vous.
