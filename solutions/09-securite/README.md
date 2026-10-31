# Correction du TP 09 – Sécurité

Fichiers corrigés, aux mêmes chemins que dans le dépôt :

- `k8s/00-namespace.yaml` : les labels Pod Security « restricted » ;
- `k8s/10-postgres.yaml`, `k8s/20-back.yaml`, `k8s/30-front.yaml`, `k8s/40-sauvegarde.yaml` : ServiceAccount et `securityContext` ;
- `k8s/securite/10-serviceaccounts.yaml` : un ServiceAccount par composant, sans token ;
- `k8s/securite/20-rbac-yanis.yaml` : le rôle `developpeur` et son binding ;
- `k8s/securite/30-networkpolicies.yaml` : refus par défaut, puis les flux autorisés.

Pour comparer : `diff -r solutions/09-securite/k8s k8s`.

Ordre d'application conseillé sur un cluster neuf : `kubectl apply -f k8s/securite/10-serviceaccounts.yaml`, puis `kubectl apply -R -f k8s/` (un pod qui référence un ServiceAccount inexistant est refusé, le contrôleur réessaie ensuite).

1. **Ce qu'a fait l'auditrice :** lancer un pod en **root** sans restriction ; trouver un **token d'API** monté dans le pod (et dans ceux du back) ; joindre **PostgreSQL** et le **back** depuis un autre namespace ; lire la base avec le mot de passe. Les pods de FestiPass : back en `uid=10001`, front en `uid=101`, mais **postgres en root** (`uid=0`) au démarrage. FestiPass n'a besoin que de : front joignable de partout, back joignable par le front, base joignable par le back et la sauvegarde. Aucun pod n'a besoin du token, ni de root.
2. **Role / RoleBinding :** les droits de Yanis ne concernent que `festipass`. Un `ClusterRoleBinding` les donnerait dans **tous** les namespaces, y compris `kube-system`. (On peut aussi réutiliser un `ClusterRole` dans un `RoleBinding` : les droits restent limités au namespace du binding, c'est ainsi qu'on utilise les rôles intégrés `view` ou `edit`.) **Identité :** Kubernetes ne stocke pas d'utilisateurs. Le nom vient de l'authentification : le `CN` du certificat client (voir le bonus), ou le jeton OIDC d'un annuaire (Entra ID, Keycloak…). `--as yanis` est une **impersonation** : l'administrateur demande à l'API d'évaluer la requête comme si elle venait de yanis. `create pods/exec` : **non**, Yanis ne peut pas entrer dans les conteneurs (où il lirait les variables d'environnement, donc le mot de passe).
3. **Pod refusé :** `Error from server (Forbidden): pods "pirate" is forbidden: violates PodSecurity "restricted:latest": allowPrivilegeEscalation != false, unrestricted capabilities, runAsNonRoot != true, seccompProfile`. La règle est **imposée par l'API** à tout le monde : un manifest oublié, un `kubectl run` rapide, une image tierce ne passent pas. L'audit et les avertissements (`warn`, `audit`) permettent de préparer la bascule.
4. **Le pirate après :** il ne joint plus ni PostgreSQL, ni le back (timeouts). Il joint toujours le front, comme tout le monde. Le mot de passe, lui, n'a pas changé : il a fuité dans le rapport d'audit et dans le dépôt (`01-secret.yaml`) ; il faudrait le changer. Le pirate est toujours root **dans la recette** : il faudrait aussi imposer `restricted` (ou au moins `baseline`) à `festipass-recette`.
5. **Probes :** oui. Le trafic entre un nœud et ses propres pods est toujours autorisé par les NetworkPolicies : le kubelet fait ses probes depuis le nœud.
6. **Tableau du TP 00 :** redémarrage automatique (TP 02), mises à jour sans coupure (TP 04), plusieurs machines et montée en charge (TP 01, 08), données persistantes (TP 06) et sauvegardées (TP 07), configuration et secrets hors du code, avec un accès contrôlé (TP 03, 09). Restent pour aller plus loin : la haute disponibilité du control plane et de la base, le stockage réseau, la supervision (Prometheus, Grafana), les logs centralisés.
7. **Lecture des Secrets :** les administrateurs du cluster ; tout compte qui peut créer un pod dans `festipass` (il peut monter le Secret dans son pod) ; quiconque accède à etcd ou à ses sauvegardes, si le chiffrement au repos n'est pas activé ; et le dépôt Git, où `01-secret.yaml` est en clair. D'où Sealed Secrets, SOPS ou External Secrets (TP 03).

## Bonus

- **Certificat :** `kubectl auth whoami` affiche `Username: yanis`, `Groups: [developpeurs system:authenticated]`. On pourrait lier le rôle au **groupe** `developpeurs` plutôt qu'à l'utilisateur.
- **Front en lecture seule :**

```yaml
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
            - name: conf
              mountPath: /etc/nginx/conf.d
      volumes:
        - name: tmp
          emptyDir: {}
        - name: conf
          emptyDir: {}
```

- **Egress :** sans règle DNS, le back ne résout plus `postgres` : `/readyz` échoue, les pods sortent du Service.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: back-sortie
  namespace: festipass
spec:
  podSelector:
    matchLabels:
      app: back
  policyTypes: ["Egress"]
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - port: 5432
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP
```

- **Job de restauration :** ajoutez le même `securityContext` que la sauvegarde (pod : `runAsNonRoot`, `runAsUser/Group 999`, `seccompProfile` ; conteneur : `allowPrivilegeEscalation: false`, `drop: ["ALL"]`) et `serviceAccountName: sauvegarde` (son label `app: sauvegarde` lui ouvre déjà l'accès réseau à postgres).
