#!/usr/bin/env bash
# HTTPS para la web YurOTS en el VPS (nginx + Let's Encrypt).
#
# Requiere un dominio (o subdominio gratis) apuntando a la IP del VPS.
# Ejemplo gratis: DuckDNS → yurots.duckdns.org → 64.176.20.238
#
# Uso en el VPS (como root):
#   cd /root/yurots-principal
#   git pull
#   ./scripts/setup-vps-https.sh tudominio.com
#
# Opcional: email para Let's Encrypt
#   CERTBOT_EMAIL=admin@tudominio.com ./scripts/setup-vps-https.sh tudominio.com
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${CERTBOT_EMAIL:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NGINX_SITE="/etc/nginx/sites-available/yurots"
NGINX_ENABLED="/etc/nginx/sites-enabled/yurots"

if [[ -z "$DOMAIN" ]]; then
  echo "Uso: $0 <dominio>" >&2
  echo "Ejemplo: $0 yurots.duckdns.org" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Ejecutá como root en el VPS." >&2
  exit 1
fi

echo "==> Instalando nginx y certbot..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx

echo "==> Configurando nginx para $DOMAIN ..."
sed "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" "$ROOT/deploy/nginx/yurots.conf" >"$NGINX_SITE"
rm -f /etc/nginx/sites-enabled/default
ln -sf "$NGINX_SITE" "$NGINX_ENABLED"
nginx -t
systemctl enable nginx
systemctl reload nginx

echo "==> Abriendo puertos 80 y 443 en ufw..."
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw reload
fi

echo "==> Comprobando que el dominio apunta a este servidor..."
RESOLVED="$(getent ahostsv4 "$DOMAIN" | awk '{print $1; exit}' || true)"
PUBLIC_IP="$(curl -4 -s --max-time 5 ifconfig.me || curl -4 -s --max-time 5 icanhazip.com || true)"
if [[ -n "$RESOLVED" && -n "$PUBLIC_IP" && "$RESOLVED" != "$PUBLIC_IP" ]]; then
  echo "AVISO: $DOMAIN resuelve a $RESOLVED pero esta máquina es $PUBLIC_IP" >&2
  echo "Corregí el DNS antes de continuar (A record → $PUBLIC_IP)." >&2
  read -r -p "¿Continuar igual? [y/N] " ans
  [[ "${ans,,}" == "y" ]] || exit 1
fi

echo "==> Obteniendo certificado SSL (Let's Encrypt)..."
CERTBOT_ARGS=(--nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect)
if [[ -n "$EMAIL" ]]; then
  CERTBOT_ARGS+=(--email "$EMAIL")
else
  CERTBOT_ARGS+=(--register-unsafely-without-email)
fi
certbot "${CERTBOT_ARGS[@]}"

echo "==> Actualizando SERVER_IP en yurots-web.service ..."
if [[ -f /etc/systemd/system/yurots-web.service ]]; then
  sed -i "s|^Environment=SERVER_IP=.*|Environment=SERVER_IP=$DOMAIN|" /etc/systemd/system/yurots-web.service
  systemctl daemon-reload
  systemctl restart yurots-web
fi

echo ""
echo "============================================"
echo "  HTTPS listo: https://$DOMAIN/"
echo "  El OT sigue en 64.176.20.238:7171 (cliente Tibia)"
echo "============================================"
echo ""
echo "Renovación automática: certbot renew (timer systemd ya instalado)"
