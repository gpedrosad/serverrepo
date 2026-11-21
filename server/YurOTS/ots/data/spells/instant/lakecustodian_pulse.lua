-- Custodio: pulso del nucleo, radio 2 con esquinas recortadas; dano inmediato.
local area = {
    {0, 1, 1, 1, 0},
    {1, 1, 1, 1, 1},
    {1, 1, 0, 1, 1},
    {1, 1, 1, 1, 1},
    {0, 1, 1, 1, 0},
}
local damage = MagicDamageObject(ATTACK_ENERGY, NM_ANI_NONE, NM_ME_ENERGY_DAMAGE,
    NM_ME_ENERGY_DAMAGE, LIGHT_BLUE, true, false, 75, 130)

function onCast(cid, creaturePos, level, maglv, var)
    local center = {x=creaturePos.x, y=creaturePos.y, z=creaturePos.z}
    return doAreaMagic(cid, center, false, NM_ME_ENERGY_AREA, area, damage:ordered())
end
