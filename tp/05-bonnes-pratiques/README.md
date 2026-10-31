# TP 05 – « Le test de la recette a fait tomber la prod »

**Durée :** 55 min (partie 1 avant la pause, partie 2 après) · **Branche :** `tp-05-bonnes-pratiques` · **Correction :** `solutions/05-bonnes-pratiques/`, dans cette branche

## L'incident

> Mardi, 16h20. Yanis teste le recalcul des statistiques de vente dans un namespace de recette. Le pod charge toutes les ventes en mémoire et calcule… sur les mêmes nœuds que la production.
> Le worker sature, la billetterie rame. Camille cherche à qui appartient ce pod : aucun label, aucune annotation, aucune limite.
> Léa : « Vendredi, la recette ne doit pas pouvoir toucher à la prod. »

## Objectifs

- Organiser les objets avec des labels et des annotations, les retrouver avec des sélecteurs.
- Comprendre requests et limits, et ce qu'en fait le scheduler et le nœud.
- Encadrer un namespace avec une LimitRange et un ResourceQuota.
- Réserver les ressources de la production.

## Point de départ

```bash
cd ~/festipass && git fetch
git stash -u
git checkout tp-05-bonnes-pratiques
kubectl apply -f k8s/
```

## Partie 1 – Labels, annotations, sélecteurs (25 min)

### 1. Interroger par labels

```bash
kubectl get pods --show-labels
kubectl get pods -L app
kubectl get pods -l app=back
kubectl get pods -l 'app in (back,front)'
kubectl get pods -l 'app!=postgres'
kubectl get all -l app=front
```

### 2. Les labels recommandés

Kubernetes recommande un jeu de labels communs (`app.kubernetes.io/*`). Dans `k8s/10-postgres.yaml`, `k8s/20-back.yaml` et `k8s/30-front.yaml`, ajoutez ces labels **dans `metadata.labels` du Deployment et dans `template.metadata.labels`** (gardez `app`) :

| Label | postgres | back | front |
|-------|----------|------|-------|
| `app.kubernetes.io/name` | `festipass` | `festipass` | `festipass` |
| `app.kubernetes.io/component` | `base-de-donnees` | `back` | `front` |
| `app.kubernetes.io/part-of` | `festival-des-embruns` | idem | idem |
| `app.kubernetes.io/version` | – | `"1.0"` | `"1.1"` |
| `environnement` | `production` | idem | idem |

Et ces **annotations** dans `metadata.annotations` des Deployments : `festipass.fr/equipe` (`exploitation` pour postgres, `developpement` pour back et front) et `festipass.fr/contact` (`camille@festipass.example` ou `yanis@festipass.example`).

```bash
kubectl apply -f k8s/
kubectl get pods -L app.kubernetes.io/component,app.kubernetes.io/version
kubectl get deploy -l app.kubernetes.io/part-of=festival-des-embruns
kubectl describe deploy back | grep -A3 Annotations
```

**Question 1 :** label ou annotation : lequel peut servir à sélectionner des objets ? Où mettre l'adresse de contact ? Le lien vers le ticket de la mise en production ?

### 3. Le sélecteur d'un Deployment est immuable

Ajoutez `environnement: production` dans `spec.selector.matchLabels` du back, puis `kubectl apply -f k8s/20-back.yaml`.

**Question 2 :** que répond l'API ? Pourquoi cette règle ?

Annulez cette modification du sélecteur.

### 4. Mettre un pod en quarantaine

Un pod du back se comporte bizarrement. Camille veut le garder pour l'analyser, mais le sortir du trafic.

```bash
kubectl get pods -l app=back
kubectl label pod <un pod du back> app=quarantaine --overwrite
kubectl get pods -L app
kubectl get endpointslices -l kubernetes.io/service-name=back -o wide
```

**Question 3 :** combien de pods du back tournent maintenant ? Le pod en quarantaine reçoit-il encore du trafic ? Qui le surveille ?

Supprimez le pod en quarantaine.

## Partie 2 – Requests, limits et quotas (30 min)

### 5. Reproduire l'incident

```bash
kubectl apply -f k8s/capacite/00-recette.yaml
kubectl apply -f tp/05-bonnes-pratiques/stats-gourmand.yaml
kubectl -n festipass-recette get pods -o wide -w        # Ctrl+C quand il tourne
```

Attendez une minute, puis :

```bash
kubectl top nodes
kubectl top pods -A --sort-by=memory | head -5
kubectl describe node <nœud du pod stats> | sed -n '/Allocated resources/,/Events/p'
```

**Question 4 :** le pod `stats` consomme un CPU entier et plus d'un gigaoctet. Que dit la section `Allocated resources` du nœud ? Que voit le scheduler au moment de placer le prochain pod ?

### 6. Encadrer la recette

Complétez les `TODO` de `k8s/capacite/limitrange.yaml` et `k8s/capacite/quota.yaml` (`kubectl explain resourcequota.spec.hard`), puis :

```bash
kubectl apply -f k8s/capacite/limitrange.yaml -f k8s/capacite/quota.yaml
kubectl -n festipass-recette describe limitrange,resourcequota
```

Le pod `stats` existant n'est pas touché : les règles s'appliquent à la création. Recréez-le :

```bash
kubectl -n festipass-recette delete pod -l app=stats       # le ReplicaSet le recrée
kubectl -n festipass-recette get pods -w                 # Ctrl+C après quelques redémarrages
kubectl -n festipass-recette describe pod -l app=stats | grep -E -A4 'Limits|Last State'
```

**Question 5 :** que s'est-il passé, et pourquoi ? D'où viennent les limites du conteneur, alors que le manifest n'en déclare pas ?

Yanis essaie de paralléliser son calcul :

```bash
kubectl -n festipass-recette scale deployment stats --replicas=15
kubectl -n festipass-recette get pods | grep -c stats
kubectl -n festipass-recette describe resourcequota budget
kubectl -n festipass-recette get events --sort-by=.lastTimestamp | grep -i quota | tail -3
```

**Question 6 :** combien de pods ont été créés ? Quelle ressource du quota a bloqué ?

Arrêtez l'expérience : `kubectl -n festipass-recette scale deployment stats --replicas=0`.

### 7. Réserver les ressources de la production

Ajoutez des `resources` aux conteneurs de la production :

| Conteneur | requests CPU | requests mémoire | limits CPU | limits mémoire |
|-----------|--------------|------------------|------------|----------------|
| postgres  | `500m` | `512Mi` | `500m` | `512Mi` |
| back      | `250m` | `128Mi` | `"1"`  | `256Mi` |
| front     | `50m`  | `64Mi`  | `200m` | `128Mi` |

```bash
kubectl apply -f k8s/
kubectl get pods -o custom-columns=NOM:.metadata.name,QOS:.status.qosClass
kubectl describe node worker1 | sed -n '/Allocated resources/,/Events/p'
```

**Question 7 :** quelle classe QoS a chaque pod ? En cas de manque de mémoire sur un nœud, dans quel ordre le kubelet expulse-t-il les pods ?

## Questions de fin

8. Un conteneur dépasse sa limite CPU : que se passe-t-il ? Et sa limite mémoire ?
9. Pourquoi ne pas mettre la même limite mémoire très haute partout « pour être tranquille » ?
10. Que faudrait-il pour que la recette ne tourne même pas sur les mêmes nœuds que la prod ?

## Bonus

- Mettez aussi un ResourceQuota sur le namespace `festipass`. Quel risque si son budget est trop juste le jour de l'ouverture ?
- Ajoutez un quota d'objets à la recette (`count/deployments.apps: "5"`, `services.nodeports: "0"`) et testez-le.
- `kubectl get pods -A -o custom-columns=NS:.metadata.namespace,NOM:.metadata.name,QOS:.status.qosClass | grep BestEffort` : quels pods du système n'ont aucune request ?
