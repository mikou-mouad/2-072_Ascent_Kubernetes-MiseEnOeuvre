# TP 01 – « Camille, il nous faut un cluster »

**Durée :** 3 h 30 (45 min avant le déjeuner, 2 h 45 l'après-midi) · **Branche :** `tp-01-installation` · **Correction :** `solutions/01-installation/`, dans cette branche

## L'incident

> Léa a tranché : « Cette année, on passe sur Kubernetes. Camille, il nous faut un cluster. »
> Camille dispose de 3 VM Ubuntu. Elle veut un cluster kubeadm standard : 1 control plane, 2 workers.

## Objectifs

- Préparer des nœuds Linux pour Kubernetes et comprendre pourquoi chaque réglage est nécessaire.
- Initialiser un control plane avec kubeadm et identifier les composants créés.
- Installer un CNI et joindre des workers.
- Voir le rôle d'un composant du control plane en l'arrêtant.
- Gérer les nœuds : labels, taints, cordon, drain, uncordon, retrait et réintégration.

## Étapes

Suivez le [guide d'installation](../../guide-installation-cluster.md), sections 2 à 7.
À chaque étape, répondez aux questions ci-dessous (on les corrige ensemble).

> Le TP 00 s'est terminé par le redémarrage du control plane. Si vous ne l'avez pas fait, retirez Docker maintenant (TP 00, étape 9).
>
> Logs « shell integration » à chaque ligne sur une machine ? `unset PROMPT_COMMAND`, `PS1='\u@\h:\w\$ '` et `PS0=''` (détail et version permanente : guide, section 2).

### 1. Préparation des nœuds (sections 2 et 3) – le matin

1. Pourquoi le kubelet refuse-t-il de démarrer si le swap est actif ?
2. À quoi servent le module `br_netfilter` et `net.ipv4.ip_forward` ?
3. Que se passe-t-il si containerd utilise le driver cgroup `cgroupfs` alors que le kubelet utilise `systemd` ?
4. Pourquoi bloque-t-on les paquets avec `apt-mark hold` ?

### 2. Control plane (section 4) – l'après-midi

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

Réalisez les tests de la section 7. Gardez le déploiement `nginx` et son Service : ils servent aux étapes 5 à 7, on les supprime à l'étape 8.

- [ ] 3 nœuds `Ready`
- [ ] la page nginx est renvoyée par le test busybox (DNS + réseau des services)
- [ ] `HTTP/1.1 200 OK` sur le NodePort des 3 nœuds

### 5. Le control plane sans scheduler

Les composants du control plane sont des static pods : le kubelet les démarre à partir des fichiers de `/etc/kubernetes/manifests`. Retirez celui du scheduler :

```bash
sudo mv /etc/kubernetes/manifests/kube-scheduler.yaml /tmp/
kubectl -n kube-system get pods -l component=kube-scheduler     # disparaît après quelques secondes
kubectl scale deployment nginx --replicas=4
kubectl get pods -o wide
kubectl describe pod <un pod Pending> | tail -3
```

10. Les nouveaux pods existent mais restent `Pending`, sans nœud. Qui les a créés ? Pourquoi ne démarrent-ils pas ? Les pods qui tournaient déjà sont-ils touchés ?

Remettez le scheduler et observez :

```bash
sudo mv /tmp/kube-scheduler.yaml /etc/kubernetes/manifests/
kubectl get pods -o wide -w          # Ctrl+C quand tout est Running
kubectl scale deployment nginx --replicas=2
```

### 6. Gérer les nœuds

**Lire un nœud :**

```bash
kubectl describe node worker1 | sed -n '/Capacity/,/Allocated resources/p'
kubectl get nodes --show-labels
kubectl describe node controlplane | grep -A2 Taints
```

11. Quelle différence entre `Capacity` et `Allocatable` ?
12. Pourquoi aucun pod nginx ne tourne-t-il sur le control plane ?

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

13. Que sont devenus les pods `calico-node` et `kube-proxy` de worker2 ? Pourquoi faut-il `--ignore-daemonsets` ?

La maintenance est finie :

```bash
kubectl uncordon worker2
kubectl get pods -o wide
```

14. Les pods nginx reviennent-ils seuls sur worker2 ? Comment les rééquilibrer ?

### 7. Retirer puis réintégrer un worker

Le disque de worker2 doit être changé : Camille le retire du cluster, puis le réintègre.

Sur le **control plane** :

```bash
kubectl drain worker2 --ignore-daemonsets
kubectl delete node worker2
kubectl get nodes
```

Sur **worker2** : effacez tout ce que `kubeadm join` avait configuré.

```bash
sudo kubeadm reset -f
sudo rm -rf /etc/cni/net.d
```

Sur le **control plane**, générez une nouvelle commande d'adhésion, puis lancez-la avec `sudo` sur **worker2** :

```bash
kubeadm token create --print-join-command
```

```bash
kubectl get nodes -w                 # Ctrl+C quand worker2 est Ready
kubectl get nodes -L festipass/scene
```

15. Quels labels worker2 a-t-il perdus ? Pourquoi ? Remettez-les (étape 6).
16. Pourquoi générer une nouvelle commande `join` plutôt que de reprendre celle du matin ? Que contient-elle en plus du token ?

### 8. Nettoyage

Les objets de test ont servi : supprimez-les.

```bash
kubectl delete svc nginx && kubectl delete deployment nginx
kubectl get all                     # il ne reste que le Service kubernetes
```

### 9. Point de restauration

- Prenez un **snapshot des 3 VM**. Vous y reviendrez en cas de problème pendant la formation.

## Bonus

- Activez l'autocomplétion : `echo 'source <(kubectl completion bash)' >> ~/.bashrc`, l'alias `alias k=kubectl` et `complete -o default -F __start_kubectl k`.
- Retrouvez dans `/etc/kubernetes/manifests/kube-apiserver.yaml` le CIDR des services et le mode d'autorisation.
- Placez un pod sur la scène « plage » uniquement : `kubectl run plage --image=public.ecr.aws/docker/library/nginx:1.27 --overrides='{"spec":{"nodeSelector":{"festipass/scene":"plage"}}}'`. Où tourne-t-il ? Supprimez-le.
- Avec Minikube ou kind sur votre poste, combien de commandes faut-il pour obtenir un cluster ? Qu'est-ce qui manque par rapport à celui-ci ?
