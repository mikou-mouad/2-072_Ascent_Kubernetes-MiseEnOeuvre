# Image nginx sans root : écoute sur 8080, utilisateur 101
FROM public.ecr.aws/nginx/nginx-unprivileged:1.28-alpine

ARG APP_VERSION=1.0
ARG COULEUR=#1d3557

# BACK_URL est injecté dans la conf nginx au démarrage (templates du conteneur nginx).
ENV BACK_URL=http://back:8080

COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY index.html /usr/share/nginx/html/index.html
COPY annonce.txt /usr/share/nginx/html/config/annonce.txt
USER root
RUN sed -i "s|__VERSION__|${APP_VERSION}|g; s|__COULEUR__|${COULEUR}|g" /usr/share/nginx/html/index.html
USER 101

EXPOSE 8080
