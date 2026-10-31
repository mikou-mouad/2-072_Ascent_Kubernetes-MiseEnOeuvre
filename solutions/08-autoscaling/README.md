# Correction du TP 08 – Autoscaling

Fichiers corrigés :

- `k8s/50-hpa.yaml` : l'HPA du back (2 à 10 pods, 60 % du CPU demandé, descente après 60 s) ;
- `k8s/20-back.yaml` : sans `replicas`.

Pour comparer : `diff -r solutions/08-autoscaling/k8s k8s`.

1. **Sans requests :** l'utilisation est un pourcentage des requests. Sans requests CPU, l'HPA ne peut rien calculer : `kubectl get hpa` affiche `<unknown>/60%` et l'événement `FailedGetResourceMetric: missing request for cpu`. Il ne fait rien.
2. **`replicas` retiré :** sinon chaque `kubectl apply -f k8s/` remettrait 2 réplicas, en plein rush, et l'HPA remonterait ensuite : des pods supprimés puis recréés pour rien. Attention : au premier `apply` sans `replicas`, kubectl retire le champ, le Deployment repasse brièvement à 1 réplica (la valeur par défaut) avant que l'HPA ne remonte à 2.
3. **Calcul :** avec 2 réplicas à 240 % pour une cible de 60 % : 2 × 240 / 60 = 8 réplicas voulus. Avec 8 réplicas à 75 % : 8 × 75 / 60 = 10. L'HPA ignore les écarts de moins de 10 % (tolérance) pour éviter de varier en permanence.
4. **Paliers :** l'HPA recalcule toutes les 15 secondes, à partir de mesures de metrics-server qui datent de 15 à 60 secondes ; les nouveaux pods mettent du temps à démarrer et à être prêts, et ne sont comptés qu'une fois prêts. La charge se répartit, l'utilisation baisse, l'HPA recalcule. La politique par défaut limite aussi la montée (doubler, ou +4 pods, par 15 s).
5. **Pending :** `0/3 nodes are available: 1 node(s) had untolerated taint {node-role.kubernetes.io/control-plane: }, 2 Insufficient cpu`. Les nœuds ne sont pas forcément à 100 % de CPU réel : le scheduler raisonne sur les **requests** déjà réservées (`Allocated resources`), pas sur la consommation.
6. **Descente :** environ une minute après la fin de la charge (la fenêtre de stabilisation de 60 s), plus le délai de mesure. L'HPA prend la plus haute recommandation de la fenêtre : il évite de supprimer des pods pendant un creux de quelques secondes et de devoir les recréer aussitôt (le « yo-yo »). Par défaut, la fenêtre est de 5 minutes.
7. **Les trois autoscalers :** l'**HPA** ajoute ou retire des pods ; le **VPA** ajuste les requests et limits des pods (en les recréant) ; le **Cluster Autoscaler** (ou Karpenter) ajoute des nœuds quand des pods sont `Pending` faute de place, et en retire quand ils sont sous-utilisés. Les deux vont ensemble : l'HPA crée des pods, mais si les nœuds sont pleins, ils restent `Pending` sans le Cluster Autoscaler.
8. **Front et PostgreSQL :** le front (nginx) consomme peu, mais pourrait en avoir un si le trafic l'exige. PostgreSQL n'est pas sans état : ajouter des réplicas crée des bases indépendantes (TP 06), pas de la capacité. On le dimensionne verticalement (plus de CPU et de mémoire), ou avec des réplicas en lecture gérés par un opérateur.
9. **Ne pas compter que sur l'HPA :** il réagit avec une à deux minutes de retard, plus le temps de démarrage des pods (et des nœuds avec un Cluster Autoscaler : plusieurs minutes). Pour un pic prévu à la minute près, on anticipe : à 9h45, on monte `minReplicas` (par exemple à 8) et on s'assure que les nœuds sont là, puis on redescend après le pic. L'HPA gère ensuite l'imprévu.

## Bonus

- **Deux métriques :** l'HPA calcule un nombre de réplicas pour chaque métrique et garde **le plus grand**.
- **`kubectl scale` pendant la charge :** le Deployment repasse à 2, puis l'HPA le remonte au calcul suivant. Avec un HPA, le nombre de réplicas ne se pilote plus à la main (on change `minReplicas`).
- **scaleUp.policies :**

```yaml
  behavior:
    scaleUp:
      policies:
        - type: Pods
          value: 2
          periodSeconds: 30
```
