-- Chispas de la forja: abanico corto de fuego, sin campos persistentes.
local area = {
    {0, 1, 1, 1, 0},
    {2, 0, 1, 0, 3},
    {2, 2, 0, 3, 3},
    {2, 0, 4, 0, 3},
    {0, 4, 4, 4, 0},
}
local damage = MagicDamageObject(ATTACK_FIRE, NM_ANI_NONE, NM_ME_HITBY_FIRE,
    NM_ME_HITBY_FIRE, ORANGE, true, false, 35, 65)

function onCast(cid, creaturePos, level, maglv, var)
    local center = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    return doAreaMagic(cid, center, true, NM_ME_FIRE_AREA, area, damage:ordered())
end
