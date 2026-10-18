"""Certificate sources and lifecycle; fake Q-SYS transport, no native TLS claim."""
from test_mqtt import runtime, design, PLUGIN

SETUP = r"""
-- Placeholder payload decodes to "fake"; these are not cryptographic credentials.
local function fake_pem(kind)
  return "-----BEGIN " .. kind .. "-----\nZmFrZQ==\n-----END " .. kind .. "-----\n"
end
Cert = fake_pem("CERTIFICATE")
Key = fake_pem("PRIVATE KEY")
Files = { ["media/ca.pem"]=Cert, ["media/client.pem"]=Cert, ["media/client.key"]=Key }
Reads, Closes = 0, 0
io.open = function(path,mode)
  assert(mode=="rb")
  if not Files[path] then return nil, "private diagnostic: " .. path end
  return {
    read=function(_,limit)
      Reads=Reads+1; assert(limit==131073)
      if ReadFailure then error("private key leak") end
      return Files[path]:sub(1,limit)
    end,
    close=function() Closes=Closes+1; return not CloseFailure end,
  }
end
function Make(extra)
  local o={Host="localhost",ClientId="tls-test",Tls=true,CaCertificateFile="media/ca.pem"}
  for k,v in pairs(extra or {}) do o[k]=v end
  return Mqtt.New(o)
end
function Started(extra)
  local c=assert(Make(extra));c.Reasons={}
  c.OnState=function(self,_,reason) table.insert(self.Reasons,reason) end
  assert(c:Connect());return c,Sockets[#Sockets]
end
"""
CASES={
"credential setup preserves trust when native setters reset TLS state":r"""
-- Conservative model of the Designer regression, not an assertion about
-- Q-SYS internals: credential setters invalidate earlier trust configuration.
local original=TcpSocket.NewTls
TcpSocket.NewTls=function()
 local socket=original();local base=getmetatable(socket);local fields={}
 local tls={ClientCertData=true,ClientKeyData=true,CACertData=true,ValidateCertificate=true}
 setmetatable(socket,{
  __index=function(o,k) if tls[k] then return fields[k] end return base.__index(o,k) end,
  __newindex=function(o,k,v)
   if not tls[k] then return base.__newindex(o,k,v) end
   if k~="ValidateCertificate" then fields.ValidateCertificate=false end
   if k=="ClientCertData" or k=="ClientKeyData" then fields.CACertData=nil end
   fields[k]=v
  end,
 })
 return socket
end
for _,identity in ipairs({{}, {ClientCertificateFile="media/client.pem",ClientKeyFile="media/client.key"}}) do
 local c,s=Started(identity)
 assert(s.ValidateCertificate==true and s.CACertData==Cert)
 s.Closed(s);Advance(1);local next=Sockets[#Sockets]
 assert(next~=s and next.ValidateCertificate==true and next.CACertData==Cert)
 c:Dispose()
end
""",
"file trust is validated before connect":r"""
local c,s=Started();assert(s.ValidateCertificate and s.CACertData==Cert and Reads==1 and Closes==1)
assert(not s.ClientCertData and not s.ClientKeyData)
""",
"mutual TLS binds the certificate and key":r"""
local c,s=Started({ClientCertificateFile="media/client.pem",ClientKeyFile="media/client.key"})
assert(s.ClientCertData==Cert and s.ClientKeyData==Key and s.ValidateCertificate)
assert(Reads==3 and Closes==3 and c.Options.ClientKey==nil)
""",
"inline data remains supported":r"""
local c=assert(Mqtt.New({Host="localhost",ClientId="inline",Tls=true,CaCertificate=Cert,
 ClientCertificate=Cert,ClientKey=Key}));c:Connect()
assert(Sockets[1].ClientKeyData==Key and Reads==0)
""",
"client identity rotation is reread with unchanged CA":r"""
local c,s=Started({ClientCertificateFile="media/client.pem",ClientKeyFile="media/client.key"})
s:Open();s:Feed("\032\002\000\000");s.Closed(s)
Files["media/client.key"]=Key.."\n"
Advance(1);local next=Sockets[#Sockets]
assert(next~=s and next.CACertData==Cert and next.ClientKeyData==Key.."\n" and Reads==6)
""",
"CA file rotation stops before creating another native socket":r"""
local c,s=Started();s:Open();s:Feed("\032\002\000\000");s.Closed(s)
Files["media/ca.pem"]=Cert..Cert;Advance(1)
assert(#Sockets==1 and c.Socket==nil and c.State=="Disconnected" and not c.Wanted)
assert(c.Reasons[#c.Reasons]=="ca-change-requires-runtime-restart")
Advance(60);assert(#Sockets==1)
-- Reverting the file, reconnecting and replacing the client cannot clear the latch.
Files["media/ca.pem"]=Cert;c:Connect();assert(#Sockets==1);c:Dispose()
local fresh=Started();assert(#Sockets==1 and fresh.Reasons[1]=="ca-change-requires-runtime-restart")
""",
"failed first connection still pins its CA across client replacement":r"""
local c,s=Started();s.Error(s);c:Dispose()
local other=assert(Mqtt.New({Host="localhost",ClientId="other",Tls=true,CaCertificate=Cert..Cert}))
other:Connect();assert(#Sockets==1 and other.State=="Disconnected")
""",
"missing file closes without socket or inline fallback":r"""
Files["media/ca.pem"]=nil;local c=Started()
assert(#Sockets==0 and c.State=="Reconnecting" and c.Reasons[1]=="ca-file-open-failed")
Files["media/ca.pem"]=Cert;Advance(1);assert(#Sockets==1)
""",
"file limits and empty data fail closed with handle cleanup":r"""
for _,case in ipairs({{"", "ca-file-empty"},{string.rep("x",131073),"ca-file-too-large"}}) do
 Files["media/ca.pem"]=case[1];local c=Started();assert(c.Reasons[1]==case[2]);c:Dispose()
end
assert(#Sockets==0 and Reads==2 and Closes==2)
""",
"read and close failures stay redacted and close handles":r"""
ReadFailure=true;local c=Started();assert(c.Reasons[1]=="ca-file-read-failed" and Closes==1);c:Dispose()
ReadFailure=false;CloseFailure=true;local c=Started();assert(c.Reasons[1]=="ca-file-read-failed" and Closes==2)
""",
"conflicting sources and incomplete identity rejected":r"""
local c,e=Make({CaCertificate=Cert});assert(not c and e=="certificate-source-conflict")
for _,o in ipairs({{ClientCertificate=Cert},{ClientKey=Key},{ClientCertificateFile="media/client.pem"}}) do
 local c,e=Make(o);assert(not c and e=="client-certificate-key-required")
end
local c,e=Make({ClientCertificate=Cert,ClientKey=Key,Tls=false});assert(not c and e=="client-certificate-requires-tls")
""",
"paths remain relative inside Q-SYS file roots":r"""
for _,path in ipairs({"","/etc/passwd","C:/key.pem","media/../key.pem","media/a/./b","media//a","media/a\\b","media/a\000b","media/"}) do
 local c,e=Make({CaCertificateFile=path});assert(not c and e=="invalid-certificate-path",path)
end
assert(Make({CaCertificateFile="design/ca.pem"}))
""",
"malformed or encrypted PEM rejected without connection":r"""
Files["media/ca.pem"]="bad";local c=Started();assert(c.Reasons[1]=="ca-invalid-pem");c:Dispose()
Files["media/ca.pem"]=Cert
for _,bad in ipairs({"-----BEGIN ENCRYPTED PRIVATE KEY-----x-----END ENCRYPTED PRIVATE KEY-----",Key.."Proc-Type: 4,ENCRYPTED",Key.."\000"}) do
 Files["media/client.key"]=bad;local c=Started({ClientCertificateFile="media/client.pem",ClientKeyFile="media/client.key"})
 assert(c.Reasons[1]=="client-key-invalid-pem");c:Dispose()
end
assert(#Sockets==0)
""",
"deleted credentials retire the old socket on reconnect":r"""
local c,s=Started();s:Open();s:Feed("\032\002\000\000");s.Closed(s)
Files["media/ca.pem"]=nil;Advance(1)
assert(c.State=="Reconnecting" and #Sockets==1 and not s.IsConnected and c.Socket==nil)
c:Dispose();Advance(60);assert(#Sockets==1)
""",
}

def main():
    for name,source in CASES.items():
        lua=runtime();lua.execute(SETUP.encode())
        try: lua.execute(source.encode())
        except Exception:
            print('FAILED:',name);raise
    lua,g,props=design(2)
    g.Properties=props
    lua.execute(SETUP.encode())
    lua.execute(b"""
Controls={}
for _,d in ipairs(GetControls(Properties)) do
 Controls[d.Name]={String=type(d.DefaultValue)=="string" and d.DefaultValue or "",
 Value=type(d.DefaultValue)=="number" and d.DefaultValue or 0,Boolean=d.DefaultValue==true}
end
SecretStorage={["text.1"]={String=""}}
""")
    lua.execute(PLUGIN)
    lua.execute(b"""
Controls.IPAddress.String="localhost";Controls.ClientId.String="plugin"
Controls.Tls.Boolean=true;Controls.CaFromFile.Boolean=true;Controls.CaCertificateFile.String="media/ca.pem"
Controls.CaCertificate.String="ignored stale pasted CA"
Controls.MutualTls.Boolean=true;Controls.ClientCertificateFile.String="media/client.pem";Controls.ClientKeyFile.String="media/client.key"
Controls.Enable.Boolean=true;Controls.Enable.EventHandler()
assert(Sockets[1].CACertData==Cert and Sockets[1].ClientKeyData==Key)
assert(MqttClient.Options.ClientKey==nil and MqttClient.Options.CaCertificate==nil)
for _,line in ipairs(Logs) do assert(not line:find("PRIVATE KEY",1,true)) end
Controls.MutualTls.Boolean=false;Controls.Reconnect.EventHandler()
assert(Sockets[2].ClientKeyData==nil and Sockets[2].ValidateCertificate)
assert(Controls.Status.Value==5)
Files["media/ca.pem"]=nil;Controls.Reconnect.EventHandler()
assert(Controls.Status.Value==2 and Controls.Status.String=="Reconnecting: ca-file-open-failed")
Files["media/ca.pem"]=Cert;Advance(1)
assert(Controls.Status.Value==5)
Files["media/ca.pem"]=Cert..Cert
local count=#Sockets;Controls.Reconnect.EventHandler()
assert(#Sockets==count and Controls.Status.Value==2)
assert(Controls.Status.String=="CA changed: Save to Core & Run required")
Controls.Enable.Boolean=false;Controls.Enable.EventHandler()
Controls.Enable.Boolean=true;Controls.Enable.EventHandler()
assert(#Sockets==count and Controls.Status.String=="CA changed: Save to Core & Run required")

""")
    print(f'PASS: {len(CASES)+1} TLS source, lifecycle and plugin groups')

if __name__=='__main__': main()
