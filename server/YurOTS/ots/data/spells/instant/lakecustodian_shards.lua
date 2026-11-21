-- Astillas de piedra cristalizada: abanico corto orientado al objetivo.
local area = {
    {0, 1, 1, 1, 0},
    {2, 0, 1, 0, 3},
    {2, 2, 0, 3, 3},
    {2, 0, 4, 0, 3},
    {0, 4, 4, 4, 0},
}
local damage = MagicDamageObject(ATTACK_PHYSICAL, NM_ANI_NONE, NM_ME_ICE_AREA,
    NM_ME_ICE_SHATTER, LIGHT_BLUE, true, false, 60, 110)

function onCast(cid, creaturePos, level, maglv, var)
    local center = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    return doAreaMagic(cid, center, true, NM_ME_ICE_AREA, area, damage:ordered())
end
