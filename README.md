# Kubernetes – Mise en œuvre : supports de formation

Formation Ascent 2-072 de 3 jours (18 h, 75 % de pratique), racontée à travers l'histoire de **FestiPass**, la billetterie du Festival des Embruns, qui passe d'une VM Docker Compose à Kubernetes avant l'ouverture des ventes, vendredi à 10h00.

- [programme-3-jours.md](programme-3-jours.md) : le programme détaillé et le fil rouge
- [guide-installation-cluster.md](guide-installation-cluster.md) : installation du cluster de TP (kubeadm, containerd, Calico)
- `app/` : l'application FestiPass (front nginx, back Python, PostgreSQL)
- `presentation/` : les slides en HTML, sur la branche `main` (ouvrir `presentation/index.html`)
- `tp/` : les énoncés des TP (un dossier par TP, ajouté dans chaque branche)

## Les branches des TP

Chaque branche part de la précédente. La branche `tp-NN` contient :

- l'application dans l'état attendu au début du TP NN ;
- l'énoncé du TP (`tp/NN-*/README.md`) ;
- sa correction (`solutions/NN-*/`), ainsi que celles des TP précédents.

Elle ne contient rien du TP suivant : on peut consulter la correction sans découvrir la suite.

| Branche | TP |
|---------|----|
| `tp-00-conteneurs` | FestiPass avec Docker Compose, les limites d'une seule machine |
| `tp-01-installation` | Installation du cluster et gestion des nœuds |
| `tp-02-yaml` | YAML, Pod, Deployment, Service : FestiPass sur le cluster |
| `tp-03-configuration` | ConfigMap et Secret |
| `tp-04-cycle-de-vie` | Mises à jour, rollback, surveillance avec kubectl |
| `tp-05-bonnes-pratiques` | Labels, sélecteurs, requests/limits, LimitRange, ResourceQuota |
| `tp-06-stockage` | PVC, StorageClass, StatefulSet |
| `tp-07-controleurs` | Job, CronJob, opérateurs |
| `tp-08-autoscaling` | HPA et capacité des nœuds |
| `tp-09-securite` | RBAC, ServiceAccount, securityContext, Pod Security, NetworkPolicy |
| `solution-finale` | État final de l'application, toutes corrections appliquées |

Sur le control plane :

```bash
git clone https://github.com/mikou-mouad/2-072_Ascent_Kubernetes-MiseEnOeuvre.git ~/festipass
cd ~/festipass
git checkout tp-00-conteneurs
```

Au début de chaque TP suivant :

```bash
cd ~/festipass && git fetch
git stash -u                  # met de côté votre travail du TP précédent
git checkout tp-03-configuration
```

## Les images

Le workflow `.github/workflows/images.yml` publie les images sur `ghcr.io/mikou-mouad` :

| Image | Tags |
|-------|------|
| `festipass-back` | `1.0` |
| `festipass-front` | `1.0` (bandeau bleu marine), `1.1` (bandeau corail, pour le rolling update) |

Le tag `festipass-front:1.2` n'existe pas, volontairement : c'est la « version cassée » du TP 04.

Pour essayer l'application « comme sur la VM » : `cd app && docker compose up -d`, puis http://localhost:8000.
