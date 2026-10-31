# Correction du TP 05 – Bonnes pratiques

Les fichiers corrigés sont dans `k8s/`, aux mêmes chemins que dans le dépôt :

- `10-postgres.yaml`, `20-back.yaml`, `30-front.yaml` : labels recommandés, annotations, `resources` ;
- `capacite/limitrange.yaml` et `capacite/quota.yaml` : les règles de la recette.

Pour comparer : `diff -r solutions/05-bonnes-pratiques/k8s k8s`.

1. **Label ou annotation :** seuls les **labels** servent aux sélecteurs (Services, Deployments, `kubectl -l`, NetworkPolicies…). Ils sont courts et contraints (63 caractères, pas d'espace). Les **annotations** portent de l'information pour les humains et les outils, sans limite de format : contact, lien vers le ticket, description, `change-cause`.
2. **Sélecteur immuable :** `spec.selector: Invalid value: … field is immutable`. Changer le sélecteur ferait perdre au Deployment ses ReplicaSets et ses pods existants (ils ne correspondraient plus) : il en créerait de nouveaux et laisserait les anciens orphelins. Pour changer de sélecteur, on recrée le Deployment.
3. **Quarantaine :** 3 pods du back tournent : le ReplicaSet ne reconnaît plus le pod relabellisé (`app=quarantaine`) et en crée un nouveau pour revenir à 2. Le Service ne le sélectionne plus non plus : il ne reçoit plus de trafic. Plus personne ne le surveille : il ne sera jamais remplacé ni supprimé automatiquement. Pratique pour analyser un problème sur un pod réel.
4. **Allocated resources :** les requests du nœud restent faibles : le pod `stats` ne déclare **aucune** request. Le scheduler raisonne sur les requests, pas sur la consommation réelle : il continue de placer des pods sur ce nœud comme s'il était vide.
5. **OOMKilled :** la LimitRange a injecté `requests: 100m / 128Mi` et `limits: 500m / 256Mi` dans le conteneur, à la création du pod (contrôleur d'admission). Le programme réserve 1200 Mo : il dépasse 256 Mi, le noyau le tue (`Last State: Terminated, Reason: OOMKilled`, code 137), le kubelet le redémarre, il est tué à nouveau : `CrashLoopBackOff`. La recette ne peut plus déborder sur la prod.
6. **Quota :** 8 pods seulement. Chaque pod reçoit de la LimitRange 128Mi de requests et 256Mi de limits mémoire : au 8e, `requests.memory` (8 × 128Mi = 1Gi) et `limits.memory` (8 × 256Mi = 2Gi) sont atteints, avant le quota de 10 pods. Les suivants sont refusés à la création : `exceeded quota: budget, requested: limits.memory=256Mi,requests.memory=128Mi, used: …, limited: …`. L'erreur apparaît dans les événements du ReplicaSet, pas sur des pods (ils n'existent pas).
7. **QoS :** postgres est **Guaranteed** (requests = limits pour CPU et mémoire), back et front sont **Burstable** (requests < limits). Un pod sans aucune request ni limit serait **BestEffort**. Sous pression mémoire, le kubelet expulse d'abord les BestEffort, puis les Burstable qui dépassent le plus leurs requests, et les Guaranteed en dernier.
8. **Dépassement :** CPU : le conteneur est **ralenti** (throttling), jamais tué. Mémoire : il est **tué** (OOMKilled) et redémarré.
9. **Limites hautes partout :** les limits ne réservent rien. Si tous les conteneurs utilisent leur limite en même temps, le nœud manque de mémoire et le kubelet expulse des pods. Une limite doit être proche du besoin réel mesuré (`kubectl top`), avec une marge.
10. **Séparer la recette :** des nœuds dédiés, avec un **taint** sur les nœuds de prod (`environnement=production:NoSchedule`) que seuls les pods de prod tolèrent, et un `nodeSelector` ou une `nodeAffinity` vers les nœuds de recette. Ou, plus simple et plus sûr : un cluster de recette séparé.

## Bonus

- **Quota sur la prod :** il protège contre une erreur de configuration (un `replicas: 200`), mais il faut qu'il laisse la place au pic du vendredi : un quota trop juste bloquerait l'HPA du TP 08 au pire moment.
- **Quota d'objets :** `count/deployments.apps: "5"` refuse le 6e Deployment ; `services.nodeports: "0"` interdit d'exposer la recette en NodePort.
- **BestEffort du système :** sur un cluster kubeadm, plusieurs composants (`kube-proxy`, certains pods Calico) n'ont pas de requests : ils sont BestEffort, mais protégés autrement (pods critiques, `priorityClassName: system-node-critical`).
