# TP 03 – « Le mot de passe de la base est sur GitHub »

**Durée :** 1 h 25 · **Branche :** `tp-03-configuration` · **Correction :** `solutions/03-configuration/`, dans cette branche

## L'incident

> Mardi, 10h40. Un festivalier curieux écrit au support : « Votre mot de passe `embruns-2026` traîne dans votre dépôt GitHub public. »
> Il est dans `docker-compose.yml`, dans `k8s/10-postgres.yaml`, dans `k8s/20-back.yaml`… Et pour changer le nombre maximum de billets par personne, Yanis doit modifier un manifest et le redéployer.
> Camille : « On change le mot de passe, et on sort toute la configuration des manifests. »

## Objectifs

- Créer des Secrets et des ConfigMaps, en les générant avec `kubectl`.
- Les injecter dans les pods en variables d'environnement et en fichiers.
- Savoir quand un changement de configuration est pris en compte, et comment le forcer.
- Savoir ce qu'un Secret protège… et ce qu'il ne protège pas.

## Point de départ

```bash
cd ~/festipass && git fetch
git stash -u
git checkout tp-03-configuration
kubectl apply -f k8s/                 # l'état attendu à la fin du TP 02
```

Le nouveau mot de passe de la base est **`maree-haute-2026`**.

## Étapes

### 1. Les Secrets

Générez les manifests avec `kubectl` plutôt que de les écrire à la main (le base64 est fait pour vous) :

```bash
kubectl create secret generic festipass-db \
  --from-literal=POSTGRES_USER=festipass \
  --from-literal=POSTGRES_PASSWORD=maree-haute-2026 \
  --dry-run=client -o yaml > k8s/01-secret.yaml

echo '---' >> k8s/01-secret.yaml

kubectl create secret generic back-signature \
  --from-literal=CLE_SIGNATURE=$(openssl rand -hex 16) \
  --dry-run=client -o yaml >> k8s/01-secret.yaml
```

Ajoutez `namespace: festipass` dans les deux `metadata`, puis appliquez le fichier.

```bash
kubectl get secrets
kubectl describe secret festipass-db                       # les valeurs sont masquées…
kubectl get secret festipass-db -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d; echo
```

**Question 1 :** un Secret est-il chiffré ? Qui peut lire ce mot de passe ? Pourquoi ce fichier `01-secret.yaml` ne devrait-il pas aller dans Git non plus ?

### 2. La ConfigMap du back

```bash
kubectl create configmap back-config \
  --from-literal=DB_HOST=postgres \
  --from-literal=DB_NAME=festipass \
  --from-literal="FESTIVAL=Festival des Embruns" \
  --from-literal=PASS_MAX=4 \
  --dry-run=client -o yaml > k8s/02-configmap.yaml
```

Ajoutez `namespace: festipass`, puis appliquez.

### 3. Les manifests utilisent la configuration

**PostgreSQL** (`k8s/10-postgres.yaml`) : remplacez `POSTGRES_USER` et `POSTGRES_PASSWORD` par la lecture de tout le Secret :

```yaml
          env:
            - name: POSTGRES_DB
              value: festipass
          envFrom:
            - secretRef:
                name: festipass-db
```

**Le back** (`k8s/20-back.yaml`) : supprimez toute la liste `env` actuelle et remplacez-la par :

- un `envFrom` qui lit la ConfigMap `back-config` ;
- trois variables `DB_USER`, `DB_PASSWORD` et `CLE_SIGNATURE` lues dans les Secrets avec `valueFrom.secretKeyRef` (`kubectl explain pod.spec.containers.env.valueFrom.secretKeyRef`).

Appliquez, puis vérifiez :

```bash
kubectl apply -f k8s/
kubectl get pods -w                         # Ctrl+C quand tout est Running et 1/1
kubectl exec deploy/back -- env | grep -E 'DB_|FESTIVAL|PASS_MAX'
grep -rn embruns-2026 k8s/                  # plus aucun résultat
```

Rechargez le site et achetez des pass.

**Question 2 :** les billets vendus au TP 02 ont disparu. Pourquoi ? (on règle ce problème au chapitre 6)

### 4. Changer une variable : le nombre de billets par personne

Léa autorise 6 billets par personne. Dans `k8s/02-configmap.yaml`, passez `PASS_MAX` à `"6"`, puis :

```bash
kubectl apply -f k8s/02-configmap.yaml
kubectl exec deploy/back -- env | grep PASS_MAX
```

**Question 3 :** la valeur a-t-elle changé dans le pod ? Pourquoi ?

Forcez la prise en compte :

```bash
kubectl rollout restart deployment back
kubectl rollout status deployment back
kubectl exec deploy/back -- env | grep PASS_MAX
```

Vérifiez sur le site : la ligne « Nombre de billets » affiche 6 maximum.

### 5. Un fichier de configuration : l'annonce du festival

Le bandeau jaune du site affiche le fichier `/config/annonce.txt` du front. Léa veut le changer sans attendre une nouvelle image.

```bash
kubectl create configmap front-annonce \
  --from-file=annonce.txt=tp/03-configuration/annonce.txt \
  --dry-run=client -o yaml > k8s/03-front-annonce.yaml
```

Ajoutez `namespace: festipass`, appliquez. Puis, dans `k8s/30-front.yaml`, montez cette ConfigMap comme un **volume** dans le dossier `/usr/share/nginx/html/config` du conteneur front (`volumes` au niveau du pod, `volumeMounts` au niveau du conteneur). Appliquez et vérifiez le bandeau sur le site.

Maintenant, modifiez le texte de l'annonce **directement dans le manifest** `k8s/03-front-annonce.yaml` (par exemple « 6 billets maximum par personne »), puis :

```bash
kubectl apply -f k8s/03-front-annonce.yaml
watch -n 5 "kubectl exec deploy/front -- cat /usr/share/nginx/html/config/annonce.txt"
```

**Question 4 :** combien de temps faut-il pour que le fichier change dans le pod ? A-t-on redémarré quelque chose ? Pourquoi est-ce différent de l'étape 4 ?

## Questions de fin

5. Variable d'environnement ou fichier monté : que choisir pour un mot de passe ? Pour un fichier de configuration nginx ?
6. Un pod référence une ConfigMap qui n'existe pas : que se passe-t-il ? (essayez : `kubectl run test --image=public.ecr.aws/docker/library/busybox:1.36 --overrides='{"spec":{"containers":[{"name":"test","image":"public.ecr.aws/docker/library/busybox:1.36","envFrom":[{"configMapRef":{"name":"nexiste-pas"}}]}]}}'`, puis `kubectl describe pod test`, puis supprimez-le)
7. Comparez avec le tableau du TP 00 : quelle ligne est réglée ?

## Bonus

- Rendez la ConfigMap `back-config` immuable (`immutable: true`). Que se passe-t-il quand vous la modifiez ? Quel intérêt ?
- Générez une ConfigMap à partir d'un fichier `.env` : `kubectl create configmap essai --from-env-file=<fichier> --dry-run=client -o yaml`.
- Cherchez comment les outils suivants évitent de mettre des Secrets dans Git : Sealed Secrets, SOPS, External Secrets Operator.
