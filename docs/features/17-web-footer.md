# Web: footer en pixel art del centro de Chillán

Al final de cada página de retro76.cl (layout `web/site/src/layouts/Base.astro`) hay una escena pixel-art del centro de
Chillán: la Catedral, la Cruz Monumental, la Plaza de Armas con el monumento a O'Higgins y la
cordillera. Reemplaza al footer de texto que se sacó en nov 2026.

Viene del proyecto "laboratorio" (`~/proyectos/footer-endless`, fuera de este repo): el arte lo
genera `tools/gen-chillan.py` allá.

| Archivo | Qué es |
|---|---|
| `web/assets/footer/chillan-day.png`, `chillan-night.png` | Arte de día y de noche (415×137, se escala con `image-rendering: pixelated`) |
| `web/assets/footer/chillan-map.png` | Mapa por píxel: capa de profundidad (R), animación (G) y grupo de luz (B) |
| `web/assets/footer/chillan-footer.js` | Animación: 4 canvas apilados, parallax al hacer scroll, loop a 8 fps |
| `web/site/src/layouts/Base.astro`, `web/site/src/styles/site.css` | `<footer class="chillan-scene">` y su CSS |

**Cómo se comporta**
- **Día o noche según la hora del visitante:** noche de 20:00 a 7:00. Si la página queda abierta,
  cambia sola al pasar la hora.
- **De día:** viento en los árboles, gente caminando, un perro, palomas que vuelan cuando alguien
  pasa y una bandada que cruza el cielo. El cielo del arte es transparente, así que el footer
  le pone un degradé celeste que nace del fondo oscuro de la página.
- **De noche:** ventanas que se prenden y apagan, faroles (uno parpadea), estrellas y la cruz
  encendida.
- El loop solo corre mientras el footer está en pantalla y la pestaña está visible.
- Con `prefers-reduced-motion` no hay parallax ni loop: se pinta un solo cuadro.
- Sin JavaScript queda la imagen fija.

Para cambiar el arte: regenerarlo en el laboratorio y copiar los tres PNG a `web/assets/footer/`
(el mapa tiene que corresponder al arte, píxel a píxel).
