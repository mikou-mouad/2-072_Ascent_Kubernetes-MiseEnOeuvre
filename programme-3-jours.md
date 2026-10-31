# Kubernetes – Mise en œuvre : programme sur 3 jours

**Référence :** Ascent Formation 2-072 · **Durée :** 3 jours – 18 h · **Public :** administrateurs systèmes, DevOps, développeurs, ingénieurs Cloud

**Rythme d'une journée**

| Demi-journée | Horaires      | Pause         |
|--------------|---------------|---------------|
| Matin        | 9h00 – 12h30  | 10h00 – 10h15 |
| Après-midi   | 13h30 – 16h30 | 15h00 – 15h15 |

**Répartition (hors pauses : 18 h)**

| Type        | Durée   | Part   |
|-------------|---------|--------|
| Pratique (TP) | 13 h 25 | **75 %** |
| Théorie (incident + concept) | 3 h 40 | 20 % |
| Accueil, récapitulatifs, quiz, bilan | 55 min | 5 % |

**Une journée = 6 h = deux modules du programme officiel :**

| Jour | Modules officiels | Durée officielle |
|------|-------------------|------------------|
| 1 – Conteneurs et cluster | Introduction (2 h) + Installation et configuration (4 h) | 6 h |
| 2 – YAML et gestion des ressources | Fichiers descriptifs YAML (3 h) + Gestion des ressources et applications (3 h) | 6 h |
| 3 – Bonnes pratiques et gestion avancée | Bonnes pratiques (3 h) + Gestion avancée (3 h) | 6 h |

La théorie est volontairement courte (15 à 45 min par chapitre) : on présente l'incident, le concept, et on passe tout de suite au TP. Chaque participant travaille seul, sur son propre cluster.

---

## Le fil rouge : l'histoire de FestiPass

**FestiPass** est la petite équipe qui vend les billets du **Festival des Embruns**, trois jours de concerts sur la plage de Saint-Malo en juillet.
Tout se joue en quelques minutes : **l'ouverture de la billetterie, le vendredi à 10h00**, juste après l'annonce de la tête d'affiche. L'an dernier, le site est tombé au bout de 3 minutes.

L'application (code dans `app/`) tient sur **une seule VM**, lancée avec Docker Compose :

```
            ┌──────────────────── VM "billetterie" ───────────────────────┐
 festivaliers ─▶│  front (nginx + page web) ──▶ back (API billets) ──▶ PostgreSQL │
            └─────────────────────────────────────────────────────────────┘
```

Chaque billet vendu est **signé** par le back (calcul PBKDF2) : c'est ce qui consomme du CPU quand tout le monde achète en même temps.

Les personnages :

- **Léa**, directrice du festival : « Vendredi 10h00, le site ne doit pas tomber. Pas cette année. »
- **Yanis**, développeur : il a écrit l'application. « Chez moi, ça marche. »
- **Camille**, administratrice système : elle va construire et exploiter le cluster.

**Principe du cours :** chaque chapitre commence par un **incident** chez FestiPass.
On l'analyse ensemble, on présente le **concept Kubernetes** qui y répond, puis on le met en œuvre en **TP** sur l'application FestiPass.
L'application déployée au TP 02 sert jusqu'au dernier TP : **chaque TP repart de l'état laissé par le précédent.**

| Ch. | Incident chez FestiPass | Concept | Module officiel | Branche du TP |
|-----|-------------------------|---------|-----------------|---------------|
| 0 | L'an dernier, la billetterie est tombée 3 minutes après l'ouverture | Conteneurs, orchestration, positionnement de Kubernetes | Introduction | `tp-00-conteneurs` |
| 1 | « Camille, il nous faut un cluster » | Architecture, kubeadm, gestion des nœuds | Installation et configuration | `tp-01-installation` |
| 2 | Yanis n'a jamais écrit de YAML | YAML, Pod, Deployment, Service | Fichiers descriptifs YAML · Gestion des ressources | `tp-02-yaml` |
| 3 | Le mot de passe de la base est sur GitHub | ConfigMap, Secret | Fichiers descriptifs YAML | `tp-03-configuration` |
| 4 | La version 1.2 est cassée, et personne ne sait pourquoi | Rolling update, rollback, probes, surveillance avec kubectl | Gestion des ressources | `tp-04-cycle-de-vie` |
| 5 | Le test de charge de la recette a fait tomber la prod | Labels, annotations, sélecteurs, requests/limits, LimitRange, ResourceQuota | Bonnes pratiques | `tp-05-bonnes-pratiques` |
| 6 | Maintenance d'un nœud : tous les billets vendus ont disparu | PV, PVC, StorageClass, StatefulSet | Gestion avancée (volumes) | `tp-06-stockage` |
| 7 | Personne n'a fait la sauvegarde cette nuit | Contrôleurs (Job, CronJob, DaemonSet), CRD et opérateurs | Bonnes pratiques | `tp-07-controleurs` |
| 8 | Vendredi 10h00 : l'ouverture de la billetterie | HPA, autoscaling des nœuds | Gestion avancée (autoscaling) | `tp-08-autoscaling` |
| 9 | L'audit de sécurité : « depuis n'importe quel pod, je lis votre base » | ServiceAccount, RBAC, securityContext, Pod Security, NetworkPolicy | Gestion avancée (sécurité) | `tp-09-securite` |

**Les branches :** chaque branche `tp-NN` part de la branche du TP précédent. Elle contient l'énoncé du TP (`tp/NN-*/README.md`) et l'état de l'application à la fin des TP précédents.
La correction du TP NN est dans la même branche (`solutions/NN-*/`), sans rien dévoiler du TP suivant.
Un participant bloqué consulte la correction, ou fait `git checkout tp-NN` pour repartir du bon point de départ.
`solution-finale` contient l'état final de l'application.

---

## Jour 1 – Conteneurs et mise en place du cluster

**Modules officiels :** Introduction (2 h) + Installation et configuration (4 h) · **Théorie 1 h 15 · Pratique 4 h 30 · Autre 15 min**

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 9h00 – 9h15   | Accueil | Tour de table (niveau et attentes de chacun), présentation de FestiPass |
| 9h15 – 10h00  | Théorie | **Ch. 0 – « La billetterie est tombée »** · Conteneurs et images, limites d'une machine unique, orchestration, cluster. Positionnement de Kubernetes dans l'écosystème Cloud (CNCF, offres managées, kubeadm, Minikube) |
| 10h00 – 10h15 | | *Pause* |
| 10h15 – 11h15 | **TP 00** | FestiPass « comme l'an dernier » avec Docker Compose : panne d'un conteneur, mise à jour qui coupe, données perdues |
| 11h15 – 11h45 | Théorie | **Ch. 1 – « Il nous faut un cluster »** · Control plane (API server, etcd, scheduler, controller-manager), nœuds (kubelet, containerd, kube-proxy), CNI, les étapes kubeadm, gestion des nœuds |
| 11h45 – 12h30 | **TP 01** | Préparation des 3 nœuds (swap, modules, sysctl, containerd, paquets), vérifications |
| 12h30 – 13h30 | | *Déjeuner* |
| 13h30 – 15h00 | **TP 01** | `kubeadm init`, Calico, `kubeadm join`, tests réseau, le control plane sans scheduler |
| 15h00 – 15h15 | | *Pause* |
| 15h15 – 16h30 | **TP 01** | Gestion des nœuds : labels, taints, cordon, drain, uncordon, retirer et réintégrer un worker, snapshot des VM |

---

## Jour 2 – YAML et gestion des ressources

**Modules officiels :** Fichiers descriptifs YAML (3 h) + Gestion des ressources et applications (3 h) · **Théorie 1 h 10 · Pratique 4 h 40 · Autre 10 min**

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 9h00 – 9h10   | Récap | Récapitulatif et quiz du jour 1 |
| 9h10 – 9h35   | Théorie | **Ch. 2 – « Yanis n'a jamais écrit de YAML »** · Syntaxe YAML, structure d'un manifest (apiVersion, kind, metadata, spec), Pod, Deployment, Service |
| 9h35 – 10h00  | **TP 02** | Partie A : réparer un YAML cassé, `kubectl explain` |
| 10h00 – 10h15 | | *Pause* |
| 10h15 – 11h50 | **TP 02** | Partie A : écrire un Pod, Pod seul contre Deployment · Partie B : déploiement de FestiPass (namespace, PostgreSQL, back, front), Services ClusterIP et NodePort, scaling, auto-réparation |
| 11h50 – 12h10 | Théorie | **Ch. 3 – « Le mot de passe est sur GitHub »** · ConfigMap, Secret, variables d'environnement, fichiers montés |
| 12h10 – 12h30 | **TP 03** | Secrets et ConfigMap générés avec kubectl |
| 12h30 – 13h30 | | *Déjeuner* |
| 13h30 – 14h25 | **TP 03** | Les manifests utilisent la configuration, annonce du festival montée en fichier, changement de configuration avec et sans redémarrage |
| 14h25 – 14h50 | Théorie | **Ch. 4 – « La 1.2 est cassée »** · Rolling update, stratégies, historique et rollback, probes, surveiller avec kubectl (get -w, describe, logs, events, top, exec, port-forward) |
| 14h50 – 15h00 | **TP 04** | metrics-server |
| 15h00 – 15h15 | | *Pause* |
| 15h15 – 16h30 | **TP 04** | La boîte à outils kubectl, mise à jour 1.0 → 1.1 sans coupure, version 1.2 introuvable, panne mystère à diagnostiquer, rollback |

---

## Jour 3 – Bonnes pratiques et gestion avancée

**Modules officiels :** Bonnes pratiques (3 h) + Gestion avancée (3 h) · **Théorie 1 h 15 · Pratique 4 h 15 · Autre 30 min**

Les deux modules s'entremêlent dans la journée : la sauvegarde automatique (contrôleurs, bonnes pratiques) a besoin des volumes persistants (gestion avancée).

| Horaire       | Type | Contenu |
|---------------|------|---------|
| 9h00 – 9h10   | Récap | Récapitulatif et quiz du jour 2 |
| 9h10 – 9h25   | Théorie | **Ch. 5 – « La recette a fait tomber la prod »** · Labels, annotations, sélecteurs ; requests/limits, QoS, LimitRange, ResourceQuota |
| 9h25 – 10h00  | **TP 05** | Labels recommandés, sélecteurs, pod mis en quarantaine |
| 10h00 – 10h15 | | *Pause* |
| 10h15 – 10h35 | **TP 05** | Namespace de recette, service gourmand, LimitRange, ResourceQuota, requests/limits sur FestiPass |
| 10h35 – 10h50 | Théorie | **Ch. 6 – « Les billets ont disparu »** · Volumes, PV, PVC, StorageClass, provisionnement dynamique, StatefulSet |
| 10h50 – 11h40 | **TP 06** | Reproduction de la perte de données, local-path-provisioner, PostgreSQL en StatefulSet, test de persistance |
| 11h40 – 11h55 | Théorie | **Ch. 7 – « Personne n'a fait la sauvegarde »** · Boucles de contrôle, DaemonSet, Job, CronJob ; CRD et opérateurs |
| 11h55 – 12h30 | **TP 07** | Les contrôleurs au travail, CronJob de sauvegarde PostgreSQL, Job déclenché à la main |
| 12h30 – 13h30 | | *Déjeuner* |
| 13h30 – 13h40 | **TP 07** | Test de restauration, l'opérateur Calico au travail |
| 13h40 – 13h55 | Théorie | **Ch. 8 – « Vendredi 10h00 »** · Autoscaling : HPA, VPA, Cluster Autoscaler, prérequis (metrics-server, requests) |
| 13h55 – 14h45 | **TP 08** | HPA sur le back, simulation de l'ouverture de la billetterie, pods en attente et ajout de capacité, retour au calme |
| 14h45 – 15h00 | Théorie | **Ch. 9 – « Je lis votre base depuis n'importe quel pod »** · ServiceAccount, RBAC, securityContext, Pod Security Admission, NetworkPolicy |
| 15h00 – 15h15 | | *Pause* |
| 15h15 – 16h10 | **TP 09** | Ce que voit un pod, droits de Yanis (RBAC), ServiceAccounts, securityContext, Pod Security « restricted », NetworkPolicies |
| 16h10 – 16h30 | Bilan | Épilogue (l'ouverture de la billetterie, architecture finale contre VM de départ), QCM final, évaluations |

---

## Gérer les niveaux différents

- **TP 02** : énoncé pas à pas avec des manifests à compléter (`TODO`). Il sert aussi de mise à niveau pratique sur YAML.
- **Chaque TP** a une partie obligatoire et des **bonus** pour ceux qui finissent en avance.
- **Rattrapage** : un participant en retard fait `git checkout tp-NN` pour repartir de l'état attendu.

## Préparation du formateur

1. Pousser le dépôt et toutes les branches sur GitHub, le rendre accessible aux participants.
2. Lancer le workflow `images` (onglet Actions) pour publier `festipass-back:1.0`, `festipass-front:1.0` et `festipass-front:1.1` sur `ghcr.io`, puis rendre les paquets publics.
   La version `festipass-front:1.2` **ne doit pas exister** : elle sert à la panne du TP 04.
3. Prévoir 3 VM Ubuntu par participant (2 CPU, 4 Go de RAM minimum, idéalement 8 Go sur les workers), plus la machine **ClientWeb** pour le navigateur. Sans ClientWeb, les participants ouvrent un tunnel sortant Cloudflare (`cloudflared`, sans compte) et utilisent le navigateur de leur poste : la commande est dans les TP 00 et 02.

## Correspondance avec le programme officiel

| Jour | Module officiel                                        | Durée officielle | Durée prévue (dont TP) |
|------|--------------------------------------------------------|------------------|------------------------|
| 1    | Introduction à Kubernetes et à l'orchestration         | 2 h              | 2 h (1 h) : accueil, ch. 0, TP 00 |
| 1    | Installation et configuration de Kubernetes            | 4 h              | 4 h (3 h 30) : ch. 1, TP 01 |
| 2    | Introduction aux fichiers descriptifs YAML             | 3 h              | 3 h (2 h 15) : ch. 2, TP 02 partie A, ch. 3, TP 03 |
| 2    | Gestion des ressources et applications                 | 3 h              | 3 h (2 h 25) : récap, TP 02 partie B, ch. 4, TP 04 |
| 3    | Mise en œuvre des bonnes pratiques                     | 3 h              | 2 h 40 (1 h 40) : récap, ch. 5, TP 05, ch. 7, TP 07, bilan |
| 3    | Gestion avancée (volumes, autoscaling, sécurité)       | 3 h              | 3 h 20 (2 h 35) : ch. 6, TP 06, ch. 8, TP 08, ch. 9, TP 09 |
| **Total (hors pauses)** |                                     | **18 h**         | **18 h (13 h 25)**     |

Le jour 3 fait bien 6 h : la gestion avancée prend 20 minutes de plus que prévu, au profit du TP de sécurité, qui conclut la formation.
