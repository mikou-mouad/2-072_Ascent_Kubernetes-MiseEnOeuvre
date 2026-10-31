# Guide d'installation d'un cluster Kubernetes

**3 VM – kubeadm – containerd – CNI Calico – Kubernetes v1.34**

## 1. Vue d'ensemble

Ce guide construit un cluster Kubernetes de 3 nœuds (1 control plane, 2 workers) pour les travaux pratiques de la formation **Kubernetes – Mise en œuvre**.
Les sections 2 et 3 s'exécutent sur **tous les nœuds**, les suivantes comme indiqué.

| Nœud         | Rôle          | Adresse IP                                |
|--------------|---------------|-------------------------------------------|
| controlplane | Control plane | 10.10.0.20                                |
| worker1      | Worker        | 10.10.0.30                                |
| worker2      | Worker        | 10.10.0.40 (à adapter à l'adresse réelle) |
| ClientWeb    | Poste avec navigateur, hors cluster | 10.10.0.10            |

| Composant             | Choix                                                                 |
|-----------------------|-----------------------------------------------------------------------|
| OS                    | Ubuntu (22.04 / 24.04)                                                |
| Runtime de conteneurs | containerd (`SystemdCgroup = true`)                                   |
| Kubernetes            | v1.34.x (kubeadm, kubelet, kubectl, paquets bloqués avec `hold`)      |
| CNI                   | Calico v3.31.0 via l'opérateur Tigera (applique les NetworkPolicies)  |
| CIDR des pods         | 192.168.0.0/16 (valeur par défaut de Calico, sans conflit avec 10.10.0.0/24) |

### Prérequis

2 CPU minimum et 4 Go de RAM par VM (8 Go sur les workers, c'est plus confortable pour le TP d'autoscaling), nom d'hôte, adresse MAC et `product_uuid` uniques pour chaque VM, et connectivité complète entre les nœuds.

Ports à ouvrir entre les nœuds : TCP 6443, 2379-2380, 10250, 30000-32767 (NodePorts), ainsi que les ports Calico TCP 179 (BGP), TCP 5473 (Typha) et UDP 4789 (VXLAN).

> **Attention : les adresses IP sont attribuées ici par DHCP.** Si l'adresse du control plane change, le cluster ne fonctionne plus. Réservez les trois adresses dans le DHCP ou configurez des IP statiques **avant** de lancer `kubeadm init`.

## 2. Préparer les 3 nœuds

> **Le terminal affiche des logs « shell integration » à chaque ligne ?** C'est le prompt de la session qui est mal configuré, pas un problème de la VM. Corrigez-le pour la session en cours :
>
> ```bash
> unset PROMPT_COMMAND
> PS1='\u@\h:\w\$ '
> ```
>
> C'est à retaper à chaque nouvelle session SSH (et après chaque redémarrage), sauf si vous l'ajoutez une fois pour toutes à la fin de `~/.bashrc`, sur chaque machine :
>
> ```bash
> echo 'unset PROMPT_COMMAND; PS1="\u@\h:\w\$ "' >> ~/.bashrc
> source ~/.bashrc
> ```
>
> Les logs reviennent à la session suivante ? Un autre fichier redéfinit `PROMPT_COMMAND` après `~/.bashrc`. Trouvez-le :
>
> ```bash
> grep -n "machineid\|PROMPT_COMMAND" ~/.bashrc ~/.profile /etc/profile.d/* 2>/dev/null
> ```
>
> Ajoutez la même ligne à la fin du fichier trouvé (remplacez `<fichier>` par son nom ; `sudo` est nécessaire pour un fichier de `/etc`) :
>
> ```bash
> echo 'unset PROMPT_COMMAND; PS1="\u@\h:\w\$ "' | sudo tee -a <fichier>
> ```

> **Docker a été installé au TP 00 sur le control plane ?** Il doit avoir été désinstallé, et la VM redémarrée (dernière étape du TP 00) : Docker modifie les règles iptables et gêne le réseau des pods.

### 2.1 Désactiver le swap, charger les modules noyau, configurer sysctl

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay && sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system
```

### 2.2 Installer et configurer containerd

```bash
sudo apt-get update && sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' \
  /etc/containerd/config.toml
sudo systemctl restart containerd && sudo systemctl enable containerd
```

### 2.3 Installer kubeadm, kubelet et kubectl

```bash
KVER=v1.34
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/$KVER/deb/Release.key | \
  sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] \
https://pkgs.k8s.io/core:/stable:/$KVER/deb/ /" | \
  sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

## 3. Vérifier la préparation (sur chaque nœud)

Toutes les vérifications doivent réussir sur les 3 nœuds avant de continuer. Les versions doivent être identiques sur tous les nœuds.

| Vérification        | Commande                                                                                             | Résultat attendu                 |
|---------------------|------------------------------------------------------------------------------------------------------|----------------------------------|
| Swap désactivé      | `swapon --show`                                                                                      | Aucune sortie                    |
| Modules             | `lsmod \| grep -E 'overlay\|br_netfilter'`                                                           | Les deux apparaissent            |
| Sysctl              | `sysctl net.bridge.bridge-nf-call-iptables net.bridge.bridge-nf-call-ip6tables net.ipv4.ip_forward` | Tous à `1`                       |
| containerd          | `systemctl is-active containerd`                                                                     | `active`                         |
| Driver cgroup       | `grep SystemdCgroup /etc/containerd/config.toml`                                                     | `SystemdCgroup = true`           |
| Runtime             | `sudo ctr version`                                                                                   | Client et Server affichés        |
| Paquets             | `kubeadm version -o short; apt-mark showhold`                                                        | Même version ; 3 paquets bloqués |
| Identité            | `hostnamectl --static; cat /sys/class/dmi/id/product_uuid`                                           | Unique pour chaque VM            |

Sur le control plane, lancez une dernière vérification préalable : `sudo kubeadm init phase preflight`.
Le message *remote version is much newer, falling back to stable-1.34* est sans conséquence.
Vous pouvez aussi pré-télécharger les images avec `sudo kubeadm config images pull`.

### Trouver l'IP privée et tester la connectivité

```bash
ip -4 addr show ens18        # ou : hostname -I
ping -c 2 10.10.0.20         # depuis chaque worker vers le control plane
```

## 4. Initialiser le control plane

À exécuter **uniquement sur controlplane**.

```bash
sudo kubeadm init \
  --pod-network-cidr=192.168.0.0/16 \
  --apiserver-advertise-address=10.10.0.20

mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

Copiez la commande `kubeadm join ...` affichée à la fin. En cas de perte, régénérez-la avec `kubeadm token create --print-join-command`.

> **Vous avez déjà lancé `init` avec un autre CIDR de pods ?** Réinitialisez d'abord :
> `sudo kubeadm reset -f; sudo rm -rf /etc/cni/net.d $HOME/.kube`, puis relancez `init`.

## 5. Installer Calico (control plane)

```bash
CALICO=v3.31.0
BASE=https://raw.githubusercontent.com/projectcalico/calico/$CALICO/manifests
kubectl create -f $BASE/operator-crds.yaml
kubectl create -f $BASE/tigera-operator.yaml
kubectl create -f $BASE/custom-resources.yaml

watch kubectl get pods -n calico-system
```

Attendez que tous les pods soient `Running`. Calico se trouve dans le namespace `calico-system`.
Utilisez `create` et non `apply` : les CRD sont trop volumineuses pour `apply`.

## 6. Joindre les workers

Exécutez la commande sauvegardée sur **worker1** et **worker2**.

```bash
sudo kubeadm join 10.10.0.20:6443 --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash>
```

## 7. Vérifier le cluster et tester le réseau

À exécuter sur le control plane. `kubectl` ne fonctionne que là où un kubeconfig existe : sur les workers, il échoue avec *localhost:8080 connection refused*. C'est normal.

```bash
kubectl get nodes -o wide                    # 3 nœuds Ready
kubectl get pods -n calico-system -o wide    # un calico-node par nœud
kubectl get pods -A                          # coredns Running

kubectl create deployment nginx --image=public.ecr.aws/docker/library/nginx:1.27 --replicas=2
kubectl expose deployment nginx --type=NodePort --port=80
kubectl get svc nginx                        # noter le NodePort

# Réseau pod-à-pod, DNS et réseau des services
kubectl run test --rm -it --image=public.ecr.aws/docker/library/busybox:1.36 --restart=Never -- \
  wget -qO- http://nginx

# NodePort sur chaque nœud (remplacer 31690 par votre port)
curl -sI http://10.10.0.20:31690 | head -1
curl -sI http://10.10.0.30:31690 | head -1
curl -sI http://10.10.0.40:31690 | head -1

# Nettoyage : PAS PENDANT LE TP 01, qui réutilise ce déploiement nginx (il le supprime à la fin)
kubectl delete svc nginx && kubectl delete deployment nginx
```

**Critères de réussite :** tous les nœuds sont `Ready`, la page d'accueil nginx est renvoyée par le test busybox, et les trois nœuds répondent `HTTP/1.1 200 OK`.

## 8. Dépannage

| Symptôme                              | Cause probable / solution                                                                 |
|---------------------------------------|-------------------------------------------------------------------------------------------|
| Nœuds bloqués en `NotReady`           | CNI non installé ou encore en démarrage. Vérifier `kubectl get pods -n calico-system`.     |
| kubelet redémarre en boucle           | Swap toujours actif, ou `SystemdCgroup` différent de `true` dans la config containerd.    |
| `join` expire (timeout)               | Pare-feu bloquant TCP 6443, ou IP erronée / token expiré.                                 |
| Pods bloqués en `ContainerCreating`   | Problème de CNI. Lancer `kubectl describe pod <nom>`.                                     |
| Le NodePort ne répond que sur un nœud | Pare-feu bloquant le trafic Calico (UDP 4789, TCP 179, TCP 5473).                          |
| `wget: bad address`                   | CoreDNS ne tourne pas. Vérifier `kubectl get pods -n kube-system`.                        |
| Échecs étranges entre nœuds           | Le MTU est de 9000 sur ces VM. Vérifier que tous les nœuds utilisent le même MTU.         |
| Logs « shell integration » à chaque ligne | Prompt mal configuré : `unset PROMPT_COMMAND` puis `PS1='\u@\h:\w\$ '`, ou à la fin de `~/.bashrc` ; s'ils reviennent, chercher le fichier qui redéfinit `PROMPT_COMMAND` (section 2). |
| `kubectl: localhost:8080 refused`     | Pas de kubeconfig sur cette machine. Exécuter kubectl sur le control plane.               |

## 9. Avant de commencer les TP

Le cluster est prêt tel quel. Gardez les éléments suivants pour le TP correspondant, afin de ne pas déflorer l'exercice.

| TP                              | À ajouter le moment venu                                                                       |
|---------------------------------|------------------------------------------------------------------------------------------------|
| 04 – Cycle de vie               | metrics-server (nécessite `--kubelet-insecure-tls` sur un cluster kubeadm).                     |
| 06 – Stockage                   | Un provisionneur dynamique (local-path-provisioner), défini comme StorageClass par défaut.      |
| 08 – Autoscaling                | Rien de plus : metrics-server (TP 04) et les requests (TP 05) suffisent.                        |
| 09 – Sécurité                   | Rien de plus : Calico applique déjà les NetworkPolicies.                                       |

### Précautions recommandées

1. Faire un snapshot des 3 VM maintenant, comme point de restauration propre.
2. Réserver ou fixer les adresses IP des 3 nœuds.
3. Supprimer les objets de test nginx.
4. Vérifier la RAM des workers (4 Go minimum, 8 Go idéalement).
