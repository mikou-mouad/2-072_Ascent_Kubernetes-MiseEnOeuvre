# Correction du TP 03 – ConfigMap et Secret

Les fichiers corrigés sont dans `k8s/`, aux mêmes chemins que dans le dépôt :

- `01-secret.yaml` : les Secrets `festipass-db` et `back-signature` (la clé de signature est un exemple : la vôtre est différente) ;
- `02-configmap.yaml` : `back-config`, avec `PASS_MAX: "6"` ;
- `03-front-annonce.yaml` : l'annonce du festival ;
- `10-postgres.yaml`, `20-back.yaml`, `30-front.yaml` : les manifests qui les utilisent.

Pour comparer : `diff -r solutions/03-configuration/k8s k8s`.

1. **Chiffrement :** non. Les valeurs sont seulement **encodées** en base64, ce qui n'est pas un chiffrement. Toute personne autorisée à lire les Secrets du namespace (et tout administrateur du cluster) lit le mot de passe. Dans etcd, ils sont stockés en clair, sauf si on active le chiffrement au repos (`EncryptionConfiguration`). Le fichier `01-secret.yaml` contient donc le mot de passe : le mettre dans Git, c'est refaire l'incident. On contrôle qui lit les Secrets avec RBAC (TP 09), et on les gère hors de Git avec Sealed Secrets, SOPS ou External Secrets Operator.
2. **Billets disparus :** le template du Deployment PostgreSQL a changé, donc un nouveau pod a été créé. Ses données vivaient dans le conteneur : le nouveau pod repart d'une base vide (initialisée avec le nouveau mot de passe). C'est l'incident du chapitre 6.
3. **PASS_MAX :** non. Les variables d'environnement sont lues **au démarrage du conteneur**. Modifier la ConfigMap ne change pas les processus qui tournent : il faut recréer les pods (`rollout restart`), ce qui se fait sans coupure grâce au rolling update.
4. **Fichier monté :** environ une minute (synchronisation périodique du kubelet, plus le cache). Rien n'a redémarré : le kubelet met à jour les fichiers d'un volume ConfigMap ou Secret dans les pods qui tournent. Le front relit le fichier à chaque requête, donc le site change tout seul. Exception : un montage avec `subPath` n'est jamais mis à jour.
5. **Env ou fichier :** les deux fonctionnent. Les fichiers sont un peu plus sûrs pour un mot de passe (les variables d'environnement se retrouvent facilement dans les logs, `/proc`, les rapports d'erreur) et se mettent à jour sans redémarrage. Un fichier de configuration complet (nginx, application) se monte toujours comme un fichier.
6. **ConfigMap absente :** le pod reste en `CreateContainerConfigError` (événement `configmap "nexiste-pas" not found`). Il démarre dès que la ConfigMap est créée. Avec `optional: true`, il démarrerait sans.
7. **Tableau du TP 00 :** « le mot de passe est en clair dans un fichier » est réglé pour les manifests. Il reste à contrôler **qui** peut lire les Secrets (TP 09).

## Bonus

- **immutable :** toute modification de `data` est refusée (`field is immutable`) ; il faut supprimer et recréer la ConfigMap, ou en créer une nouvelle (`back-config-v2`) et modifier le Deployment, ce qui déclenche un rolling update. Intérêt : pas de changement de configuration accidentel, et moins de charge sur l'API server (le kubelet ne surveille plus ces objets).
- **--from-env-file :** chaque ligne `CLE=valeur` du fichier devient une entrée de la ConfigMap.
- **Secrets hors de Git :** Sealed Secrets chiffre le Secret avec une clé du cluster (seul le cluster le déchiffre, le fichier chiffré peut aller dans Git) ; SOPS chiffre les valeurs dans le fichier avec une clé KMS, GPG ou age ; External Secrets Operator crée les Secrets à partir d'un coffre externe (Vault, AWS Secrets Manager, Azure Key Vault…).
