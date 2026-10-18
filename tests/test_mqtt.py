"""Deterministic Lua 5.3 protocol, host-double and plugin-contract tests.

These checks do not emulate Q-SYS or certify MQTT conformance.
"""
from pathlib import Path
import hashlib
import subprocess
import json
import re
import sys
from lupa.lua53 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = (ROOT / "content/MqttClient.qplug").read_bytes()
VERSION = re.search(rb'\bVersion\s*=\s*"([^"]+)"', PLUGIN)[1]
# Exercise the engine embedded in the exact packaged plugin.
START, END = b"  Mqtt = (function()\n", b"\nend)()"
if PLUGIN.count(START) != 1 or PLUGIN.count(END) != 1:
    raise RuntimeError("Embedded engine boundaries changed; review the test loader")
ENGINE = PLUGIN.split(START, 1)[1].split(END, 1)[0]
FAKE = (ROOT / "tests/fake_host.lua").read_bytes()
RESULTS = []


def runtime():
    lua = LuaRuntime(unpack_returned_tuples=True, encoding=None)
    lua.execute(FAKE)
    lua.execute(b'''NativeRequire = require
require = function(name)
  assert(name ~= "socket" and name ~= "ssl" and name ~= "coroutine", "external dependency")
  return NativeRequire(name)
end''')
    lua.globals().Mqtt = lua.execute(ENGINE)
    return lua


CASES = {
    "host callback setters reject nil replacements": r'''
local socket=TcpSocket.New()
for _,name in ipairs({"Connected","Data","Closed","Error","Timeout","Reconnect"}) do
  socket[name]=function() end
  assert(not pcall(function() socket[name]=nil end))
  assert(type(socket[name])=="function")
end
local timer=Timer.New();timer.EventHandler=function() end
assert(not pcall(function() timer.EventHandler=nil end))
assert(type(timer.EventHandler)=="function")
''',
    "disconnect in failed-operation callback cancels reconnect": r'''
local c,s=Online()
c:Publish("a","b",1,false,function(self) self:Disconnect() end)
s.Error(s,"failed")
Advance(20)
assert(c.State=="Disconnected" and not c.Wanted and #Sockets==1 and not c.TickTimer.Running)
''',
    "trace-driven replacement connection survives old send continuation": r'''
for _,kind in ipairs({"CONNECT","SUBSCRIBE"}) do
  local c,s=Online()
  if kind=="SUBSCRIBE" then
    local _,id=c:Subscribe("a/#",1)
    s:Feed("\144\003" .. IdBytes(id) .. "\001")
  end
  local replaced=false
  c.OnTrace=function(self,dir,packet)
    if dir=="Tx" and packet==kind and not replaced then
      replaced=true
      self:Disconnect()
      self:Connect()
    end
  end
  s.Closed(s);Advance(1)
  s=Sockets[#Sockets];s:Open()
  if kind=="SUBSCRIBE" then s:Feed("\032\002\000\000") end
  assert(replaced and c.State=="Connecting" and Sockets[#Sockets].Connected)
end
''',
    "coalesced packets across incomplete varint read boundary": r'''
local c,s=Online()
local first=string.char(48,251,63,0,1)..'a'..string.rep('x',8184)
local second=string.char(48,128,1,0,1)..'b'..string.rep('y',125)
s:Feed(first .. second)
assert(#c.Messages==1 and s.BufferLength>0)
Advance(0.1)
assert(#c.Messages==2 and #c.Messages[2].Payload==125)
local c,s=Online()
s.ShortRead=2
s:Feed(second)
Advance(1)
assert(#c.Messages==1)
''',
    "trace callback disposal prevents post-disposal delivery": r'''
for _,direction in ipairs({"Tx","Rx"}) do
  local c,s=Online()
  c.OnTrace=function(self,dir,kind)
    if dir==direction then self:Dispose() end
  end
  s:Feed("\050\006\000\001a\000\001b")
  assert(c.Disposed and c.State=="Disconnected" and #c.Messages==0)
end
''',
    "disposal in failed operation callback cannot reconnect": r'''
local c,s=Online()
c:Publish("a","b",1,false,function(self) self:Dispose() end)
s.Closed(s)
Advance(20)
assert(c.Disposed and c.State=="Disconnected" and #Sockets==1 and not c.TickTimer.Running)
''',
    "async CONNECT and clean-session wire vector": r'''
local c,s = NewClient({KeepAlive=0})
assert(c.State == "Connecting" and #s.Writes == 0)
s:Open()
assert(s.Writes[1] == "\016\023\000\004MQTT\004\002\000\000\000\011test-client")
s:Feed("\032\002\000\000")
assert(c.State == "Connected")
''',
    "binary and empty QoS0 publishes": r'''
local c,s = Online()
local results = {}
assert(c:Publish("a/b", "x\000y", 0, true, function(_,ok,detail) results={ok,detail} end))
assert(s.Writes[2] == "\049\008\000\003a/bx\000y")
assert(results[1] and results[2] == "written-unacknowledged")
assert(c:Publish("a/b", "", 0, true))
assert(s.Writes[3] == "\049\005\000\003a/b")
''',
    "QoS1 waits for broker ACK and isolates duplicate ACK": r'''
local c,s = Online()
local calls=0
local ok,id=c:Publish("a/b","hi",1,false,function(_,success,detail)
  assert(success and detail == "broker-acknowledged"); calls=calls+1
end)
assert(ok and calls==0)
assert(s.Writes[2] == "\050\009\000\003a/b" .. IdBytes(id) .. "hi")
s:Feed(Ack(0x40,id)); s:Feed(Ack(0x40,id))
assert(calls==1 and c.PendingCount==0)
''',
    "every byte fragmentation and repeat messages": r'''
local c,s=Online()
local frame="\048\007\000\003a/bhi"
for i=1,#frame do s:Feed(frame:sub(i,i)); if i<#frame then assert(#c.Messages==0) end end
s:Feed(frame .. "\048\005\000\003a/b")
assert(#c.Messages==3 and c.Messages[1].Payload=="hi" and c.Messages[3].Payload=="")
''',
    "QoS1 receive and duplicate flag": r'''
local c,s=Online()
s:Feed("\058\009\000\003a/b\000\042hi")
assert(c.Messages[1].Duplicate and c.Messages[1].Qos==1)
assert(s.Writes[2]=="\064\002\000\042")
''',
    "burst work yields and resumes without another socket event": r'''
local c,s=Online()
s:Feed(string.rep("\048\007\000\003a/bhi",80))
assert(#c.Messages==16)
Advance(0.1)
assert(#c.Messages==80 and #c.Buffer==0)
''',
    "short socket reads continue from buffered bytes": r'''
local c,s=Online()
s.ShortRead=1
s:Feed("\048\007\000\003a/bhi")
Advance(0.5)
assert(#c.Messages==1 and c.Messages[1].Payload=="hi")
''',
    "subscribe refusal and unsubscribe acknowledgement": r'''
local c,s=Online()
local count=0
local ok,id=c:Subscribe("a/+",1,function(_,success) assert(not success);count=count+1 end)
assert(ok)
s:Feed("\144\003" .. IdBytes(id) .. "\128")
assert(count==1 and c.Subscriptions["a/+"]==nil)
ok,id=c:Subscribe("a/+",1)
s:Feed("\144\003" .. IdBytes(id) .. "\001")
local ok,id=c:Unsubscribe("a/+",function(_,success) assert(success);count=count+1 end)
assert(ok)
s:Feed(Ack(0xB0,id))
assert(count==2 and c.Subscriptions["a/+"]==nil)
''',
    "reconnect fails old callback once and restores subscriptions": r'''
local c,s=Online()
local calls={}
local ok,id=c:Subscribe("a/#",1,function(_,success) table.insert(calls,success) end)
local oldData=s.Data
s.Closed(s)
assert(c.State=="Reconnecting" and #calls==1 and calls[1]==false)
Advance(1)
local nextSocket=Sockets[#Sockets]
assert(nextSocket~=s)
nextSocket:Open();nextSocket:Feed("\032\002\000\000")
assert(nextSocket.Writes[2]:byte()==0x82)
local newId=c.NextId
nextSocket:Feed("\144\003" .. IdBytes(newId) .. "\001")
oldData(s)
assert(#calls==1 and c.State=="Connected" and c.PendingCount==0)
''',
    "zero keepalive sends no pings": r'''
local c,s=Online({KeepAlive=0})
Advance(100)
assert(#s.Writes==1 and c.State=="Connected")
''',
    "PINGRESP watchdog independent of other received traffic": r'''
local c,s=Online({KeepAlive=4,Timeout=2})
Advance(3)
assert(s.Writes[2]=="\192\000")
s:Feed("\048\007\000\003a/bhi")
Advance(2)
assert(c.State=="Reconnecting")
''',
    "PINGRESP clears outstanding ping": r'''
local c,s=Online({KeepAlive=4,Timeout=2})
Advance(3);s:Feed("\208\000");Advance(2)
assert(c.State=="Connected" and not c.PingAt)
''',
    "CONNACK and transport deadline": r'''
local c,s=NewClient({Timeout=1})
Advance(1);assert(c.State=="Reconnecting")
Advance(1);s=Sockets[#Sockets];s:Open();Advance(1)
assert(c.State=="Reconnecting")
''',
    "ACK timeout produces unconfirmed and never replays publish": r'''
local c,s=Online({Timeout=1})
local calls=0
c:Publish("a","command",1,false,function(_,ok,detail)
  assert(not ok and detail:find("unconfirmed")); calls=calls+1
end)
Advance(1);assert(c.State=="Reconnecting" and calls==1)
Advance(1);s=Sockets[#Sockets];s:Open();s:Feed("\032\002\000\000")
assert(#s.Writes==1)
''',
    "explicit disconnect stops reconnect and retires handlers": r'''
local c,s=Online()
c:Disconnect()
assert(s.Writes[#s.Writes]=="\224\000")
assert(not s.IsConnected and not c.TickTimer.Running)
s.Data(s);s.Error(s,"retired");s.Closed(s)
assert(c.State=="Disconnected" and #c.Messages==0)
Advance(100);assert(#Sockets==1)
c:Dispose();c.TickTimer.EventHandler();c.WorkTimer.EventHandler()
assert(not c.TickTimer.Running and not c.WorkTimer.Running)
assert(not c:Connect())
''',
    "native TLS fails closed without CA and enables validation": r'''
local c,reason=Mqtt.New({Host="test",ClientId="a",Tls=true})
assert(not c and reason=="ca-certificate-required")
local c,s=NewClient({Tls=true,CaCertificate="-----BEGIN CERTIFICATE-----fixture-----END CERTIFICATE-----",Username="user",Password="secret"})
assert(s.Tls and s.ValidateCertificate==true and s.CACertData=="-----BEGIN CERTIFICATE-----fixture-----END CERTIFICATE-----" and s.Port==8883)
''',
    "Last Will and credentials flags": r'''
local c,s=NewClient({Username="u",Password="p",KeepAlive=0,
  Will={Topic="status",Payload="offline",Qos=1,Retain=true}})
s:Open()
assert(s.Writes[1]:byte(10)==0xEE)
assert(s.Writes[1]:find("\000\006status\000\007offline\000\001u\000\001p",1,true))
''',
    "topic validation and wildcard semantics": r'''
local matches=Mqtt.TopicMatches
assert(matches("a/#","a") and matches("a/+","a/") and matches("+/b","a/b"))
assert(not matches("#","$SYS/a") and matches("$SYS/#","$SYS/a"))
assert(not matches("a/+","a") and not matches("a/#/b","a/x/b"))
assert(not matches("a+","a") and not matches("a\000","a"))
local c=Online()
for _,topic in ipairs({"", "a+", "a#", "a\000", "\192\128", "\237\160\128", "\244\144\128\128"}) do
  assert(not c:Publish(topic,"",0,false))
end
assert(c:Publish("\195\169", "",0,false))
assert(not c:Publish("a","",2,false))
''',
    "packet and inflight bounds": r'''
local c,s=Online({MaxPacketBytes=128,MaxInflight=32})
assert(not c:Publish("a",string.rep("x",128),0,false))
for i=1,32 do assert(c:Publish("a","",1,false)) end
assert(not c:Publish("a","",1,false))
s:Feed(string.rep("x",257));assert(c.State=="Reconnecting")
''',
    "packet ID wrap avoids outstanding identifiers": r'''
local c,s=Online()
local _,first=c:Publish("a","",1,false)
c.NextId=65535
local _,second=c:Publish("a","",1,false)
assert(first==1 and second==2)
''',
    "malformed packet rejection": r'''
local bad={
  "\054\007\000\001a\000\001hi", -- reserved QoS3
  "\056\003\000\001a", -- DUP QoS0
  "\048\003\000\001#", -- wildcard topic name
  "\050\005\000\001a\000\000", -- zero packet id
  "\064\002\000\000", -- zero PUBACK id
  "\192\000", -- server PINGREQ
  "\208\128\000", -- nonminimal remaining length
  "\048\255\255\255\255", -- too long remaining length
  "\032\002\000\000", -- second CONNACK
}
for _,frame in ipairs(bad) do
  local c,s=Online();s:Feed(frame);assert(c.State=="Reconnecting", "accepted malformed frame")
end
''',
    "incomplete packet deadline": r'''
local c,s=Online({Timeout=1})
s:Feed("\048\007\000")
Advance(1)
assert(c.State=="Reconnecting")
''',
    "callback exceptions cannot crash parser or expose data": r'''
local c,s=Online()
c.OnMessage=function() error("secret") end
s:Feed("\048\007\000\003a/bhi")
assert(c.State=="Connected" and c.Errors[1]=="callback-error")
''',
    "disconnect in message callback stops processing old stream": r'''
local c,s=Online()
local count=0
c.OnMessage=function(self) count=count+1;self:Disconnect() end
s:Feed(string.rep("\048\007\000\003a/bhi",3))
assert(count==1 and c.State=="Disconnected")
''',
    "socket error and Timeout reset without Closed": r'''
for _,event in ipairs({"Error","Timeout"}) do
  local c,s=Online();s:Feed("\048\007")
  s[event](s,"sensitive error")
  assert(c.State=="Reconnecting" and c.Buffer=="")
  s.Data(s);assert(c.State=="Reconnecting" and #c.Messages==0)
end
''',
    "CONNACK reserved flags and clean-session constraint": r'''
for _,frame in ipairs({"\032\002\002\000","\032\002\001\000","\032\002\000\006"}) do
  local c,s=NewClient();s:Open();s:Feed(frame);assert(c.State=="Reconnecting")
end
''',
    "independent clients retain separate state": r'''
local a,sa=Online({ClientId="a"})
local b,sb=Online({ClientId="b"})
sa:Feed("\048\007\000\003a/bhi")
assert(#a.Messages==1 and #b.Messages==0)
a:Dispose();assert(b.State=="Connected" and sb.IsConnected)
''',
}


def check_case(name, source):
    lua = runtime()
    lua.execute(source.encode())
    RESULTS.append(name)


def design(channels):
    lua = runtime()
    lua.execute(PLUGIN)
    g = lua.globals()
    props = lua.table()
    for _, item in g.GetProperties().items():
        props[item.Name] = lua.table_from({b"Value": item.Value})
    props.Channels.Value = channels
    return lua, g, props


def rect(item):
    x, y = item.Position[1], item.Position[2]
    return x, y, x + item.Size[1], y + item.Size[2]


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def validate_layout(layout, graphics, definitions, page, certificate_page=False):
    assert set(layout.keys()) == set(definitions)
    for item in layout.values():
        if item.Style == b"None":
            assert set(item.keys()) <= {b"Style", b"Position", b"Size", b"PrettyName", b"ZOrder"}, "hidden visual fields"
    visible = [v for v in layout.values() if v.Style != b"None"]
    graphics = list(graphics.values())
    orders = [v.ZOrder for v in graphics + list(layout.values())]
    assert len(set(orders)) == len(orders) and None not in orders, "duplicate/missing order"
    captions = {v.Text for v in graphics if v.Type in (b"Label", b"Header")}
    expected = ({b"Connection", b"Last Will (optional)", b"Broker address", b"Unique client ID", b"Status"}
                if page == 1 else {b"Publish", b"Subscribe", b"Topic filter", b"Received payload", b"Message event"})
    if certificate_page:
        expected = {b"Broker trust", b"Client identity (mutual TLS)", b"CA file path", b"Private key file"}
    assert expected <= captions, "missing caption"
    assert b"Version " + VERSION in captions
    assert (b"Setup" if page == 1 else (b"Certificates" if certificate_page else f"Channel {page - 1}".encode())) in captions
    logos = [v for v in graphics if v.Type == b"Svg"]
    assert len(logos) == 1, "missing logo"
    logo = logos[0]
    assert abs(logo.Size[1] / logo.Size[2] - 1100 / 280) < 1e-9
    assert tuple(logo.Position.values()) == (12.5, 25 / 11)
    import base64
    assert b'viewBox="0 0 1100 280"' in base64.b64decode(logo.Image)
    assert b'fill="#606"' in base64.b64decode(logo.Image)
    height = 755 if page == 1 else (475 if certificate_page else 640)
    for item in visible + graphics:
        x, y, right, bottom = rect(item)
        assert 0 <= x < right <= 400 and 0 <= y < bottom <= height
    for index, item in enumerate(visible):
        assert item.TextColor is None and item.OffColor is None and item.UnlinkOffColor is None
        assert item.PrettyName
        assert item.PrettyName.split(b"~")[-1] in captions, "missing control label"
        if item.Style == b"Led":
            assert tuple(item.Color.values()) == (0, 159, 60), "LED must explicitly confirm OK in green"
        if item.Style == b"Button":
            assert item.ButtonStyle in (b"Toggle", b"Trigger")
            assert item.Margin == 2 and item.CornerRadius == 2
        for other in visible[index + 1:]:
            assert not overlaps(rect(item), rect(other)), "overlapping controls"
        for graphic in graphics:
            if graphic.Type in (b"Label", b"Header"):
                assert not overlaps(rect(item), rect(graphic)), "control covers label"
    for i, background in enumerate(graphics):
        if background.Type != b"GroupBox":
            continue
        for foreground in graphics[i + 1:] + visible:
            if overlaps(rect(background), rect(foreground)):
                assert foreground.ZOrder > background.ZOrder


def plugin_tests():
    for channels in range(1, 9):
        lua, g, props = design(channels)
        definitions = {v.Name: v for v in g.GetControls(props).values()}
        assert len(definitions) == len(g.GetControls(props))
        assert [v.name for v in g.GetPages(props).values()] == [b"Setup"] + [f"Channel {n}".encode() for n in range(1, channels + 1)] + [b"Certificates"]
        assert tuple(g.GetColor(props).values()) == (102, 0, 102)
        for page in range(1, channels + 3):
            props.page_index = lua.table_from({b"Value": page})
            layout, graphics = g.GetControlLayout(props)
            validate_layout(layout, graphics, definitions, page, page == channels + 2)
        RESULTS.append(f"layout/contracts all {channels + 2} pages with {channels} channels")
    lua, g, props = design(1)
    props.page_index = lua.table_from({b"Value": 1})
    layout, graphics = g.GetControlLayout(props)
    definitions = {v.Name: v for v in g.GetControls(props).values()}
    graphics[3].ZOrder = graphics[4].ZOrder
    try:
        validate_layout(layout, graphics, definitions, 1)
    except AssertionError as exc:
        assert str(exc) == "duplicate/missing order"
    else:
        raise AssertionError("layout validator accepted duplicate order")
    layout, graphics = g.GetControlLayout(props)
    for item in graphics.values():
        if item.Text == b"Connection":
            item.Text = b"Removed"
    try:
        validate_layout(layout, graphics, definitions, 1)
    except AssertionError as exc:
        assert str(exc) == "missing caption"
    else:
        raise AssertionError("layout validator accepted missing caption")
    RESULTS.append("layout negative mutations reject duplicate order and missing heading")
    layout, graphics = g.GetControlLayout(props)
    for item in graphics.values():
        if item.Text == b"Password":
            item.Text = b"Removed"
    try:
        validate_layout(layout, graphics, definitions, 1)
    except AssertionError as exc:
        assert str(exc) == "missing control label"
    else:
        raise AssertionError("layout validator accepted missing Password label")
    RESULTS.append("layout negative mutation rejects removed per-control label")
    layout, graphics = g.GetControlLayout(props)
    next(item for item in layout.values() if item.Style == b"None").ZOrder = None
    try:
        validate_layout(layout, graphics, definitions, 1)
    except AssertionError as exc:
        assert str(exc) == "duplicate/missing order"
    else:
        raise AssertionError("layout validator accepted missing hidden-control order")
    RESULTS.append("layout rejects missing hidden-control order")
    layout, graphics = g.GetControlLayout(props)
    next(item for item in layout.values() if item.Style == b"None").ButtonStyle = b"Trigger"
    try:
        validate_layout(layout, graphics, definitions, 1)
    except AssertionError as exc:
        assert str(exc) == "hidden visual fields"
    else:
        raise AssertionError("layout validator accepted hidden button styling")
    RESULTS.append("layout rejects hidden button styling")
    g.Properties = props
    lua.execute(b'''
Controls = {}
for _,def in ipairs(GetControls(Properties)) do
  Controls[def.Name] = {String=type(def.DefaultValue)=="string" and def.DefaultValue or "",
    Value=type(def.DefaultValue)=="number" and def.DefaultValue or 0,
    Boolean=def.DefaultValue==true, TriggerCount=0,
    Trigger=function(self) self.TriggerCount=self.TriggerCount+1 end}
end
setmetatable(Controls,{__index=function(_,name) error("undeclared control: " .. name) end})
SecretStorage = {["text.1"]={String="old-secret"}}
''')
    lua.execute(PLUGIN)
    lua.execute(b'''
assert(#Sockets==0 and Controls.Password.String=="********")
Controls.Password.String="new-secret"
Controls.Password.EventHandler(Controls.Password)
assert(SecretStorage["text.1"].String=="new-secret" and Controls.Password.String=="********")
Controls.Username.String="user"
Controls.IPAddress.String="local-broker"
Controls.ClientId.String="plugin-test"
Controls.SubscribeFilter1.String="a/#"
Controls.SubscribeQos1.String="1"
Controls.Enable.Boolean=true
Controls.Enable.EventHandler()
assert(Controls.Status.Value==5 and Controls.Status.String:find("Connecting",1,true))
local s=Sockets[#Sockets]
s:Open();s:Feed("\\032\\002\\000\\000")
assert(Controls.Connected.Boolean and s.Writes[2]:byte()==0x82)
assert(Controls.Status.Value==0)
s:Feed("\\144\\003" .. IdBytes(MqttClient.NextId) .. "\\001")
assert(Controls.Subscribed1.Boolean)
s:Feed(string.rep("\\048\\007\\000\\003a/bhi",2))
assert(Controls.MessageReceived1.TriggerCount==2 and Controls.MessageCount1.Value==2)
assert(Controls.ReceivedPayload1.String=="hi" and Controls.ReceivedValid1.Boolean)
Controls.PublishTopic1.String="command"
Controls.PublishPayload1.String="go"
Controls.Publish1.EventHandler()
assert(Controls.PublishResult1.String:find("written%-unacknowledged"))
local text,format=DisplayPayload("a\\000b")
assert(text=="610062" and format=="Hex")
s.Error(s,"test-connection-fault")
assert(Controls.Status.Value==2 and not Controls.Connected.Boolean)
assert(Controls.Status.String:find("Reconnecting",1,true))
Advance(1.1)
assert(Controls.Status.Value==5)
local retry=Sockets[#Sockets]
retry:Open();retry:Feed("\\032\\002\\000\\000")
assert(Controls.Status.Value==0 and Controls.Connected.Boolean)
MqttClient:Disconnect()
assert(Controls.Status.Value==3 and Controls.Status.String=="Disconnected: requested")
Controls.Enable.Boolean=false;Controls.Enable.EventHandler()
assert(not Controls.ReceivedValid1.Boolean and Controls.ReceivedPayload1.String=="")
assert(not Controls.Connected.Boolean and Controls.Status.String=="Disabled")
assert(Controls.Status.Value==3)
Controls.Username.String=""
Controls.Enable.Boolean=true;Controls.Enable.EventHandler()
assert(Controls.Status.Value==2 and Controls.Status.String=="Password requires username")
for _,line in ipairs(Logs) do assert(not line:find("new-secret",1,true)) end
''')
    RESULTS.append("plugin runtime, password, subscriptions, repeated message events and commands")


def main():
    for name, source in CASES.items():
        try:
            check_case(name, source)
        except Exception:
            print("FAILED:", name, file=sys.stderr)
            raise
    plugin_tests()
    subprocess.run([sys.executable, str(ROOT / "scripts/verify.py")], check=True)
    RESULTS.append("packaged plugin source integrity")
    report = {"scope": "Stock Lua 5.3, fake host objects; no Designer/Core acceptance",
              "engine_sha256": hashlib.sha256(ENGINE).hexdigest(),
              "plugin_sha256": hashlib.sha256(PLUGIN).hexdigest(), "checks": RESULTS}
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(RESULTS)} test groups (including all 52 channel/page combinations)")


if __name__ == "__main__":
    main()
