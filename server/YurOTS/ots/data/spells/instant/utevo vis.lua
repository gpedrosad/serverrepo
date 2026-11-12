-- Eco (utevo vis), Sorcerer: el próximo golpe a un blanco se repite solo, más débil.
--
-- Al lanzarlo, el Eco queda activo VENTANA segundos. El primer hechizo marcado con echo="1" en
-- spells.xml (golpes a un blanco: exori flam / vis / mort / frigo / san, exori vis hur) que salga bien en
-- ese tiempo se repite 1 s después contra el mismo blanco, al ESCALA del daño (ESCALA_PVP si el blanco es un
-- jugador), sin maná ni espera. Si cambiaste de blanco o quedó fuera de alcance, el eco se pierde.
-- Nunca repite áreas, runas, curaciones ni otro Eco. Se puede volver a lanzar a los ESPERA segundos.
-- Estos números se ajustan acá sin recompilar. La lógica está en spells.cpp (startEcho, castEcho).
-- Doc: docs/gameplay/SPELL_ECO.md.

VENTANA = 6
ESPERA = 25
ESCALA = 0.5
ESCALA_PVP = 0.25

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_SOUND_PURPLE
animationColor = LIGHT_BLUE
offensive = false
drawblood = false

EchoObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	if echoReady(cid) > 0 then
		return false
	end
	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, EchoObject:ordered())
	if ret then
		startEcho(cid, VENTANA, ESPERA, ESCALA, ESCALA_PVP)
	end
	return ret
end
