# TP 00 – FestiPass « comme l'an dernier »

**Durée :** 45 min · **Branche :** `tp-00-conteneurs` · **Correction :** `solutions/00-conteneurs/`, dans cette branche

## L'incident

> L'an dernier, vendredi, 10h03. La tête d'affiche vient d'être annoncée, 4 000 festivaliers se connectent en même temps.
> La VM de la billetterie est à 100 % de CPU. Yanis redémarre le conteneur du back pour « débloquer » : le site est coupé 20 minutes.
> Cette année, Léa veut comprendre ce qui s'est passé avant de choisir une solution.

On rejoue l'application telle qu'elle tournait l'an dernier : **une VM, Docker Compose, trois conteneurs.**

## Objectifs

- Lancer une application multi-conteneurs avec Docker Compose et identifier images, conteneurs, réseau et volumes.
- Constater les limites d'une machine unique : panne, mise à jour, montée en charge, données.
- Lister ce qu'on attend d'un orchestrateur.

## Où travailler

Ce TP se fait sur le **control plane** (`10.10.0.10`), **avant** l'installation du cluster.
À la fin du TP, Docker est désinstallé et la VM redémarrée : le TP 01 part d'une machine propre.

## Étapes

### 1. Installer Docker et récupérer le dépôt

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
newgrp docker                       # ou déconnexion / reconnexion

git clone https://github.com/mikou-mouad/2-072_Ascent_Kubernetes-MiseEnOeuvre.git ~/festipass
cd ~/festipass
git checkout tp-00-conteneurs
```

### 2. Lancer FestiPass

Lisez `app/docker-compose.yml`, puis :

```bash
cd ~/festipass/app
docker compose up -d
docker compose ps
docker images
```

Depuis la machine **ClientWeb** (bouton **Ouvrir la console** de votre environnement de TP), ouvrez un navigateur sur `http://10.10.0.10:8000` et achetez deux pass.

**Questions :**

1. Combien de conteneurs tournent ? Lequel est exposé à l'extérieur, et sur quel port ?
2. Comment le back trouve-t-il PostgreSQL ? (indice : `DB_HOST`, puis `docker network ls` et `docker network inspect app_default`)
3. Où est écrit le mot de passe de la base ? Qui peut le lire ?

### 3. Regarder à l'intérieur

```bash
docker compose logs back --tail=5          # logs JSON : une ligne par événement
docker compose exec back env | grep DB_
docker compose exec postgres psql -U festipass -c 'select pass, count(*) from billets group by pass'
docker history ghcr.io/mikou-mouad/festipass-back:1.0 | head
```

**Question 4 :** une image est faite de couches. Quelle couche change quand Yanis modifie seulement `app.py` (voir `app/back/Dockerfile`) ?

### 4. Panne : le back s'arrête

Ouvrez un **second terminal** sur le control plane et laissez tourner cette boucle, qui interroge le site toutes les 0,5 s :

```bash
while true; do curl -s -o /dev/null -w "%{http_code} " http://localhost:8000/api/version; sleep 0.5; done
```

Dans le premier terminal, simulez un plantage :

```bash
docker kill app-back-1
docker compose ps
```

**Question 5 :** la boucle affiche `502`. Le conteneur redémarre-t-il seul ? Qui doit intervenir, et à 10h03 un vendredi, combien de temps cela prend-il ?

Relancez-le : `docker compose up -d`.

### 5. Mise à jour : le front passe en 1.1

Yanis livre le front 1.1 (bandeau corail). Gardez la boucle du second terminal ouverte.

```bash
sed -i 's/festipass-front:1.0/festipass-front:1.1/' docker-compose.yml
docker compose up -d front
```

**Question 6 :** la boucle a-t-elle affiché des erreurs (`000`) ? Pourquoi une mise à jour coupe-t-elle le service ici ?

### 6. Le rush : plus de back ?

```bash
docker compose up -d --scale back=3
docker compose ps
```

**Question 7 :** on a 3 back… sur la même VM. Qu'a-t-on gagné si la VM sature ou tombe ?

### 7. Les données

Notez le nombre de billets vendus, puis faites ce que Yanis a fait l'an dernier pour « repartir propre » :

```bash
docker compose down
docker compose up -d
```

Rechargez la page.

**Question 8 :** où sont passés les billets ? (indice : `docker volume ls`, et la ligne `VOLUME` de l'image postgres : `docker image inspect public.ecr.aws/docker/library/postgres:16 -f '{{.Config.Volumes}}'`)

### 8. Ce qu'on attend d'un orchestrateur

En binôme, complétez le tableau (on le corrige ensemble, il servira de fil rouge jusqu'au dernier jour) :

| Problème constaté | Ce qu'il faudrait |
|-------------------|-------------------|
| Le back planté reste planté | … |
| La mise à jour coupe le site | … |
| Une seule machine pour tout | … |
| Les données disparaissent avec le conteneur | … |
| Le mot de passe est en clair dans un fichier | … |

### 9. Nettoyage (obligatoire)

Docker modifie les règles réseau (iptables) de la VM et gênerait Kubernetes. On le retire **avant** le TP 01 :

```bash
cd ~/festipass/app
git checkout docker-compose.yml           # annule la modification de l'étape 5
docker compose down -v
sudo apt-get purge -y docker.io docker-compose-v2
sudo reboot
```

Ne lancez **pas** `apt autoremove` : il retirerait aussi containerd, dont Kubernetes a besoin.

## Bonus

- Construisez l'image du back en local (`docker compose build back`) et comparez sa taille avec celle de ghcr.io.
- Ajoutez `restart: unless-stopped` au back et refaites l'étape 4 : qu'est-ce qui change ? Que se passe-t-il si c'est la VM qui redémarre ?
- Déclarez un volume nommé pour PostgreSQL dans `docker-compose.yml` et refaites l'étape 7.
