# Correction du TP 06 – Stockage

Fichiers corrigés :

- `k8s/10-postgres.yaml` : PostgreSQL en StatefulSet, avec son Service headless ;
- `bonus-storageclass-retain.yaml` : la StorageClass du bonus.

Pour comparer : `diff solutions/06-stockage/k8s/10-postgres.yaml k8s/10-postgres.yaml`.

1. **Données :** dans la couche inscriptible du conteneur (le `VOLUME` de l'image n'est relié à aucun stockage dans Kubernetes). Elles vivent et meurent avec le conteneur. `drain` supprime le pod et en crée un nouveau ailleurs ; `delete pod` fait de même sur n'importe quel nœud : dans les deux cas, nouveau conteneur, base vide.
2. **PV :** créé par **local-path-provisioner**, à la demande du PVC (provisionnement dynamique). Avec `volumeBindingMode: WaitForFirstConsumer`, le volume n'est créé qu'au moment où un pod l'utilise : il est créé **sur le nœud choisi par le scheduler**. Sinon, le volume pourrait être créé sur un nœud et le pod placé sur un autre.
3. **PV après suppression du PVC :** supprimé, avec ses données : `reclaimPolicy: Delete`. Avec `Retain`, le PV resterait (`Released`), à récupérer à la main.
4. **Noms :** le pod s'appelle `postgres-0` (nom du StatefulSet + numéro d'ordre stable), le PVC `data-postgres-0` (nom du volumeClaimTemplate + nom du pod). Si le pod est recréé, il reprend le même nom et donc le même PVC.
5. **DNS headless :** `postgres` résout directement vers l'**IP du pod** (pas de ClusterIP). Chaque pod a aussi son propre nom : `postgres-0.postgres.festipass.svc.cluster.local`. C'est ce qui permet, dans un cluster de bases, de viser une instance précise (le primaire).
6. **Pending :** le PV local-path porte une `nodeAffinity` vers son nœud (`volume node affinity conflict`). Le pod ne peut tourner que là où sont ses données. Si le nœud est perdu, les données le sont aussi : local-path convient à un lab, pas à la production.
7. **Suppression du StatefulSet :** les PVC créés par `volumeClaimTemplates` sont conservés par défaut (`persistentVolumeClaimRetentionPolicy` : `Retain`). Il faut les supprimer explicitement pour perdre les données.
8. **StatefulSet :** identité stable (nom, DNS, PVC propre à chaque réplica), démarrage et arrêt dans l'ordre. Un Deployment avec un PVC `ReadWriteOnce` partagerait un seul volume entre tous ses réplicas (impossible sur plusieurs nœuds) et donnerait des noms aléatoires aux pods.
9. **Production :** un stockage réseau ou répliqué, accessible depuis tous les nœuds : disques cloud (EBS, Azure Disk, Persistent Disk) via leur pilote CSI, Ceph (Rook), Longhorn, une baie SAN… Ou une base managée hors du cluster. Pour la haute disponibilité de PostgreSQL lui-même : un opérateur (CloudNativePG, TP 07).

## Bonus

- **Retain :** après `kubectl delete pvc`, le PV passe `Released` et le dossier reste sur le nœud. Il faut supprimer le PV (et le dossier) à la main.
- **2 réplicas :** `postgres-1` a son propre PVC, vide : c'est une **seconde base indépendante**. Le Service headless envoie les connexions du back vers l'une ou l'autre : des billets sont écrits dans l'une, d'autres dans l'autre. La réplication est l'affaire de PostgreSQL (ou d'un opérateur), pas du StatefulSet. Retour à 1 réplica : `kubectl scale statefulset postgres --replicas=1` puis `kubectl delete pvc data-postgres-1`.
- **Dossier du volume :** `/opt/local-path-provisioner/pvc-<uid>_festipass_data-postgres-0/pgdata`.
