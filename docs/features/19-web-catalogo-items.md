# Web: catálogos de ítems (/items y /items-all)

Dos páginas privadas de la web (no están en la navegación, llevan `noindex`). Piden la clave del staff
(`_items_admin_token` en `web/server.py`).

| Página | Qué muestra | Datos | Imágenes |
|---|---|---|---|
| `/items` | Ítems custom curados (23): accesorios dorados, premium scrolls, runas, trainer dummy, armas del Crisol, crimson, fury cape, armas PvP, wands, enchanted spear. Con stats y el comando `/i` para copiar | `web/data/items_catalog.json` | `web/assets/items/custom/<serverId>.png` |
| `/items-all` | Todos los ítems del OTB de producción (5.072, incluidos los 66 custom desde `20100`) | `web/data/items_all.json` | `web/assets/items/items-atlas.png` |

Las dos salen del **cliente actual** (`devtools/rme/rme-client-760`) y del **OTB de producción**
(`items-zagan-test.otb`). Regenerar después de cambiar sprites o ítems:

```bash
python3.11 scripts/export-items-catalog-web.py --dat devtools/rme/rme-client-760/Tibia.dat \
    --spr devtools/rme/rme-client-760/Tibia.spr --otb server/YurOTS/ots/data/items/items-zagan-test.otb
python3.11 scripts/web/build-items-catalog.py
```

- `export-items-catalog-web.py` arma el atlas y `items_all.json`.
- `build-items-catalog.py` recorta del atlas la imagen de cada ítem de `items_catalog.json`, completa
  `clientId` y los stats (ataque, defensa, armadura, slot, peso) desde el OTB y avisa si alguno no existe
  o no tiene sprite. Para sumar un ítem al catálogo: agregar su fila (nombre, descripción, categoría,
  `serverId`, `spawn`) y correr el script.
- No se compila nada: es Python. La web no hay que recompilarla (estas páginas no son de Astro).

**Historia (nov 2026):** `/items-all` era de julio (OTB vanilla, sin ningún Zagan) y las imágenes de `/items`
vivían en `web/private/zagan-items/`, fuera de git, solo en el VPS: se perdieron con él y la página
mostraba 14 imágenes rotas. `scripts/sync-zagan-items-web.py` dependía del pack Zagan original, que
tampoco existe más. De los Aurora solo está el Shield (`20165`, nov 2026); Blade y Axe no llegaron al OTB.
