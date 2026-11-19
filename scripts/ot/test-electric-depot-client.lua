-- Solo para fixture de QA en 7278; nunca ejecutarlo contra 7171.
g_resources.makeDir('/settings/')
local finished = false
local function finish(ok, detail)
  if finished then return end
  finished = true
  print((ok and 'DEPOT_QA_PASS: ' or 'DEPOT_QA_FAIL: ') .. detail)
  if g_game.isOnline() then g_game.safeLogout() end
  scheduleEvent(function() g_app.exit() end, 1000)
end
connect(Container, { onOpen = function(container)
  for slot = 0, container:getCapacity() - 1 do
    local item = container:getItem(slot)
    -- crystal coin server 2160 -> client 3043 (comprobado contra el OTB).
    if item and item:getId() == 3043 and item:getCount() == 7 then
      finish(true, 'locker 129,58,6: se ven las 7 crystal coins guardadas en depotid=1')
      return
    end
  end
  finish(false, 'el locker no mostró los objetos guardados')
end })
connect(g_game, { onGameStart = function()
  scheduleEvent(function()
    local player = g_game.getLocalPlayer()
    if player:getSkull() ~= 7 or getSkullImagePath(7) ~= '/images/game/skulls/skull_cyan' then
      finish(false, 'el estado punitivo 7 no resuelve a la calavera cian')
      return
    end
    g_textures.preload('/images/game/skulls/skull_cyan')
    print('SKULL_QA_PASS: estado 7 recibido; textura cian cargada por el cliente real')
    local tile = g_map.getTile({x=129,y=58,z=6})
    if tile then
      for _, item in ipairs(tile:getItems()) do
        if item:getId() == 3497 then
          print('DEPOT_QA: abriendo locker real con cliente 760')
          g_game.open(item)
          return
        end
      end
    end
    finish(false, 'no se recibió el locker en el mapa')
  end, 700)
end, onLoginError = function(message) finish(false, tostring(message)) end })
g_game.setClientVersion(760)
g_game.setProtocolVersion(760)
g_game.setCustomOs(2)
g_game.loginWorld('111111', 'asantest', 'Depot QA', '192.168.1.17', 7278, 'Bot Knight', '', '')
scheduleEvent(function() finish(false, 'timeout de login o contenedor') end, 20000)
