import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, AlertCircle, Server, Code, Zap, Shield, Database, ExternalLink, Github, Terminal, Info, Copy, Sun, Moon } from "lucide-react";
import { ConfigDialog } from "@/components/ConfigDialog";

interface SystemSnapshot {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
}

interface ServerStatus {
  status: "healthy" | "degraded" | "offline";
  uptime: string;
  sessions_active: number;
  lastCheck: string;
  system?: SystemSnapshot;
}

interface ServiceStatus {
  name: string;
  enabled: boolean;
  status: "active" | "inactive" | "error";
  lastActivity?: string;
}

const BACKEND_URL = import.meta.env.VITE_API_URL || "https://google-workspace-mcp-server-554655392699.us-central1.run.app";

export default function Home() {
  const [serverStatus, setServerStatus] = useState<ServerStatus>({
    status: "healthy",
    uptime: "0s",
    sessions_active: 0,
    lastCheck: "Never",
  });

  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "Google Drive", enabled: true, status: "active", lastActivity: "Syncing..." },
    { name: "Gmail", enabled: true, status: "active", lastActivity: "Syncing..." },
    { name: "Google Calendar", enabled: true, status: "active", lastActivity: "Syncing..." },
    { name: "Google Docs", enabled: true, status: "inactive" },
    { name: "Google Sheets", enabled: true, status: "inactive" },
    { name: "Google Slides", enabled: true, status: "inactive" },
  ]);

  const [activeTab, setActiveTab] = useState("overview");
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window !== "undefined") {
      return (localStorage.getItem("theme") as "light" | "dark") || "light";
    }
    return "light";
  });

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/health`);
      if (!response.ok) throw new Error("Backend unreachable");
      const data = await response.json();

      setServerStatus({
        status: data.status,
        uptime: data.uptime,
        sessions_active: data.sessions_active,
        lastCheck: new Date().toLocaleTimeString(),
        system: data.system
      });
      setError(null);
    } catch (err) {
      console.error("Failed to fetch status:", err);
      setServerStatus(prev => ({ ...prev, status: "offline" }));
      setError("Cannot connect to MCP server");
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "healthy":
      case "active":
        return <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider">{status}</Badge>;
      case "degraded":
        return <Badge className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-amber-500/20 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider">{status}</Badge>;
      case "offline":
      case "error":
        return <Badge className="bg-rose-500/10 text-rose-500 hover:bg-rose-500/20 border-rose-500/20 px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider">{status}</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getServiceIcon = (serviceName: string) => {
    const name = serviceName.toLowerCase();
    if (name.includes("drive")) return "/drive.png";
    if (name.includes("gmail")) return "/gmail.webp";
    if (name.includes("calendar")) return "/calendar.png";
    if (name.includes("docs")) return "/docs.png";
    if (name.includes("sheets")) return "/sheets.png";
    if (name.includes("slides")) return "/slides.png";
    return "/mcp-logo.png";
  };

  return (
    <div className="min-h-screen bg-background text-foreground selection:bg-primary/20 transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <header className="flex flex-col md:flex-row items-center justify-between gap-8 mb-16 border-b border-border pb-12">
          <div className="flex items-center gap-6">
            <div className="p-3 rounded-2xl bg-primary/5 border border-primary/10">
              <img src="/user-branding.png" alt="User Logo" className="w-16 h-16 object-contain" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Google Workspace MCP</h1>
              <p className="text-muted-foreground font-medium">Professional Server Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon"
              className="rounded-full w-9 h-9"
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            >
              {theme === "light" ? (
                <Moon className="w-4 h-4 text-nordic-slate" />
              ) : (
                <Sun className="w-4 h-4 text-amber-400" />
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-2 font-semibold"
              onClick={() => window.open("https://github.com/mcpmessenger/google-workspace-mcp-server", "_blank")}
            >
              <Github className="w-4 h-4 text-[#24292e] dark:text-white" />
              GitHub
            </Button>
            <ConfigDialog />
          </div>
        </header>

        {/* Status Alert */}
        {serverStatus.status !== "healthy" && (
          <Alert variant="destructive" className="mb-8 rounded-xl border-rose-500/20 bg-rose-500/5">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="font-semibold uppercase tracking-wider text-xs">
              System Alert: Server status is {serverStatus.status}
            </AlertDescription>
          </Alert>
        )}

        {/* Global Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {[
            { label: "Server Status", value: serverStatus.status, icon: Server, color: "text-emerald-500" },
            { label: "Uptime", value: serverStatus.uptime, icon: Zap, color: "text-amber-500" },
            { label: "Active Sessions", value: serverStatus.sessions_active, icon: Shield, color: "text-blue-500" }
          ].map((stat) => (
            <Card key={stat.label} className="nordic-card p-6 rounded-2xl flex items-center justify-between group">
              <div>
                <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-widest mb-1">{stat.label}</p>
                <p className="text-2xl font-bold tracking-tight capitalize">{stat.value}</p>
              </div>
              <div className={`p-3 rounded-xl bg-muted/30 group-hover:scale-110 transition-transform duration-300`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </Card>
          ))}
        </div>

        {/* Main Content Sections */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-8">
          <TabsList className="bg-muted/30 p-1 rounded-xl glass">
            {["Overview", "Usage", "Services", "Configuration", "Deployment"].map((tab) => (
              <TabsTrigger
                key={tab.toLowerCase()}
                value={tab.toLowerCase()}
                className="rounded-lg px-8 py-2 text-sm font-semibold transition-all data-[state=active]:bg-background data-[state=active]:shadow-sm"
              >
                {tab}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview" className="space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <Card className="nordic-card rounded-2xl overflow-hidden">
                <CardHeader className="bg-muted/30 pb-6 border-b border-border">
                  <CardTitle className="text-sm font-bold uppercase tracking-widest">System Metrics</CardTitle>
                </CardHeader>
                <CardContent className="p-8 grid grid-cols-2 gap-8">
                  {[
                    { label: "Memory Usage", value: serverStatus.system ? `${serverStatus.system.memory_percent}%` : "---" },
                    { label: "CPU Usage", value: serverStatus.system ? `${serverStatus.system.cpu_percent}%` : "---" },
                    { label: "Process Memory", value: serverStatus.system ? `${serverStatus.system.memory_used_mb} MB` : "---" },
                    { label: "Last Polled", value: serverStatus.lastCheck }
                  ].map((metric) => (
                    <div key={metric.label}>
                      <p className="text-[10px] font-bold text-muted-foreground uppercase mb-1">{metric.label}</p>
                      <p className="text-2xl font-bold">{metric.value}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="nordic-card rounded-2xl overflow-hidden">
                <CardHeader className="bg-muted/30 pb-6 border-b border-border">
                  <CardTitle className="text-sm font-bold uppercase tracking-widest">Protocol Capabilities</CardTitle>
                </CardHeader>
                <CardContent className="p-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    { icon: Zap, title: "Unified Endpoint", desc: "Single /mcp gateway" },
                    { icon: Shield, title: "Secure Sessions", desc: "Encrypted handshake" },
                    { icon: Database, title: "Persistence", desc: "Stateless scalability" },
                    { icon: Code, title: "JSON-RPC 2.0", desc: "Standard structure" }
                  ].map((feat) => (
                    <div key={feat.title} className="flex gap-4 items-start group">
                      <div className="p-2 rounded-lg bg-primary/5 group-hover:bg-primary/10 transition-colors">
                        <feat.icon className="w-4 h-4 text-primary" />
                      </div>
                      <div>
                        <p className="text-xs font-bold uppercase">{feat.title}</p>
                        <p className="text-[11px] text-muted-foreground mt-0.5">{feat.desc}</p>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="usage" className="animate-in fade-in slide-in-from-bottom-2 duration-500">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <Card className="nordic-card rounded-2xl overflow-hidden">
                <CardHeader className="bg-muted/30 pb-6 border-b border-border">
                  <CardTitle className="text-sm font-bold uppercase tracking-widest flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-emerald-500" />
                    How to Use
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-8 space-y-6">
                  <div className="space-y-4">
                    <div className="flex gap-4">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">1</div>
                      <p className="text-sm font-medium leading-relaxed italic opacity-80 decoration-emerald-500/30 underline-offset-4 underline">Open your MCP client (e.g., Claude Desktop, Cursor).</p>
                    </div>
                    <div className="flex gap-4">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">2</div>
                      <p className="text-sm font-medium leading-relaxed italic opacity-80 decoration-emerald-500/30 underline-offset-4 underline">Add the following JSON configuration to your settings file.</p>
                    </div>
                    <div className="flex gap-4">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">3</div>
                      <p className="text-sm font-medium leading-relaxed italic opacity-80 decoration-emerald-500/30 underline-offset-4 underline">The server uses **Streamable HTTP**, so you connect to it via its URL.</p>
                    </div>
                  </div>

                  <Alert className="bg-primary/5 border-primary/10 rounded-xl">
                    <Info className="h-4 w-4" />
                    <AlertDescription className="text-xs font-semibold">
                      Ensure you have implemented the MCP Streamable HTTP transport on your client side.
                    </AlertDescription>
                  </Alert>
                </CardContent>
              </Card>

              <Card className="nordic-card rounded-2xl overflow-hidden">
                <CardHeader className="bg-muted/30 pb-6 border-b border-border flex flex-row items-center justify-between">
                  <CardTitle className="text-sm font-bold uppercase tracking-widest">Connection Config</CardTitle>
                  <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => navigator.clipboard.writeText(JSON.stringify({
                    mcpServers: {
                      workspace: {
                        url: BACKEND_URL,
                        transport: "http"
                      }
                    }
                  }, null, 2))}>
                    <Copy className="w-4 h-4" />
                  </Button>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="bg-slate-900 text-slate-200 p-8 font-mono text-xs overflow-x-auto h-[250px]">
                    <pre className="leading-relaxed">
                      {`{
  "mcpServers": {
    "workspace": {
      "url": "${BACKEND_URL}",
      "transport": "http"
    }
  }
}`}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="services" className="animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Card className="nordic-card rounded-2xl overflow-hidden">
              <CardHeader className="bg-muted/30 pb-6 border-b border-border">
                <CardTitle className="text-sm font-bold uppercase tracking-widest">Workspace Services</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="divide-y divide-border">
                  {services.map((service) => (
                    <div key={service.name} className="flex items-center justify-between p-6 hover:bg-muted/20 transition-colors">
                      <div className="flex items-center gap-6">
                        <div className="relative">
                          <img
                            src={getServiceIcon(service.name)}
                            alt={service.name}
                            className={`w-10 h-10 object-contain ${service.status === "active" ? "" : "grayscale opacity-40"}`}
                          />
                          {service.status === "active" && (
                            <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-emerald-500 rounded-full border-2 border-background" />
                          )}
                        </div>
                        <div>
                          <p className="font-bold text-sm tracking-tight">{service.name}</p>
                          {service.lastActivity && (
                            <p className="text-[10px] text-muted-foreground mt-0.5 font-medium italic">Active {service.lastActivity}</p>
                          )}
                        </div>
                      </div>
                      {getStatusBadge(service.status)}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="configuration" className="animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Card className="nordic-card rounded-2xl overflow-hidden p-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div className="space-y-6">
                  <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground border-b border-border pb-4">Endpoint Configuration</h3>
                  <div className="grid gap-4">
                    {[
                      { label: "Host Address", value: "0.0.0.0" },
                      { label: "Server Port", value: "8080" },
                      { label: "Protocol", value: "MCP v1.0.4" }
                    ].map(cfg => (
                      <div key={cfg.label} className="flex justify-between items-center py-2 border-b border-border/10">
                        <span className="text-xs font-semibold text-muted-foreground">{cfg.label}</span>
                        <span className="text-xs font-mono font-bold">{cfg.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="space-y-6">
                  <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground border-b border-border pb-4">Security Layer</h3>
                  <div className="grid gap-3">
                    {["DNS Rebinding Shield", "CORS Proxy Layer", "Session Isolation"].map(s => (
                      <div key={s} className="flex items-center gap-3 text-xs font-medium">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                        {s}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="deployment" className="animate-in fade-in slide-in-from-bottom-2 duration-500">
            <Card className="nordic-card rounded-2xl overflow-hidden">
              <CardHeader className="bg-muted/30 pb-6 border-b border-border">
                <CardTitle className="text-sm font-bold uppercase tracking-widest">Cloud Run Command</CardTitle>
              </CardHeader>
              <CardContent className="p-8 bg-slate-900 text-slate-200">
                <pre className="font-mono text-xs leading-relaxed overflow-x-auto">
                  {`gcloud run deploy google-workspace-mcp-server \\
  --image gcr.io/PROJECT_ID/mcp-server:latest \\
  --platform managed \\
  --region us-central1 \\
  --memory 1Gi --cpu 1 \\
  --no-allow-unauthenticated`}
                </pre>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-6 mt-32 border-t border-border py-12 flex flex-col items-center gap-4">
        <img src="/mcp-logo.png" alt="MCP" className="w-10 h-10 object-contain opacity-20 grayscale" />
        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em]">
          Google Workspace MCP Server • Professional 2026
        </p>
      </footer>
    </div>
  );
}
