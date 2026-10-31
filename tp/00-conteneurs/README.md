# TP 00 – FestiPass « comme l'an dernier »

**Durée :** 1 h · **Branche :** `tp-00-conteneurs` · **Correction :** `solutions/00-conteneurs/`, dans cette branche

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

Ce TP se fait sur le **control plane** (`10.10.0.20`), **avant** l'installation du cluster.
À la fin du TP, Docker est désinstallé et la VM redémarrée : le TP 01 part d'une machine propre.

> **Le terminal affiche des logs « shell integration » à chaque ligne ?** C'est le prompt de la session qui est mal configuré, pas un problème de la VM. Corrigez-le pour la session en cours :
>
> ```bash
> unset PROMPT_COMMAND
> PS1='\u@\h:\w\$ '
> PS0=''
> ```
>
> C'est à retaper à chaque nouvelle session SSH (et après chaque redémarrage), sauf si vous l'ajoutez une fois pour toutes à la fin de `~/.bashrc`, sur chaque machine :
>
> ```bash
> echo 'unset PROMPT_COMMAND; PS1="\u@\h:\w\$ "' >> ~/.bashrc
> echo 'PS0=""' >> ~/.bashrc
> source ~/.bashrc
> ```
>
> Les logs reviennent à la session suivante ? Un autre fichier redéfinit `PROMPT_COMMAND` après `~/.bashrc`. Trouvez-le :
>
> ```bash
> grep -n "machineid\|PROMPT_COMMAND" ~/.bashrc ~/.profile /etc/profile.d/* 2>/dev/null
> ```
>
> Ajoutez la même ligne à la fin du fichier trouvé (remplacez `<fichier>` par son nom ; `sudo` est nécessaire pour un fichier de `/etc`) :
>
> ```bash
> echo 'unset PROMPT_COMMAND; PS1="\u@\h:\w\$ "; PS0=""' | sudo tee -a <fichier>
> ```

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

Depuis la machine **ClientWeb** (bouton **Ouvrir la console** de votre environnement de TP), ouvrez un navigateur sur `http://10.10.0.20:8000` et achetez deux pass.

> **Pas de machine ClientWeb dans votre environnement ?** Ouvrez un tunnel **sortant** depuis le control plane. Il tourne en arrière-plan (`-d`) : le terminal reste libre.
>
> ```bash
> docker run -d --name cf-tunnel --restart unless-stopped --network host \
>   cloudflare/cloudflared:latest tunnel --no-autoupdate --url http://localhost:8000
> sleep 10                                   # le temps que le tunnel obtienne son adresse
> docker logs cf-tunnel 2>&1 | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com'
> ```
>
> Ouvrez l'adresse affichée dans le navigateur de **votre poste**. Elle reste valable pendant tout le TP ; on supprime le tunnel à l'étape 9.

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

Lancez une **sonde** en arrière-plan (`&` à la fin) : elle interroge le site toutes les 0,5 s et note chaque code HTTP dans un fichier. `-m 2` limite chaque requête à 2 secondes : une requête sans réponse est notée `000`.

```bash
while true; do curl -s -m 2 -o /dev/null -w "%{http_code} " http://localhost:8000/api/version; sleep 0.5; done > /tmp/sonde.log &
```

Simulez un plantage, puis regardez ce qu'a vu la sonde :

```bash
docker kill app-back-1
sleep 10
docker compose ps
tail -c 120 /tmp/sonde.log; echo         # les derniers codes HTTP
```

**Question 5 :** la sonde n'affiche plus que des `000` (puis, au bout d'une minute, des `502` ou `504` renvoyés par nginx). Que s'est-il passé côté front ? Le conteneur redémarre-t-il seul ? Qui doit intervenir, et à 10h03 un vendredi, combien de temps cela prend-il ?

Relancez-le : `docker compose up -d`.

### 5. Mise à jour : le front passe en 1.1

Yanis livre le front 1.1 (bandeau corail). La sonde tourne toujours : on vide son fichier, on met à jour, puis on lit ce qu'elle a vu.

```bash
> /tmp/sonde.log
sed -i 's/festipass-front:1.0/festipass-front:1.1/' docker-compose.yml
docker compose up -d front
sleep 5
cat /tmp/sonde.log; echo
kill %1                                  # arrête la sonde
```

**Question 6 :** la sonde a-t-elle noté des erreurs (`000` ou `502`) ? Pourquoi une mise à jour coupe-t-elle le service ici ?

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

Complétez le tableau (on le corrige ensemble, il servira de fil rouge jusqu'au dernier jour) :

| Problème constaté | Ce qu'il faudrait |
|-------------------|-------------------|
| Le back planté reste planté | … |
| La mise à jour coupe le site | … |
| Une seule machine pour tout | … |
| Les données disparaissent avec le conteneur | … |
| Le mot de passe est en clair dans un fichier | … |

### 9. Nettoyage (obligatoire)

Docker modifie les règles réseau (iptables) de la VM et gênerait Kubernetes. On le retire **avant** le TP 01.
Le tunnel Cloudflare disparaît avec lui : on en ouvrira un nouveau dans le cluster au TP 02.

```bash
cd ~/festipass/app
docker rm -f cf-tunnel 2>/dev/null       # le tunnel, s'il existe
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
