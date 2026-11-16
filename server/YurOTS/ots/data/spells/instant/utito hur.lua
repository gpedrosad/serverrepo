-- Frenzy (utito hur), Knight: golpes cuerpo a cuerpo más rápidos durante DURACION segundos.
--
-- La espera entre golpes baja PORCENTAJE % (con la base de 1333 ms: 800 ms). Se suma a las gemas y armas
-- rápidas y nunca baja de 500 ms. Se puede volver a lanzar a los ESPERA segundos (si no, no gasta maná).
-- Estos números se ajustan acá sin recompilar. La lógica está en spells.cpp (startAttackSpeed) y
-- player.cpp (getAttackDelayMs). Doc: docs/gameplay/SPELL_ATTACK_SPEED.md.

DURACION = 6
PORCENTAJE = 40
ESPERA = 20
EFECTO = NM_ME_MAGIC_BLOOD   -- cada segundo sobre el jugador mientras dura (NM_ME_NONE = ninguno)

attackType = ATTACK_NONE
animationEffect = NM_ANI_NONE
hitEffect = NM_ME_NONE
damageEffect = NM_ME_SOUND_RED
animationColor = RED
offensive = false
drawblood = false

BuffObject = MagicDamageObject(attackType, animationEffect, hitEffect, damageEffect, animationColor, offensive, drawblood, 0, 0)

function onCast(cid, creaturePos, level, maglv, var)
	if attackSpeedReady(cid) > 0 then
		return false
	end
	local centerpos = {x = creaturePos.x, y = creaturePos.y, z = creaturePos.z}
	local ret = doTargetMagic(cid, centerpos, BuffObject:ordered())
	if ret then
		startAttackSpeed(cid, DURACION, PORCENTAJE, ESPERA, EFECTO)
	end
	return ret
end
