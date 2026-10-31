# Correction du TP 02 – YAML, Pod, Deployment, Service

Les fichiers corrigés sont dans ce dossier, aux mêmes chemins que dans le dépôt :

- `casse-corrige.yaml` : le manifest de Yanis, avec un commentaire sur chaque erreur ;
- `k8s/20-back.yaml` et `k8s/30-front.yaml` : les manifests complétés.

Pour comparer avec votre travail : `diff -r solutions/02-yaml/k8s k8s`.

## Partie A

**Les 6 erreurs de `casse.yaml` :** `kind: pod` au lieu de `Pod` ; `app:premier` sans espace (une chaîne, pas une clé) ; `containers` écrit comme un objet au lieu d'une liste ; une tabulation devant `ports` ; `containerPort: "80"` en chaîne au lieu d'un entier ; `resources` mal indenté. `--dry-run=client` trouve les erreurs de syntaxe YAML, `--dry-run=server` celles de schéma (types, champs inconnus, valeurs refusées).

1. **Champs de premier niveau :** `apiVersion`, `kind`, `metadata`, `spec`. On n'écrit jamais `status` : c'est Kubernetes qui le remplit avec l'état réel.
2. **`ports` :** seul `containerPort` est obligatoire (`kubectl explain` affiche `-required-`).
3. **Champs ajoutés :** `uid`, `resourceVersion`, `creationTimestamp`, des valeurs par défaut (`restartPolicy: Always`, `dnsPolicy`, `terminationGracePeriodSeconds`, `imagePullPolicy`…), le nœud choisi (`nodeName`) et le token du ServiceAccount monté. `status` contient la phase, les conditions, l'IP du pod et l'état de chaque conteneur.
4. **Pod supprimé :** il n'est pas recréé, personne ne le surveille. Si son nœud tombe, il disparaît avec lui. Un pod seul ne sert qu'aux tests.
5. **Deployment :** un fichier crée 1 Deployment, 1 ReplicaSet et 3 Pods. C'est le **ReplicaSet** qui recrée le pod supprimé, pour revenir au nombre de réplicas voulu.
6. **Selector et labels :** l'API refuse un Deployment dont le `selector` ne correspond pas aux labels du template (`selector does not match template labels`). Sans cette règle, le ReplicaSet créerait des pods qu'il ne reconnaîtrait pas, à l'infini.

## Partie B

7. **readinessProbe de PostgreSQL :** `pg_isready` vérifie que la base accepte des connexions. `0/1` : le conteneur tourne, mais n'est pas encore prêt. Tant qu'il ne l'est pas, le pod ne reçoit pas de trafic du Service.
8. **Résolution de `back` :** CoreDNS résout `back` (en complet : `back.festipass.svc.cluster.local`) vers la **ClusterIP** du Service. kube-proxy redirige ensuite cette IP virtuelle vers l'un des pods du back.
9. **NodePort sur le control plane :** kube-proxy ouvre le port 30080 sur **tous** les nœuds, et redirige le trafic vers un pod du front, quel que soit le nœud où il tourne.
10. **`scale` puis `apply` :** `apply` remet `replicas: 2` : c'est le fichier qui gagne. Gardez le fichier (versionné dans Git) comme source de vérité : les commandes impératives servent à tester ou à dépanner. Exception à venir au TP 08 : quand un HPA gère les réplicas, on retire `replicas` du fichier.
11. **Sélecteur sans correspondance :** le Service existe, mais n'a aucun endpoint. Les connexions échouent (refus ou timeout).
12. **Endpoints du back :** `/readyz` teste la base. Tant que PostgreSQL n'est pas prêt, le back reste `0/1 Ready` et n'est pas exposé.
13. **Bilan :** réglés : le redémarrage automatique, plusieurs copies réparties sur plusieurs machines, la découverte des services par leur nom. Il manque : le mot de passe est toujours en clair dans les manifests (TP 03), les mises à jour sans coupure (TP 04), les données de PostgreSQL vivent dans le conteneur (TP 06).

## Bonus

- **PostgreSQL à 0 :** les pods du back passent `0/1` (la readinessProbe échoue), le Service `back` n'a plus d'endpoint, le site affiche « back injoignable ». Les pods du back ne sont pas redémarrés : c'est la **liveness** qui déclenche un redémarrage, et `/healthz` ne dépend pas de la base. À 1 réplica, tout revient seul.
- **Deux objets dans un fichier :**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello
spec:
  replicas: 2
  selector:
    matchLabels: {app: hello}
  template:
    metadata:
      labels: {app: hello}
    spec:
      containers:
        - name: nginx
          image: public.ecr.aws/docker/library/nginx:1.27
---
apiVersion: v1
kind: Service
metadata:
  name: hello
spec:
  selector: {app: hello}
  ports:
    - port: 80
```
