# TP 07 – « Personne n'a fait la sauvegarde cette nuit »

**Durée :** 45 min (35 min avant le déjeuner, 10 min après) · **Branche :** `tp-07-controleurs` · **Correction :** `solutions/07-controleurs/`, dans cette branche

## L'incident

> Mercredi, 9h00. Depuis l'incident d'hier, Camille sauvegarde la base chaque soir, à la main, avec `pg_dump`.
> Ce matin, pas de sauvegarde : elle était chez le dentiste, et personne d'autre ne connaissait la commande.
> Camille : « Kubernetes redémarre mes pods tout seul. Il peut bien lancer une sauvegarde tout seul aussi. »

## Objectifs

- Voir les contrôleurs au travail : Deployment, ReplicaSet, DaemonSet, StatefulSet.
- Programmer une tâche avec un CronJob, lancer un Job à la demande, lire ses logs.
- Vérifier qu'une sauvegarde se restaure.
- Comprendre ce qu'est un opérateur, à partir de celui qui gère déjà votre réseau.

## Point de départ

```bash
cd ~/festipass && git fetch
git stash -u
git checkout tp-07-controleurs
kubectl apply -R -f k8s/
```

## Étapes

### 1. Les contrôleurs au travail

Chaque objet est surveillé par un contrôleur, qui le rapproche de l'état voulu. Suivez la chaîne des propriétaires d'un pod du back :

```bash
kubectl get deployment,replicaset,pods -l app=back
POD=$(kubectl get pod -l app=back -o jsonpath='{.items[0].metadata.name}')
kubectl get pod $POD -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}'; echo
RS=$(kubectl get pod $POD -o jsonpath='{.metadata.ownerReferences[0].name}')
kubectl get rs $RS -o jsonpath='{.metadata.ownerReferences[0].kind}/{.metadata.ownerReferences[0].name}'; echo
```

Les **DaemonSets** placent un pod par nœud :

```bash
kubectl get daemonsets -A
kubectl -n kube-system get pods -l k8s-app=kube-proxy -o wide
kubectl -n kube-system delete pod <un pod kube-proxy>
kubectl -n kube-system get pods -l k8s-app=kube-proxy -o wide
```

**Question 1 :** qui a recréé le pod kube-proxy, et sur quel nœud ? Pourquoi un DaemonSet n'a-t-il pas de champ `replicas` ?

### 2. Le CronJob de sauvegarde

Complétez les `TODO` de `tp/07-controleurs/sauvegarde.yaml` (`kubectl explain cronjob.spec`), puis :

```bash
cp tp/07-controleurs/sauvegarde.yaml k8s/40-sauvegarde.yaml
kubectl apply -f k8s/40-sauvegarde.yaml
kubectl get cronjob,pvc -l app=sauvegarde
```

**Question 2 :** que signifie `0 3 * * *` ? Pourquoi `concurrencyPolicy: Forbid` pour une sauvegarde ?

### 3. Ne pas attendre 3h du matin

Lancez un Job tout de suite, à partir du modèle du CronJob :

```bash
kubectl create job --from=cronjob/sauvegarde sauvegarde-manuelle
kubectl get jobs,pods -l app=sauvegarde -w        # Ctrl+C quand le Job est Complete
kubectl logs job/sauvegarde-manuelle
```

Achetez un pass, puis relancez une seconde sauvegarde (`sauvegarde-manuelle-2`).

**Question 3 :** un Job terminé a-t-il encore un pod ? Dans quel état ? Pourquoi le garder ?

### 4. Une sauvegarde qui échoue (si vous avez le temps)

Simulons un mot de passe erroné : créez un Job à partir du CronJob, mais en changeant le mot de passe :

```bash
kubectl create job --from=cronjob/sauvegarde sauvegarde-ratee --dry-run=client -o yaml \
  | sed 's/key: POSTGRES_PASSWORD/key: POSTGRES_USER/' | kubectl apply -f -
kubectl get pods -l job-name=sauvegarde-ratee -w   # Ctrl+C après quelques essais
kubectl describe job sauvegarde-ratee | tail -5
kubectl logs -l job-name=sauvegarde-ratee --tail=3
```

**Question 4 :** combien d'essais ? Que vaut le statut du Job à la fin ? Comment seriez-vous prévenu en production ?

Supprimez ce Job : `kubectl delete job sauvegarde-ratee`.

### 5. Tester la restauration

Lisez `tp/07-controleurs/restauration-job.yaml`, puis :

```bash
kubectl apply -f tp/07-controleurs/restauration-job.yaml
kubectl wait --for=condition=complete job/test-restauration --timeout=120s
kubectl logs job/test-restauration
```

**Question 5 :** le nombre de billets restaurés correspond-il au site ? Pourquoi est-il indispensable de tester une restauration régulièrement ?

### 6. Les opérateurs : Calico se gère tout seul

Depuis le TP 01, votre réseau est installé par un **opérateur** : `tigera-operator`. Il a ajouté ses propres types d'objets à l'API.

```bash
kubectl get crd | grep -E 'tigera|projectcalico' | head
kubectl get crd | wc -l
kubectl get installation default -o yaml | sed -n '/^spec:/,/^status:/p'
kubectl get tigerastatus
```

Mettez l'opérateur à l'épreuve : arrêtez un composant de Calico qu'il gère.

```bash
kubectl -n calico-system get deployment calico-kube-controllers
kubectl -n calico-system scale deployment calico-kube-controllers --replicas=0
kubectl -n calico-system get deployment calico-kube-controllers -w      # Ctrl+C après 30 s
kubectl -n tigera-operator logs deploy/tigera-operator --tail=20 | grep -i kube-controllers
```

**Questions :**

6. Que s'est-il passé ? Qui a corrigé, et pourquoi ?
7. Quel objet décrit l'état voulu du réseau ? Qu'est-ce qu'une CRD ? Qu'est-ce qu'un opérateur ajoute à une CRD ?

## Questions de fin

8. Deployment, StatefulSet, DaemonSet, Job, CronJob : lequel pour un agent de collecte de logs ? Une migration de schéma de base ? Le front ? Un calcul de statistiques chaque nuit ? PostgreSQL ?
9. La sauvegarde est sur un volume du même nœud que la base. Est-ce une vraie sauvegarde ?

## Bonus

- Passez le `schedule` à `*/2 * * * *` et observez les Jobs pendant 10 minutes : combien en garde-t-on ? Remettez `0 3 * * *`.
- Ajoutez `timeZone: Europe/Paris` au CronJob : sans ce champ, dans quel fuseau horaire est interprété `0 3 * * *` ?
- Installez l'opérateur **CloudNativePG** et créez une base PostgreSQL répliquée à 2 instances dans un namespace `essai-cnpg` (documentation : cloudnative-pg.io, section *Installation* et *Quickstart*). Comparez avec notre StatefulSet.
