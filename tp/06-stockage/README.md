# TP 06 – « Maintenance d'un nœud : tous les billets vendus ont disparu »

**Durée :** 50 min · **Branche :** `tp-06-stockage` · **Correction :** `solutions/06-stockage/`, dans cette branche

## L'incident

> Mercredi, 8h30. Camille applique les mises à jour de sécurité d'un worker : elle le draine, comme au TP 01.
> Le pod PostgreSQL redémarre sur l'autre worker… avec une base vide. Les 312 pass vendus en prévente ont disparu.
> Léa : « Si ça arrive vendredi à 10h05, on ferme. »

## Objectifs

- Reproduire la perte de données et comprendre pourquoi elle se produit.
- Installer un provisionneur de volumes et une StorageClass par défaut.
- Comprendre le lien PVC → PV → stockage, et le provisionnement dynamique.
- Migrer PostgreSQL vers un StatefulSet avec un volume persistant.

## Point de départ

```bash
cd ~/festipass && git fetch
git stash -u
git checkout tp-06-stockage
kubectl apply -R -f k8s/          # -R : avec les sous-dossiers (capacite/)
```

## Étapes

### 1. Reproduire l'incident

Achetez quelques pass sur le site, puis :

```bash
kubectl get pods -l app=postgres -o wide            # notez le nœud
kubectl drain <ce nœud> --ignore-daemonsets
kubectl get pods -l app=postgres -o wide -w         # Ctrl+C quand il est 1/1 ailleurs
kubectl uncordon <ce nœud>
```

Rechargez le site.

**Question 1 :** où étaient stockées les données de PostgreSQL ? Pourquoi un `kubectl delete pod` aurait-il eu le même effet ?

### 2. Pas de stockage dans le cluster

```bash
kubectl get storageclass
kubectl get pv
```

Aucune StorageClass : le cluster ne sait pas créer de volumes. Installez **local-path-provisioner** (il crée les volumes dans un dossier du nœud) et déclarez-le par défaut :

```bash
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml
kubectl patch storageclass local-path \
  -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
kubectl get storageclass
kubectl get storageclass local-path -o yaml | grep -E 'provisioner|reclaimPolicy|volumeBindingMode'
```

### 3. Un premier volume

Lisez `tp/06-stockage/test-pvc.yaml`. Appliquez d'abord **seulement le PVC** (l'option `-l` filtre les objets du fichier par label) :

```bash
kubectl apply -f tp/06-stockage/test-pvc.yaml -l etape=1
kubectl get pvc,pv                # le PVC est Pending, aucun PV
kubectl describe pvc test-pvc | tail -3
```

Puis le pod qui l'utilise :

```bash
kubectl apply -f tp/06-stockage/test-pvc.yaml
kubectl get pod ecrivain -o wide
kubectl get pvc,pv                # Bound
kubectl get pv -o custom-columns=NOM:.metadata.name,PVC:.spec.claimRef.name,CHEMIN:.spec.hostPath.path,NOEUD:.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]
```

**Question 2 :** qui a créé le PV ? Pourquoi le PVC est-il resté `Pending` jusqu'à la création du pod (`volumeBindingMode`) ?

Supprimez le pod et recréez-le :

```bash
kubectl delete pod ecrivain
kubectl apply -f tp/06-stockage/test-pvc.yaml
kubectl logs ecrivain             # deux lignes : le fichier a survécu au pod
```

Nettoyez : `kubectl delete -f tp/06-stockage/test-pvc.yaml`, puis `kubectl get pv`.

**Question 3 :** qu'est devenu le PV ? Pourquoi (`reclaimPolicy`) ?

### 4. PostgreSQL en StatefulSet

Complétez les `TODO` de `tp/06-stockage/postgres-statefulset.yaml` (`kubectl explain statefulset.spec.volumeClaimTemplates`), puis remplacez `k8s/10-postgres.yaml` par ce fichier :

```bash
cp tp/06-stockage/postgres-statefulset.yaml k8s/10-postgres.yaml
```

Le Service `postgres` devient *headless* : son `clusterIP` ne peut pas être modifié, et un Deployment ne se transforme pas en StatefulSet. On supprime les anciens objets avant d'appliquer :

```bash
kubectl delete deployment postgres
kubectl delete service postgres
kubectl apply -f k8s/10-postgres.yaml
kubectl get statefulset,pods,pvc -l app=postgres
kubectl get pods -w              # Ctrl+C quand postgres-0 et le back sont prêts
```

**Questions :**

4. Comment s'appelle le pod ? Et le PVC ? D'où vient ce nom ?
5. Le back se connecte toujours à `postgres` : que renvoie maintenant le DNS ? (`kubectl run test --rm -it --image=public.ecr.aws/docker/library/busybox:1.36 --restart=Never -- nslookup postgres`)

### 5. Le test de Léa

Achetez des pass, puis rejouez l'incident :

```bash
kubectl delete pod postgres-0
kubectl get pods -l app=postgres -w           # Ctrl+C quand postgres-0 est prêt
```

Rechargez le site : les billets sont toujours là.

Maintenant la maintenance de Camille :

```bash
kubectl get pods postgres-0 -o wide           # notez le nœud
kubectl drain <ce nœud> --ignore-daemonsets
kubectl get pods postgres-0 -o wide
kubectl describe pod postgres-0 | tail -5
```

**Question 6 :** postgres-0 reste `Pending`. Pourquoi ? Que se passerait-il si ce nœud était perdu définitivement ?

```bash
kubectl uncordon <ce nœud>
kubectl get pods postgres-0 -w                # il repart, avec ses données
```

## Questions de fin

7. Supprimez-vous les données en supprimant le StatefulSet ? (ne le faites pas : cherchez dans la documentation ce que devient le PVC)
8. Pourquoi un StatefulSet plutôt qu'un Deployment avec un PVC ?
9. Quelle solution de stockage pour la production, pour que PostgreSQL puisse changer de nœud ?

## Bonus

- Créez une StorageClass `local-path-retain` avec `reclaimPolicy: Retain` et testez la suppression d'un PVC.
- Passez le StatefulSet à 2 réplicas : postgres-1 a-t-il les billets ? Pourquoi un StatefulSet ne suffit-il pas à faire de la réplication ? Revenez à 1 (et supprimez le PVC `data-postgres-1`).
- Retrouvez sur le nœud le dossier du volume : `sudo ls /opt/local-path-provisioner/` (sur le worker qui porte postgres-0).
