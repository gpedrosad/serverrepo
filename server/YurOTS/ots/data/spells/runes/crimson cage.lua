-- Crimson Cage Rune (20273)
-- Se tira sobre una criatura: paredes rojas en las 8 casillas de alrededor durante 3 segundos.
-- La logica (casillas validas, timer de 3 s, PvP) esta en C++: doCrimsonCage en source/spells.cpp.
-- Doc: docs/gameplay/CRIMSON_CAGE_RUNE.md

function onCast(cid, creaturePos, level, maglv, var)
	centerpos = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
	return doCrimsonCage(cid, centerpos)
end
