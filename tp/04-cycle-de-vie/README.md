# TP 04 – « La version 1.2 est cassée, et personne ne sait pourquoi »

**Durée :** 1 h 25 (metrics-server avant la pause, le reste après) · **Branche :** `tp-04-cycle-de-vie` · **Correction :** `solutions/04-cycle-de-vie/`, dans cette branche

## L'incident

> Mardi, 14h00. Yanis livre la nouvelle charte graphique du front (version 1.1). Puis, pressé, il enchaîne avec une « 1.2 »… et plus rien ne démarre.
> Une heure plus tard, nouvelle livraison, cette fois sur le back : les nouveaux pods ne sont jamais prêts.
> Camille : « Avant de toucher à quoi que ce soit, on regarde ce que dit le cluster. »

## Objectifs

- Surveiller les ressources avec kubectl : `get -w`, `describe`, `logs`, `events`, `top`, `exec`, `port-forward`.
- Mettre à jour une application sans coupure, suivre et annoter un rollout, revenir en arrière.
- Diagnostiquer les pannes les plus courantes : image introuvable, pod jamais prêt.

## Point de départ

```bash
cd ~/festipass && git fetch
git stash -u
git checkout tp-04-cycle-de-vie
kubectl apply -f k8s/
```

## Étapes

### 1. metrics-server : voir la consommation

`kubectl top` a besoin de metrics-server, qui collecte le CPU et la mémoire auprès des kubelets.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/download/v0.7.2/components.yaml
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
kubectl -n kube-system rollout status deployment metrics-server
```

Attendez une minute, puis :

```bash
kubectl top nodes
kubectl top pods
```

> `--kubelet-insecure-tls` : sur un cluster kubeadm, les certificats des kubelets ne sont pas signés par la CA du cluster. On l'accepte en formation, pas en production.

### 2. La boîte à outils de surveillance

Prenez 10 minutes pour essayer chaque commande et noter ce qu'elle apporte :

```bash
kubectl get pods -o wide                         # où, quelle IP, combien de redémarrages
kubectl get pods -w                              # en continu (Ctrl+C)
kubectl describe pod -l app=back | less          # détail + événements en bas
kubectl get events --sort-by=.lastTimestamp      # ce qui s'est passé dans le namespace
kubectl logs -l app=back --prefix --tail=3       # les logs de tous les pods du back
kubectl logs -f deploy/back                      # en continu, achetez un pass sur le site (Ctrl+C)
kubectl exec deploy/back -- env | grep FESTIVAL  # une commande dans un conteneur
kubectl port-forward svc/back 9090:8080 &        # un tunnel vers le Service
curl -s localhost:9090/api/stats; echo
kill %1
```

**Question 1 :** quelle commande utiliser pour savoir **pourquoi** un pod ne démarre pas ? Et pour savoir ce que fait l'application ?

### 3. Mise à jour sans coupure : le front 1.1

Lancez une **sonde** en arrière-plan (`&` à la fin) : elle interroge le site toutes les 0,2 s et note chaque code HTTP, un par ligne, dans un fichier.

```bash
while true; do curl -s -m 2 -o /dev/null -w "%{http_code}\n" http://10.10.0.30:30080/; sleep 0.2; done > /tmp/sonde.log &
```

Dans `k8s/30-front.yaml` :

1. ajoutez une stratégie de mise à jour prudente dans `spec` :

   ```yaml
     strategy:
       type: RollingUpdate
       rollingUpdate:
         maxSurge: 1          # 1 pod de plus que prévu pendant la mise à jour
         maxUnavailable: 0    # jamais moins de pods prêts que prévu
   ```

2. passez l'image en `festipass-front:1.1` ;
3. ajoutez la raison du changement dans les `annotations` du Deployment (dans `metadata`, pas dans le template) : `kubernetes.io/change-cause: "front 1.1 : nouvelle charte corail"`.

```bash
kubectl apply -f k8s/30-front.yaml
kubectl rollout status deployment front
kubectl rollout history deployment front
kubectl get replicasets -l app=front
sort /tmp/sonde.log | uniq -c               # combien de réponses, par code HTTP
kill %1                                     # arrête la sonde
```

Rechargez le site depuis ClientWeb (ou l'adresse du tunnel, TP 02) : le bandeau est passé au corail.

**Questions :**

2. La sonde a-t-elle noté autre chose que `200` ? Comparez avec la mise à jour du TP 00.
3. Combien de ReplicaSets existe-t-il pour le front ? À quoi sert l'ancien ?

### 4. La 1.2 : une image qui n'existe pas

Yanis livre en urgence, en ligne de commande :

```bash
kubectl set image deployment/front front=ghcr.io/mikou-mouad/festipass-front:1.2
kubectl annotate deployment/front kubernetes.io/change-cause="front 1.2 : urgence" --overwrite
kubectl rollout status deployment front --timeout=60s
```

Le rollout n'aboutit pas. **Diagnostiquez** avec les outils de l'étape 2 : état des pods, raison exacte, événements.

**Questions :**

4. Quel est l'état du nouveau pod et quelle est la cause exacte ? Le site est-il coupé ? Pourquoi ?
5. Qu'aurait changé `maxUnavailable: 100%` ?

Revenez en arrière :

```bash
kubectl rollout undo deployment front
kubectl rollout status deployment front
kubectl rollout history deployment front
```

**Question 6 :** le cluster tourne en 1.1. Que dit le fichier `k8s/30-front.yaml` ? Pourquoi éviter `kubectl set image` en dehors des urgences ?

### 5. La panne mystère

Yanis livre une modification du back. Lancez sa livraison (sans lire le script) :

```bash
bash tp/04-cycle-de-vie/panne-mystere.sh
```

Le site fonctionne-t-il ? Le rollout du back aboutit-il (`kubectl rollout status deployment back --timeout=30s`) ?
Trouvez la cause **uniquement avec kubectl** : `get`, `describe`, `logs`, `events`, `exec`… Puis corrigez **à partir des fichiers du dépôt**, sans écrire de nouvelle valeur à la main.

**Questions :**

7. Quelle est la cause ? Quelles commandes vous ont mis sur la piste ?
8. Pourquoi le site est-il resté disponible pendant la panne ? Quelle probe a protégé les clients ?
9. Pourquoi la livraison de Yanis n'a-t-elle pas touché aux fichiers du dépôt, et pourquoi est-ce un problème ?

## Bonus

- `kubectl diff -f k8s/` : comparez les fichiers et l'état du cluster avant chaque `apply`.
- `kubectl rollout pause deployment front`, changez l'image **et** une variable, puis `kubectl rollout resume` : combien de rollouts ?
- Lancez un conteneur de débogage dans un pod du back : `kubectl debug -it <pod du back> --image=public.ecr.aws/docker/library/busybox:1.36 --target=back -- sh`, puis `ps` et `wget -qO- localhost:8080/api/version`.
- Ajoutez une `startupProbe` au back. Dans quel cas est-elle utile ?
