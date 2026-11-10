# Guía para escribir artículos de la wiki

La wiki es para **jugadores**, no para el staff. Cada artículo explica una cosa del servidor para que alguien que nunca la vio la entienda en un minuto.

Los archivos que empiezan con `_` (como este) no se publican. Cómo se publica la wiki: `docs/features/18-web-astro.md`.

## Archivo

Un archivo por tema: `web/site/src/wiki/<slug>.md`. El slug es corto, en minúsculas, con guiones y sin tildes (`gemas`, `el-crisol`, `soft-boots`). La URL queda `retro76.cl/wiki/<slug>`.

Encabezado obligatorio:

```
---
titulo: Gemas e imbuements
categoria: Progresión y botín
resumen: Junta gemas de monstruos furiosos, cámbialas por gemas grandes y mejora tu equipo para siempre.
orden: 10
icono: 2154
estado: publicado
---
```

- **titulo:** el nombre que usan los jugadores.
- **categoria:** una de estas, escrita igual:
  `Primeros pasos`, `PvP`, `Progresión y botín`, `Items especiales`, `Lugares y actividades`, `Hechizos y combate`, `NPCs y economía`, `Monstruos`.
- **resumen:** una sola oración, máximo ~110 caracteres. Dice qué es y para qué sirve. Se muestra en el índice y en buscadores.
- **orden:** número para ordenar dentro de la categoría (menor = más arriba).
- **icono:** server id de un ítem que represente el tema (opcional).
- **estado:** `publicado` o `borrador`. Los borradores no aparecen en la web. Usar `borrador` si la función no está activa en el juego todavía o si hay dudas que no se pudieron resolver.

## Estructura del artículo

Siempre en este orden; saltar las secciones que no apliquen:

1. **`## Lo esencial`**: 3 a 5 viñetas con lo más importante (números incluidos). Quien lea solo esto ya sabe lo principal.
2. **`## Cómo se hace`** (o `## Cómo funciona`): pasos numerados, uno por acción.
3. **Detalles**: secciones `##` con nombres concretos (`## Precios`, `## Qué gema va en qué equipo`). Tablas cuando hay más de 3 datos comparables.
4. **Avisos**: `> **Ojo:** ...` para lo que puede hacer perder algo (oro, ítems, gemas). `> **Tip:** ...` para un consejo útil. Máximo uno o dos por artículo.
5. **`## Relacionado`**: viñetas con enlaces a otros artículos.

## Cómo escribir

- Tú, no vos ni usted: "escribe", "usa", "puedes".
- Oraciones cortas. Una idea por oración. Sin relleno ("cabe destacar", "es importante mencionar").
- Números exactos y en cifras: `50%`, `20 gemas`, `1.000 gp`, `2 h`.
- Nada técnico: sin ids, archivos, C++, Lua, actionid, "spawntime", "AID". Si un dato solo le sirve al staff, no va.
- Nombres de ítems, NPCs y monstruos como aparecen en el juego (en inglés si el juego los muestra en inglés: *Big Ruby*, *Soft Boots*).
- Lo que se le dice a un NPC o se escribe en el chat va entre comillas invertidas: `` `hi` ``, `` `exchange ruby` ``, `` `!pz` ``.
- Ubicaciones: lugar reconocible primero ("en el templo, al lado de Parived"), coordenadas al final si ayudan (`140, 50, piso 7`).
- Largo: lo justo. La mayoría de los artículos caben en 150–350 palabras más tablas.

## Formato disponible

- `## Título` y `### Subtítulo`.
- Párrafos, `- viñetas`, `1. pasos`.
- `**negrita**` (con moderación: solo números o palabras clave).
- Tablas Markdown.
- `> **Ojo:** ...`, `> **Tip:** ...`, o `> texto` (nota neutra).
- Enlace a otro artículo: `[[gemas]]` o `[[gemas|texto del enlace]]`.
- Enlace normal: `[texto](https://...)` o a una sección de la web: `[página Gemas](/gemas)`.
- Ícono de un ítem dentro del texto: `{item:2154}` (server id). Ponerlo antes del nombre: `{item:2154} Yellow Gem`.
  Después de agregar un id nuevo, correr `python3 scripts/web/build-wiki-icons.py` (si el ítem no tiene imagen, la wiki no muestra ícono).
- Imagen: `![descripción](/assets/...)`.

## Verificación

Antes de escribir un número, comprobarlo en el código o los datos del servidor (scripts Lua de NPCs y acciones, XML de monstruos e ítems, `config.lua`, `const76.h`), no solo en `docs/`. Los documentos internos a veces quedaron viejos. Si el código y la doc no coinciden, vale el código.
