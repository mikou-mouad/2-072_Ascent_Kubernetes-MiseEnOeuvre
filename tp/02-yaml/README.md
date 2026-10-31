# TP 02 – YAML, Pod, Deployment, Service : FestiPass arrive sur le cluster

**Durée :** 2 h (partie A : 1 h, partie B : 1 h) · **Branche :** `tp-02-yaml` · **Correction :** `solutions/02-yaml/`, dans cette branche

## L'incident

> Le cluster est prêt. Léa veut voir la billetterie tourner dessus avant la fin de la semaine.
> Problème : Yanis n'a jamais écrit une ligne de YAML Kubernetes. Camille propose d'apprendre sur un pod de test, puis de migrer composant par composant : la base, l'API, le front.

## Objectifs

- Lire et écrire du YAML sans se faire piéger par l'indentation.
- Trouver la structure d'un objet avec `kubectl explain` et générer un manifest avec `--dry-run`.
- Comprendre la différence entre un Pod seul et un Deployment.
- Déployer une application complète : namespace, Deployments, Services ClusterIP et NodePort, probes.

## Avant de commencer : récupérer les fichiers

Sur le **control plane** :

```bash
cd ~/festipass && git fetch
git stash -u                      # met de côté d'éventuelles modifications du TP 00
git checkout tp-02-yaml
```

Toutes les commandes se lancent depuis `~/festipass`.

---

## Partie A – Premiers pas en YAML (1 h)

### A1. Réparer le manifest de Yanis

`tp/02-yaml/casse.yaml` contient **6 erreurs**. kubectl vous aide à les trouver :

```bash
kubectl apply -f tp/02-yaml/casse.yaml --dry-run=client     # erreurs de syntaxe YAML
kubectl apply -f tp/02-yaml/casse.yaml --dry-run=server     # erreurs vues par l'API server
```

Corrigez le fichier jusqu'à obtenir `pod/premier-pod created (server dry run)`. Astuce : `cat -A` affiche les tabulations (`^I`).

### A2. Explorer l'API

```bash
kubectl api-resources | head -20
kubectl explain pod
kubectl explain pod.spec.containers.ports
kubectl explain deployment.spec --recursive | less
```

**Questions :**

1. Quels sont les 4 champs de premier niveau de presque tous les objets ? Lequel n'écrit-on jamais ?
2. Quels champs de `ports` sont obligatoires ?

### A3. Un pod

Faites écrire le YAML par kubectl plutôt que de partir d'une page blanche :

```bash
kubectl run hello --image=public.ecr.aws/docker/library/nginx:1.27 --port=80 \
  --labels=app=hello --dry-run=client -o yaml > tp/02-yaml/hello-pod.yaml
cat tp/02-yaml/hello-pod.yaml
kubectl apply -f tp/02-yaml/hello-pod.yaml
kubectl get pods -o wide
kubectl get pod hello -o yaml | less          # comparez avec votre fichier
```

**Question 3 :** quels champs Kubernetes a-t-il ajoutés à votre manifest ? Que contient la section `status` ?

Testez le pod, puis supprimez-le :

```bash
kubectl port-forward pod/hello 8080:80 &      # tunnel vers le pod
curl -s localhost:8080 | head -4
kill %1

kubectl delete pod hello
kubectl get pods
```

**Question 4 :** le pod est-il recréé ? Que se passerait-il si son nœud tombait ?

### A4. Un Deployment

```bash
kubectl create deployment hello --image=public.ecr.aws/docker/library/nginx:1.27 \
  --replicas=3 --dry-run=client -o yaml > tp/02-yaml/hello-deploy.yaml
kubectl apply -f tp/02-yaml/hello-deploy.yaml
kubectl get deployment,replicaset,pods -l app=hello
```

Supprimez un des pods (`kubectl delete pod <nom>`), puis relancez la commande précédente.

**Questions :**

5. Combien d'objets ont été créés à partir d'un seul fichier ? Qui recrée le pod supprimé ?
6. Dans `hello-deploy.yaml`, repérez le `selector` et les `labels` du template. Que se passerait-il s'ils étaient différents ?

Nettoyage : `kubectl delete -f tp/02-yaml/hello-deploy.yaml`.

---

## Partie B – FestiPass sur le cluster (1 h)

### Ce qu'on migre

Regardez `app/docker-compose.yml` : c'est l'application telle qu'elle tournait sur la VM (TP 00).

| Composant | Image | Port | Configuration |
|-----------|-------|------|---------------|
| postgres  | `public.ecr.aws/docker/library/postgres:16` | 5432 | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| back      | `ghcr.io/mikou-mouad/festipass-back:1.0` | 8080 | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `FESTIVAL`, `CLE_SIGNATURE` |
| front     | `ghcr.io/mikou-mouad/festipass-front:1.0` | 8080 | appelle le back sur `http://back:8080` |

Routes utiles du back : `/healthz` (vivant), `/readyz` (base joignable), `/api/passes`, `/api/billets`, `/api/stats`, `/api/version`.

### B1. Namespace

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl config set-context --current --namespace=festipass
kubectl get pods                       # « No resources found in festipass namespace »
```

### B2. PostgreSQL

`k8s/10-postgres.yaml` est fourni complet. Lisez-le, puis appliquez-le.

```bash
kubectl apply -f k8s/10-postgres.yaml
kubectl get pods -w                    # Ctrl+C quand le pod est 1/1 Running
kubectl exec -it deploy/postgres -- psql -U festipass -c '\l'
```

**Question 7 :** que fait la `readinessProbe` de PostgreSQL ? Que signifie `0/1` dans la colonne `READY` ?

### B3. Le back

Complétez les `TODO` de `k8s/20-back.yaml`, puis :

```bash
kubectl apply -f k8s/20-back.yaml
kubectl get pods -l app=back
kubectl logs -l app=back --tail=5
kubectl get endpointslices -l kubernetes.io/service-name=back
```

Testez l'API depuis l'intérieur du cluster :

```bash
kubectl run test --rm -it --image=public.ecr.aws/docker/library/busybox:1.36 --restart=Never -- \
  wget -qO- http://back:8080/api/passes
```

**Question 8 :** le nom `back` fonctionne dans le pod de test. Qui le résout, et vers quelle adresse ? (`kubectl get svc back`)

### B4. Le front

Complétez les `TODO` de `k8s/30-front.yaml` et appliquez-le.

Le Service est de type **NodePort** : le site répond sur le port `30080` de **chaque nœud** du cluster.

| Nœud | INTERNAL-IP |
|------|-------------|
| controlplane | 10.10.0.10 |
| worker1 | 10.10.0.20 |
| worker2 | 10.10.0.30 |

Depuis la machine **ClientWeb**, ouvrez `http://10.10.0.20:30080` et achetez des pass. Partout où un énoncé écrit `<IP d'un nœud>`, utilisez l'une de ces adresses.

**Question 9 :** pourquoi le site répond-il aussi sur `10.10.0.10`, alors qu'aucun pod du front ne tourne sur le control plane ?

### B5. Scaling et auto-réparation

```bash
kubectl scale deployment back --replicas=3
kubectl get pods -o wide
```

Rafraîchissez la page plusieurs fois : le bandeau indique quel pod du back a répondu.
Supprimez un pod du back (`kubectl delete pod <nom>`) et observez ce que fait le Deployment (`kubectl get pods -w`).

**Question 10 :** vous avez lancé `kubectl scale` : le fichier `k8s/20-back.yaml` dit pourtant `replicas: 2`. Que se passera-t-il au prochain `kubectl apply -f k8s/` ? Quelle source de vérité garder ?

Remettez l'état du fichier : `kubectl apply -f k8s/`.

## Questions de fin

11. Que se passe-t-il si le sélecteur d'un Service ne correspond à aucun pod ?
12. Pourquoi le back n'apparaît-il dans les endpoints qu'une fois la base prête ?
13. Comparez avec le tableau du TP 00 : qu'a-t-on déjà réglé ? Que manque-t-il encore ?

## Bonus

- Passez PostgreSQL à 0 réplica : que deviennent les pods du back, les endpoints et le site ? Remettez-le à 1.
- `kubectl get pods -o custom-columns=NOM:.metadata.name,NOEUD:.spec.nodeName,IP:.status.podIP`
- Écrivez un manifest qui contient deux objets (`---`) : un Deployment `hello` et son Service ClusterIP. Appliquez-le en une commande, testez-le depuis un pod busybox, puis supprimez-le avec `kubectl delete -f`.
