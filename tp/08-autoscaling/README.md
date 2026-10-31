# TP 08 – « Vendredi 10h00 : l'ouverture de la billetterie »

**Durée :** 50 min · **Branche :** `tp-08-autoscaling` · **Correction :** `solutions/08-autoscaling/`, dans cette branche

## L'incident

> Vendredi, 9h55. La tête d'affiche sera annoncée à 10h00, la billetterie ouvre dans la foulée.
> L'an dernier, il aurait fallu 8 back… pendant 15 minutes, puis 2 le reste de l'année.
> Camille : « Je ne vais pas faire `kubectl scale` à la main toutes les 30 secondes. Le cluster va s'adapter tout seul. »

## Objectifs

- Mettre en place un HorizontalPodAutoscaler (HPA) sur le CPU, et comprendre son calcul.
- Observer la montée et la descente en charge.
- Voir ce qui se passe quand les nœuds sont pleins, et ce que ferait un Cluster Autoscaler.

## Point de départ

```bash
cd ~/festipass && git fetch
git stash -u
git checkout tp-08-autoscaling
kubectl apply -R -f k8s/
```

## Étapes

### 1. Les prérequis

```bash
kubectl top pods                                              # metrics-server (TP 04)
kubectl get deploy back -o jsonpath='{.spec.template.spec.containers[0].resources}'; echo   # requests (TP 05)
```

**Question 1 :** l'HPA compare la consommation CPU aux **requests**. Que se passerait-il sans requests CPU sur le back ?

### 2. L'HPA du back

Faites générer le manifest par kubectl :

```bash
kubectl autoscale deployment back --cpu-percent=60 --min=2 --max=10 \
  --dry-run=client -o yaml > k8s/50-hpa.yaml
```

Complétez-le :

- ajoutez `namespace: festipass` ;
- l'HPA attend 5 minutes avant de réduire le nombre de pods : pour le TP, raccourcissez ce délai à 60 secondes avec `spec.behavior.scaleDown.stabilizationWindowSeconds` (`kubectl explain hpa.spec.behavior.scaleDown`).

Dans `k8s/20-back.yaml`, **supprimez la ligne `replicas: 2`** : c'est désormais l'HPA qui décide.

```bash
kubectl apply -f k8s/20-back.yaml -f k8s/50-hpa.yaml
kubectl get hpa back
kubectl describe hpa back | tail -8
```

**Question 2 :** pourquoi retirer `replicas` du manifest du Deployment ? Que se passerait-il à chaque `kubectl apply` sinon ?

### 3. 10h00 : l'ouverture

Lisez `tp/08-autoscaling/ouverture-billetterie.yaml`, puis lâchez les festivaliers et suivez tout sur un seul écran, rafraîchi toutes les 5 secondes : l'HPA, la consommation et la place de chaque pod du back.

```bash
kubectl apply -f tp/08-autoscaling/ouverture-billetterie.yaml
watch -n 5 'kubectl get hpa back; echo; kubectl top pods -l app=back; echo; kubectl get pods -l app=back -o wide'
```

Observez pendant 3 à 4 minutes, puis quittez `watch` avec Ctrl+C. Gardez aussi le site ouvert sur ClientWeb (ou l'adresse du tunnel, TP 02) : le bandeau change de pod à chaque rafraîchissement.

**Questions :**

3. Relevez une ligne de `kubectl get hpa` (par exemple `cpu: 240%/60%`, 2 réplicas). Vérifiez le calcul de l'HPA : `réplicas voulus = arrondi supérieur (réplicas actuels × utilisation / cible)`.
4. Pourquoi l'HPA monte-t-il par paliers, et pas directement au bon nombre ?

### 4. La tête d'affiche est annoncée : les nœuds sont pleins

```bash
kubectl -n charge scale deployment festivaliers --replicas=10
kubectl get pods -l app=back -o wide -w                   # Ctrl+C après 2 minutes
```

Si des pods du back restent `Pending` :

```bash
kubectl describe pod <un pod Pending> | tail -5
kubectl describe nodes | grep -A8 'Allocated resources'
```

> **Aucun pod `Pending` ?** Vos workers ont plus de CPU que prévu. Calculez combien de pods du back (250m chacun) tiennent sur les deux workers (`Allocatable` moins les requests déjà allouées), passez `maxReplicas` au-dessus dans `k8s/50-hpa.yaml`, appliquez, et augmentez encore les festivaliers.

**Question 5 :** que dit l'événement du scheduler ? La consommation réelle des nœuds (`kubectl top nodes`) est-elle à 100 % ?

Sur un cloud, un **Cluster Autoscaler** verrait ces pods `Pending` et commanderait une VM de plus. Ici, Camille « ajoute un nœud » à la main : elle ouvre le control plane aux pods de l'application.

```bash
kubectl taint nodes controlplane node-role.kubernetes.io/control-plane:NoSchedule-
kubectl get pods -l app=back -o wide                      # les Pending démarrent sur controlplane
```

Remettez la protection tout de suite (les pods déjà placés restent, aucun nouveau n'arrivera) :

```bash
kubectl taint nodes controlplane node-role.kubernetes.io/control-plane:NoSchedule
```

### 5. 10h20 : retour au calme

```bash
kubectl delete -f tp/08-autoscaling/ouverture-billetterie.yaml
```

Suivez la descente pendant 2 à 3 minutes (Ctrl+C pour quitter) :

```bash
kubectl get hpa back -w
```

**Question 6 :** au bout de combien de temps le nombre de pods redescend-il ? Pourquoi l'HPA attend-il avant de réduire ?

Combien de pass ont été vendus ?

```bash
kubectl exec postgres-0 -- psql -U festipass -c 'select pass, count(*) from billets group by pass'
```

## Questions de fin

7. HPA, VPA, Cluster Autoscaler : lequel ajoute des pods, lequel ajuste les requests, lequel ajoute des nœuds ? Pourquoi a-t-on souvent besoin de l'HPA **et** du Cluster Autoscaler ?
8. Le front et PostgreSQL ont-ils besoin d'un HPA ? Pourquoi un HPA sur PostgreSQL ne servirait à rien ?
9. L'ouverture est à 10h00 précises. Pourquoi ne pas compter uniquement sur l'HPA, et que feriez-vous à 9h45 ?

## Bonus

- Ajoutez une seconde métrique à l'HPA : la mémoire, cible 80 %. Comment l'HPA combine-t-il deux métriques ?
- Pendant la charge, lancez `kubectl scale deployment back --replicas=2` : que fait l'HPA ?
- Ajoutez `behavior.scaleUp.policies` pour limiter la montée à 2 pods par 30 secondes, et comparez.
