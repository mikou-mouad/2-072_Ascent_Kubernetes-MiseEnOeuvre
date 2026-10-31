# TP 09 – « Depuis n'importe quel pod, je lis votre base »

**Durée :** 55 min · **Branche :** `tp-09-securite` · **Correction :** `solutions/09-securite/`, dans cette branche

## L'incident

> Jeudi, 14h30. Avant l'ouverture, Léa a demandé un audit de sécurité. L'auditrice lance un simple pod dans le namespace de recette… et se connecte directement à PostgreSQL.
> Son rapport tient en trois lignes : « Tous vos pods tournent en root. N'importe quel pod du cluster joint votre base. Votre développeur a le kubeconfig administrateur. »
> Camille : « On a 24 heures pour fermer tout ça. »

## Objectifs

- Donner à un utilisateur les droits dont il a besoin, et pas plus (RBAC).
- Retirer aux pods ce dont ils n'ont pas besoin : token d'API, root, capacités Linux.
- Imposer ces règles à tout le namespace avec Pod Security Admission.
- Cloisonner le réseau avec des NetworkPolicies.

## Point de départ

```bash
cd ~/festipass && git fetch
git stash -u
git checkout tp-09-securite
kubectl apply -R -f k8s/
```

## Étapes

### 1. Ce que voit un pod

Rejouez l'audit : un pod quelconque, dans un autre namespace, avec un client PostgreSQL.

Le pirate tourne dans la recette, dont le budget est limité (TP 05) : vérifiez qu'il reste de la place, en supprimant le calcul de statistiques s'il tourne encore.

```bash
kubectl -n festipass-recette delete deployment stats --ignore-not-found
kubectl -n festipass-recette describe resourcequota budget
```

```bash
kubectl run pirate -n festipass-recette --rm -it --restart=Never \
  --image=public.ecr.aws/docker/library/postgres:16 -- bash
```

Dans le pod :

```bash
id                                                        # qui suis-je ?
ls /var/run/secrets/kubernetes.io/serviceaccount/         # un token d'API est monté
pg_isready -h postgres.festipass -t 3                     # la base répond-elle ?
timeout 3 bash -c '</dev/tcp/back.festipass/8080' && echo "back : ouvert"
PGPASSWORD=maree-haute-2026 psql -h postgres.festipass -U festipass -c 'select count(*) from billets'
exit
```

Et dans les pods de FestiPass :

```bash
kubectl exec deploy/back -- id
kubectl exec deploy/back -- ls /var/run/secrets/kubernetes.io/serviceaccount/
kubectl exec deploy/front -- id
kubectl exec postgres-0 -- id
```

**Question 1 :** listez tout ce que l'auditrice a pu faire ou voir. Lesquels de ces accès sont vraiment nécessaires à FestiPass ?

### 2. Les droits de Yanis (RBAC)

Aujourd'hui, Yanis utilise le kubeconfig administrateur. Il doit pouvoir observer son application et livrer (rollout), mais pas lire les Secrets, ni supprimer quoi que ce soit, ni toucher aux autres namespaces.

```bash
kubectl auth can-i --list --as yanis -n festipass       # rien pour l'instant
```

Complétez les `TODO` de `tp/09-securite/rbac-yanis.yaml` (`kubectl api-resources -o wide` donne les groupes et les verbes), puis :

```bash
mkdir -p k8s/securite
cp tp/09-securite/rbac-yanis.yaml k8s/securite/20-rbac-yanis.yaml
kubectl apply -f k8s/securite/20-rbac-yanis.yaml
```

Vérifiez en vous faisant passer pour Yanis :

```bash
kubectl get pods --as yanis -n festipass                                  # oui
kubectl logs deploy/back --tail=2 --as yanis -n festipass                 # oui
kubectl rollout restart deployment front --as yanis -n festipass          # oui
kubectl get secrets --as yanis -n festipass                               # non
kubectl delete deployment back --as yanis -n festipass                    # non
kubectl get pods --as yanis -n kube-system                                # non
kubectl auth can-i create pods/exec --as yanis -n festipass               # ?
```

**Question 2 :** pourquoi un `Role` et un `RoleBinding`, plutôt qu'un `ClusterRole` et un `ClusterRoleBinding` ? Comment Kubernetes sait-il que la personne qui se connecte s'appelle « yanis » ?

### 3. Des pods qui en font moins

**ServiceAccounts.** Aucun composant de FestiPass n'appelle l'API Kubernetes : ils n'ont pas besoin de token. Créez `k8s/securite/10-serviceaccounts.yaml` avec 4 ServiceAccounts (`back`, `front`, `postgres`, `sauvegarde`), dans `festipass`, avec `automountServiceAccountToken: false`. Appliquez-le.

**Ce que dirait le profil « restricted » :** avant d'imposer quoi que ce soit, demandez à l'API ce qui serait refusé :

```bash
kubectl label --dry-run=server --overwrite namespace festipass \
  pod-security.kubernetes.io/enforce=restricted
```

**Corrigez les manifests** jusqu'à ce que cette commande n'affiche plus d'avertissement. Pour chaque pod (`10-postgres.yaml`, `20-back.yaml`, `30-front.yaml`, et le template du CronJob dans `40-sauvegarde.yaml`) :

- au niveau du **pod** (`spec` du template) : `serviceAccountName` (le ServiceAccount du composant), et un `securityContext` avec `runAsNonRoot: true` et `seccompProfile: {type: RuntimeDefault}` ;
- au niveau du **conteneur** : un `securityContext` avec `allowPrivilegeEscalation: false` et `capabilities: {drop: ["ALL"]}` ;
- pour le **back**, en plus : `readOnlyRootFilesystem: true` (il n'écrit rien sur son disque) ;
- pour **postgres et la sauvegarde** : l'image démarre en root par défaut. Ajoutez au `securityContext` du pod `runAsUser: 999`, `runAsGroup: 999` et `fsGroup: 999` (l'utilisateur `postgres` de l'image).

```bash
kubectl apply -f k8s/
kubectl rollout status deployment back
kubectl rollout status deployment front
kubectl rollout status statefulset postgres
```

La vérification porte sur **tous** les pods du namespace, y compris ceux des Jobs terminés (`Completed`) : les sauvegardes lancées au TP 07 tournaient en root. Supprimez ces Jobs (le CronJob, lui, reste), puis refaites la vérification :

```bash
kubectl delete jobs --all
kubectl get pods                          # plus que les pods de FestiPass, tous récents
kubectl label --dry-run=server --overwrite namespace festipass \
  pod-security.kubernetes.io/enforce=restricted
```

Il reste un avertissement ? Le pod cité a été créé avant vos modifications : regardez son âge et son propriétaire (`kubectl get pod <nom> -o jsonpath='{.metadata.ownerReferences[0].name}'`).

Vérifiez que le site fonctionne et que les billets sont toujours là, puis que la sauvegarde fonctionne encore : `kubectl create job --from=cronjob/sauvegarde sauvegarde-securisee`, puis ses logs.

**Imposer la règle :** ajoutez les labels Pod Security au namespace dans `k8s/00-namespace.yaml` :

```yaml
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl run pirate -n festipass --image=public.ecr.aws/docker/library/busybox:1.36 -- sleep 3600
```

**Question 3 :** que répond l'API au dernier `kubectl run` ? Pourquoi est-ce mieux que de compter sur chacun pour écrire des `securityContext` ?

### 4. Cloisonner le réseau

Le chemin légitime : festivaliers → front → back → postgres, et la sauvegarde → postgres. Rien d'autre.

Complétez les `TODO` de `tp/09-securite/networkpolicies.yaml` (`kubectl explain networkpolicy.spec.ingress`), puis :

```bash
cp tp/09-securite/networkpolicies.yaml k8s/securite/30-networkpolicies.yaml
kubectl apply -f k8s/securite/30-networkpolicies.yaml
kubectl get networkpolicies
```

Vérifiez que le site fonctionne toujours depuis ClientWeb ou l'adresse du tunnel (achetez un pass), et que la sauvegarde aussi (`sauvegarde-reseau`).

### 5. L'auditrice repasse

Relancez le pod `pirate` de l'étape 1, et les mêmes commandes.

**Questions :**

4. Qu'est-ce qui a changé pour le pirate ? Qu'est-ce qui n'a pas changé (pensez au mot de passe) ?
5. Les probes du kubelet passent-elles encore, alors que tout est refusé par défaut ? Pourquoi ?

## Questions de fin

6. Reprenez le tableau du TP 00 : toutes les lignes sont-elles réglées ?
7. Il reste un risque sur les Secrets : qui peut encore lire le mot de passe de la base ?

## Bonus

- Donnez un vrai certificat à Yanis : `bash tp/09-securite/creer-utilisateur.sh yanis developpeurs`, puis `KUBECONFIG=~/utilisateurs/yanis/yanis.kubeconfig kubectl get pods`. Que donne `kubectl auth whoami` avec ce kubeconfig ?
- Rendez le système de fichiers du front en lecture seule : nginx a besoin d'écrire dans `/tmp` et `/etc/nginx/conf.d` : montez-y des volumes `emptyDir`.
- Ajoutez une politique `Egress` : le back ne peut joindre que postgres… et le DNS (port 53 UDP et TCP vers kube-system). Que se passe-t-il si on oublie le DNS ?
- Le Job `tp/07-controleurs/restauration-job.yaml` est maintenant refusé. Corrigez-le.
