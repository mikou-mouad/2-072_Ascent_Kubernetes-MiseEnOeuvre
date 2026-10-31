# Correction du TP 00 – FestiPass avec Docker Compose

1. **Conteneurs :** trois (`postgres`, `back`, `front`). Seul le front est publié : le port `8000` de la VM est redirigé vers le port `8080` du conteneur nginx.
2. **Découverte de PostgreSQL :** Compose crée un réseau `app_default` et un DNS interne : chaque service est joignable par son nom. `DB_HOST=postgres` suffit. Kubernetes fera la même chose avec les **Services** (TP 02).
3. **Mot de passe :** en clair dans `docker-compose.yml`, donc dans Git. Toute personne qui lit le dépôt, ou qui fait `docker inspect` sur la VM, le lit. On le sort du code au TP 03 (Secret).
4. **Couches :** les instructions du Dockerfile produisent chacune une couche. Modifier `app.py` ne reconstruit que la couche `COPY app.py .` et les suivantes : la couche Python et la couche `pip install` sont réutilisées depuis le cache.
5. **Plantage :** le front (nginx) essaie de joindre l'adresse IP du back, qui n'existe plus : il attend jusqu'à son délai de connexion (60 s par défaut), puis répond `504` (délai dépassé) ou `502` (back injoignable). La sonde, limitée à 2 s, note `000` en attendant. Le conteneur ne redémarre pas : aucune politique de redémarrage n'est définie. Il faut qu'un humain s'en aperçoive et relance le conteneur : plusieurs minutes, en plein rush. Kubernetes surveille et redémarre les conteneurs tout seul (TP 02).
6. **Mise à jour :** Compose arrête l'ancien conteneur, puis démarre le nouveau. Entre les deux, plus rien ne répond. Il faudrait démarrer la nouvelle version, attendre qu'elle soit prête, puis arrêter l'ancienne : c'est le **rolling update** (TP 04).
7. **Scaling sur une seule VM :** on répartit la charge entre 3 processus, mais ils partagent le même CPU et la même mémoire. Si la VM sature, les 3 saturent. Si elle tombe, tout tombe. Il faut répartir sur **plusieurs machines** : un cluster (TP 01).
8. **Données :** l'image postgres déclare un `VOLUME`. Sans volume nommé, Compose crée un volume anonyme. `down` supprime le conteneur ; le nouveau conteneur reçoit un **nouveau** volume anonyme vide (l'ancien reste orphelin dans `docker volume ls`). Kubernetes sépare le cycle de vie des données de celui des pods avec les **PersistentVolumeClaims** (TP 06).

## Ce qu'on attend d'un orchestrateur

| Problème constaté | Ce qu'il faudrait | Dans Kubernetes | TP |
|-------------------|-------------------|-----------------|----|
| Le back planté reste planté | Surveiller et redémarrer automatiquement | Deployment, probes | 02, 04 |
| La mise à jour coupe le site | Remplacer progressivement, revenir en arrière | Rolling update, rollback | 04 |
| Une seule machine pour tout | Plusieurs machines, placement automatique, ajout de copies au rush | Cluster, scheduler, HPA | 01, 08 |
| Les données disparaissent avec le conteneur | Stockage indépendant du conteneur | PVC, StatefulSet | 06 |
| Le mot de passe est en clair dans un fichier | Configuration et secrets séparés du code, accès contrôlé | ConfigMap, Secret, RBAC | 03, 09 |

## Bonus

- **Build local :** l'image construite a la même taille, à quelques octets près : mêmes couches de base. Le build réutilise le cache au deuxième lancement.
- **`restart: unless-stopped` :** Docker relance le back après le `kill`… sur cette VM. Si la VM redémarre, Docker relance les conteneurs au démarrage, mais si elle est perdue, rien ne repart ailleurs.
- **Volume nommé :** avec `volumes: [donnees:/var/lib/postgresql/data]` et une section `volumes: {donnees: {}}`, les billets survivent à `down` / `up` (mais pas à `down -v`).
