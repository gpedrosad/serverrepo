-- Root Colossus: nube de esporas cercana (radio 1), dano de veneno inmediato.
local area = {
    {1, 1, 1},
    {1, 0, 1},
    {1, 1, 1},
}
local damage = MagicDamageObject(ATTACK_POISON, NM_ANI_NONE, NM_ME_POISEN_RINGS,
    NM_ME_POISEN_RINGS, GREEN, true, false, 50, 90)

function onCast(cid, creaturePos, level, maglv, var)
    local center = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    return doAreaMagic(cid, center, false, NM_ME_POISONCLOUD, area, damage:ordered())
end
