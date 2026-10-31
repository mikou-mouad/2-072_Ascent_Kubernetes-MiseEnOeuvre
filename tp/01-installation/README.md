# TP 01 – « Camille, il nous faut un cluster »

**Durée :** 2 h 55 (1 h 25 le matin, 1 h 30 l'après-midi) · **Branche :** `tp-01-installation` · **Correction :** `solutions/01-installation/`, dans cette branche

## L'incident

> Léa a tranché : « Cette année, on passe sur Kubernetes. Camille, il nous faut un cluster. »
> Camille dispose de 3 VM Ubuntu. Elle veut un cluster kubeadm standard : 1 control plane, 2 workers.

## Objectifs

- Préparer des nœuds Linux pour Kubernetes et comprendre pourquoi chaque réglage est nécessaire.
- Initialiser un control plane avec kubeadm et identifier les composants créés.
- Installer un CNI et joindre des workers.
- Gérer les nœuds : labels, cordon, drain, uncordon, taints.

## Étapes

Suivez le [guide d'installation](../../guide-installation-cluster.md), sections 2 à 7.
À chaque étape, répondez aux questions ci-dessous (on les corrige ensemble).

> Le TP 00 s'est terminé par le redémarrage du control plane. Si vous ne l'avez pas fait, retirez Docker maintenant (TP 00, étape 9).

### 1. Préparation des nœuds (sections 2 et 3) – le matin

1. Pourquoi le kubelet refuse-t-il de démarrer si le swap est actif ?
2. À quoi servent le module `br_netfilter` et `net.ipv4.ip_forward` ?
3. Que se passe-t-il si containerd utilise le driver cgroup `cgroupfs` alors que le kubelet utilise `systemd` ?
4. Pourquoi bloque-t-on les paquets avec `apt-mark hold` ?

### 2. Control plane (section 4) – avant le déjeuner

Après `kubeadm init` :

```bash
ls /etc/kubernetes/manifests/
kubectl get pods -n kube-system -o wide
kubectl get nodes
```

5. Quels composants tournent en **static pods** ? Qui les démarre ?
6. Pourquoi le nœud est-il `NotReady` ?
7. Où sont rangés les certificats du cluster ? Combien de temps sont-ils valides (`sudo kubeadm certs check-expiration`) ?

### 3. Réseau et workers (sections 5 et 6) – l'après-midi

8. Combien de pods `calico-node` attendez-vous, et pourquoi ?
9. Le token de `kubeadm join` expire au bout de combien de temps ?

### 4. Validation (section 7)

Réalisez les tests de la section 7, **sans faire le nettoyage final** : on garde le déploiement nginx pour l'étape suivante.

- [ ] 3 nœuds `Ready`
- [ ] la page nginx est renvoyée par le test busybox (DNS + réseau des services)
- [ ] `HTTP/1.1 200 OK` sur le NodePort des 3 nœuds

### 5. Gérer les nœuds

**Lire un nœud :**

```bash
kubectl describe node worker1 | sed -n '/Capacity/,/Allocated resources/p'
kubectl get nodes --show-labels
kubectl describe node controlplane | grep -A2 Taints
```

10. Quelle différence entre `Capacity` et `Allocatable` ?
11. Pourquoi aucun pod nginx ne tourne-t-il sur le control plane ?

**Donner un rôle et des labels aux workers :**

```bash
kubectl label node worker1 worker2 node-role.kubernetes.io/worker=
kubectl label node worker1 festipass/scene=plage
kubectl label node worker2 festipass/scene=remparts
kubectl get nodes -L festipass/scene
```

**Maintenance d'un nœud :** Camille doit appliquer les mises à jour de sécurité de worker2.

```bash
kubectl scale deployment nginx --replicas=4
kubectl get pods -o wide                      # répartis sur worker1 et worker2

kubectl cordon worker2                        # plus de nouveaux pods sur worker2
kubectl get nodes                             # SchedulingDisabled
kubectl scale deployment nginx --replicas=6
kubectl get pods -o wide                      # les nouveaux vont tous sur worker1

kubectl drain worker2 --ignore-daemonsets     # évacue worker2
kubectl get pods -o wide                      # tous sur worker1
```

12. Que sont devenus les pods `calico-node` et `kube-proxy` de worker2 ? Pourquoi faut-il `--ignore-daemonsets` ?

La maintenance est finie :

```bash
kubectl uncordon worker2
kubectl get pods -o wide
```

13. Les pods nginx reviennent-ils seuls sur worker2 ? Comment les rééquilibrer ?

### 6. Point de restauration

- Supprimez les objets de test : `kubectl delete svc nginx && kubectl delete deployment nginx`.
- Prenez un **snapshot des 3 VM**. Vous y reviendrez en cas de problème pendant la formation.

## Bonus

- Activez l'autocomplétion : `echo 'source <(kubectl completion bash)' >> ~/.bashrc`, l'alias `alias k=kubectl` et `complete -o default -F __start_kubectl k`.
- Retrouvez dans `/etc/kubernetes/manifests/kube-apiserver.yaml` le CIDR des services et le mode d'autorisation.
- Placez un pod sur la scène « plage » uniquement : `kubectl run plage --image=public.ecr.aws/docker/library/nginx:1.27 --overrides='{"spec":{"nodeSelector":{"festipass/scene":"plage"}}}'`. Où tourne-t-il ? Supprimez-le.
- Avec Minikube ou kind sur votre poste, combien de commandes faut-il pour obtenir un cluster ? Qu'est-ce qui manque par rapport à celui-ci ?
