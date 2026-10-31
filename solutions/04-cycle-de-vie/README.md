# Correction du TP 04 – Cycle de vie et surveillance

Le fichier corrigé est `k8s/30-front.yaml` (stratégie, image 1.1, `change-cause`).
Pour comparer : `diff -r solutions/04-cycle-de-vie/k8s k8s`.

1. **Pourquoi un pod ne démarre pas :** `kubectl describe pod` (section `Events` en bas) et `kubectl get events`. Ce que fait l'application : `kubectl logs`. Règle simple : si le conteneur n'a jamais démarré, les logs sont vides, il faut regarder les événements.
2. **Pendant la mise à jour :** uniquement des `200`. Le nouveau pod démarre, devient prêt (readinessProbe), reçoit du trafic, et seulement ensuite un ancien pod est arrêté. Au TP 00, Compose arrêtait l'ancien conteneur avant de démarrer le nouveau.
3. **ReplicaSets :** deux. Le Deployment crée un ReplicaSet par version du template. L'ancien est gardé à 0 réplica : c'est lui qui permet le `rollout undo` instantané (10 versions gardées par défaut, `revisionHistoryLimit`).
4. **La 1.2 :** le nouveau pod est en `ErrImagePull` puis `ImagePullBackOff`. `describe` indique `ghcr.io/mikou-mouad/festipass-front:1.2: not found`. Le site n'est pas coupé : avec `maxUnavailable: 0`, Kubernetes ne supprime aucun ancien pod tant que le nouveau n'est pas prêt. Le rollout reste bloqué, puis passe en `ProgressDeadlineExceeded` au bout de 10 minutes (`progressDeadlineSeconds`).
5. **`maxUnavailable: 100%` :** tous les anciens pods auraient pu être arrêtés tout de suite : site coupé jusqu'au rollback.
6. **Fichier et cluster :** ici, le fichier dit 1.1 et le cluster tourne en 1.1, par chance. En général, une modification impérative (`set image`, `edit`, `scale`) crée un écart entre Git et le cluster : le prochain `apply` l'écrasera, ou pire, la remettra en place des semaines plus tard. En dehors d'une urgence, on modifie le fichier et on fait `apply`.
7. **La panne mystère :** la ConfigMap `back-config` contient `DB_HOST: postgresql` au lieu de `postgres`. Pistes : `kubectl rollout status` bloqué ; `kubectl get pods` montre un nouveau pod du back `0/1` ; `kubectl describe pod` indique `Readiness probe failed: HTTP probe failed with statuscode: 503` ; `kubectl logs` affiche `base_indisponible` avec `failed to resolve host 'postgresql'` ; `kubectl exec <nouveau pod> -- env | grep DB_HOST` confirme. Correction :

   ```bash
   kubectl apply -f k8s/02-configmap.yaml          # remet DB_HOST=postgres
   kubectl rollout restart deployment back         # les variables ne sont lues qu'au démarrage
   kubectl rollout status deployment back
   ```

8. **Site disponible :** la **readinessProbe** (`/readyz` teste la base) a gardé le nouveau pod hors du Service, et la stratégie par défaut (`maxUnavailable: 25%` de 2 réplicas, arrondi à 0) a gardé les anciens pods. La livenessProbe (`/healthz`) ne dépend pas de la base : le pod n'a pas été redémarré en boucle, ce qui aurait masqué la cause.
9. **Modification hors dépôt :** `kubectl patch` change le cluster mais pas Git. Personne ne voit la modification en relisant le dépôt, et le prochain `kubectl apply -f k8s/` la corrige « par hasard ». C'est ce qui a permis de réparer avec `apply` : le dépôt était la source de vérité.

## Bonus

- **`kubectl diff` :** affiche le diff entre le fichier et l'objet du cluster, sans rien appliquer (rien si tout est à jour).
- **pause / resume :** un seul rollout, avec les deux changements. Utile pour grouper plusieurs modifications impératives.
- **`kubectl debug` :** ajoute un conteneur éphémère dans le pod, qui partage l'espace des processus du conteneur `back` (`--target`). Utile quand l'image n'a pas de shell.
- **startupProbe :** pour une application lente à démarrer. Tant qu'elle n'a pas réussi, la liveness n'est pas évaluée : on évite qu'un démarrage long soit pris pour un blocage et redémarré en boucle.
