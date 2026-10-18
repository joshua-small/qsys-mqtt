-- Deterministic host double, not a Q-SYS emulator.
Clock = 0
Timers = {}
Sockets = {}
Logs = {}
print = function(...) table.insert(Logs, table.concat({...}, " ")) end
-- Native Q-SYS callback setters reject nil. Keep handlers outside the table so
-- every assignment passes through __newindex, including replacements.
local function WithCallbacks(object, names)
  local callbacks = {}
  return setmetatable(object, {
    __index = function(_, key) return callbacks[key] end,
    __newindex = function(self, key, value)
      if names[key] then
        assert(type(value) == "function", "bad argument for callback (function expected)")
        callbacks[key] = value
      else
        rawset(self, key, value)
      end
    end,
  })
end
Timer = {}
function Timer.Now() return Clock end
function Timer.New()
  local timer = WithCallbacks({ Running = false }, { EventHandler = true })
  function timer:Start(period)
    self.Running = true
    self.Period = period
    self.Due = Clock + period
  end
  function timer:Stop() self.Running = false end
  function timer:IsRunning() return self.Running end
  table.insert(Timers, timer)
  return timer
end
function Advance(seconds)
  local target = Clock + seconds
  local steps = 0
  while true do
    local chosen
    for _, timer in ipairs(Timers) do
      if timer.Running and timer.Due <= target and (not chosen or timer.Due < chosen.Due) then
        chosen = timer
      end
    end
    if not chosen then break end
    Clock = chosen.Due
    chosen.Due = Clock + chosen.Period
    if chosen.EventHandler then chosen.EventHandler(chosen) end
    steps = steps + 1
    assert(steps < 100000, "timer loop")
  end
  Clock = target
end
TcpSocket = {}
function TcpSocket.New()
  local socket = WithCallbacks({ IsConnected = false, BufferLength = 0, Input = "", Writes = {} },
    {Connected=true, Data=true, Closed=true, Error=true, Timeout=true, Reconnect=true, EventHandler=true})
  function socket:Connect(host, port) self.Host = host; self.Port = port end
  function socket:Disconnect() self.IsConnected = false end
  function socket:Write(data)
    assert(self.IsConnected, "write before Connected")
    if self.FailWrite then error("secret-containing transport error") end
    table.insert(self.Writes, data)
  end
  function socket:Read(count)
    count = math.min(count, self.ShortRead or count)
    local data = self.Input:sub(1, count)
    self.Input = self.Input:sub(#data + 1)
    self.BufferLength = #self.Input
    return data
  end
  function socket:Open()
    self.IsConnected = true
    self.Connected(self)
  end
  function socket:Feed(data)
    self.Input = self.Input .. data
    self.BufferLength = #self.Input
    if self.Data then self.Data(self) end
  end
  table.insert(Sockets, socket)
  return socket
end
function TcpSocket.NewTls()
  local socket = TcpSocket.New()
  socket.Tls = true
  return socket
end
function NewClient(options)
  options = options or {}
  options.Host = options.Host or "test.invalid"
  options.ClientId = options.ClientId or "test-client"
  local client = assert(Mqtt.New(options))
  client.Messages = {}
  client.States = {}
  client.Errors = {}
  client.OnMessage = function(self, message) table.insert(self.Messages, message) end
  client.OnState = function(self, state, reason) table.insert(self.States, {state, reason}) end
  client.OnError = function(self, errorCode) table.insert(self.Errors, errorCode) end
  assert(client:Connect())
  return client, Sockets[#Sockets]
end
function Online(options)
  local client, socket = NewClient(options)
  assert(#socket.Writes == 0)
  socket:Open()
  assert(socket.Writes[1]:byte() == 0x10)
  socket:Feed("\032\002\000\000")
  assert(client.State == "Connected")
  return client, socket
end
function IdBytes(id) return string.char(math.floor(id / 256), id % 256) end
function Ack(kind, id) return string.char(kind, 2) .. IdBytes(id) end
