import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle2, AlertCircle, Server, Settings, Code, Zap, Shield, Database } from "lucide-react";

/**
 * Google Workspace MCP Server Dashboard
 * 
 * Design Philosophy: Modern, professional tech dashboard with clear information hierarchy
 * - Clean typography with semantic color usage
 * - Card-based layout for modular content
 * - Real-time status indicators
 * - Responsive grid system
 */

interface ServerStatus {
  status: "healthy" | "degraded" | "offline";
  uptime: string;
  sessions: number;
  lastCheck: string;
}

interface ServiceStatus {
  name: string;
  enabled: boolean;
  status: "active" | "inactive" | "error";
  lastActivity?: string;
}

export default function Home() {
  const [serverStatus, setServerStatus] = useState<ServerStatus>({
    status: "healthy",
    uptime: "24h 15m",
    sessions: 3,
    lastCheck: new Date().toLocaleTimeString(),
  });

  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "Google Drive", enabled: true, status: "active", lastActivity: "2 min ago" },
    { name: "Gmail", enabled: true, status: "active", lastActivity: "5 min ago" },
    { name: "Google Calendar", enabled: true, status: "active", lastActivity: "1 min ago" },
    { name: "Google Docs", enabled: true, status: "inactive" },
    { name: "Google Sheets", enabled: true, status: "inactive" },
    { name: "Google Slides", enabled: true, status: "inactive" },
  ]);

  const [activeTab, setActiveTab] = useState("overview");

  // Simulate status updates
  useEffect(() => {
    const interval = setInterval(() => {
      setServerStatus(prev => ({
        ...prev,
        lastCheck: new Date().toLocaleTimeString(),
      }));
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
      case "active":
        return "bg-green-100 text-green-800";
      case "degraded":
        return "bg-yellow-100 text-yellow-800";
      case "offline":
      case "error":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "healthy":
      case "active":
        return <CheckCircle2 className="w-4 h-4" />;
      case "degraded":
        return <AlertCircle className="w-4 h-4" />;
      case "offline":
      case "error":
        return <AlertCircle className="w-4 h-4" />;
      default:
        return null;
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
    return "/mcp-logo.png"; // fallback
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-8 flex flex-col items-center">
      {/* Header */}
      <header className="w-full max-w-5xl mb-12 relative">
        <div className="flex items-center justify-between mb-8">
          <div className="select-none flex items-center gap-4 group">
            <img
              src="/user-branding.png"
              alt="User Logo"
              className="w-24 h-24 object-contain hover:scale-110 transition-transform cursor-pointer"
              onClick={() => setActiveTab("overview")}
            />
          </div>

          <div className="text-center flex-1">
            <h1 className="text-4xl md:text-5xl font-bold text-foreground">Google Workspace MCP</h1>
            <p className="text-lg md:text-xl font-handwriting text-primary mt-1">Model Context Protocol Dashboard</p>
          </div>

          <div className="select-none flex items-center gap-4 group">
            <img
              src="/mcp-logo.png"
              alt="MCP Logo"
              className="w-16 h-16 object-contain opacity-40 hover:opacity-100 transition-opacity rotate-12 group-hover:rotate-0 transition-transform"
            />
          </div>
        </div>

        <div className="flex justify-center gap-4">
          <Button
            variant="outline"
            className="border-2 border-foreground hover:bg-foreground hover:text-background font-typewriter transform -rotate-1 transition-transform"
            onClick={() => window.open("https://github.com/mcpmessenger/google-workspace-mcp-server", "_blank")}
          >
            [ Documentation ]
          </Button>
          <Button className="bg-primary text-primary-foreground border-2 border-primary hover:bg-transparent hover:text-primary font-typewriter transform rotate-1 transition-transform">
            [ Configure Server ]
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full max-w-5xl space-y-12">
        {/* Status Alert */}
        {serverStatus.status !== "healthy" && (
          <Alert className="border-4 border-destructive bg-destructive/10 font-typewriter postcard-card mb-8">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <AlertDescription className="text-destructive font-bold uppercase tracking-widest">
              SYSTEM ALERT: Server status is {serverStatus.status}.
            </AlertDescription>
          </Alert>
        )}

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-10">
          <TabsList className="bg-transparent gap-2 h-auto flex-wrap justify-center border-b-2 border-foreground/20 pb-2">
            {["Overview", "Services", "Configuration", "Deployment"].map((tab) => (
              <TabsTrigger
                key={tab.toLowerCase()}
                value={tab.toLowerCase()}
                className="data-[state=active]:bg-foreground data-[state=active]:text-background border-2 border-foreground px-6 py-2 font-typewriter uppercase text-xs tracking-tighter transition-all"
              >
                {tab}
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Server Status Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Status Card */}
              <Card className="postcard-card transform -rotate-1">
                <div className="postcard-stamp">PRORITY</div>
                <CardHeader className="pb-3 border-b-2 border-foreground/10 mx-4">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Server Status</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className={`w-4 h-4 rounded-full ${serverStatus.status === "healthy" ? "bg-green-600 shadow-[0_0_10px_rgba(22,163,74,0.5)]" : "bg-yellow-500"}`} />
                    <span className="text-3xl font-bold tracking-tighter uppercase">{serverStatus.status}</span>
                  </div>
                  <p className="text-xs font-typewriter mt-4 text-muted-foreground italic">Checked: {serverStatus.lastCheck}</p>
                </CardContent>
              </Card>

              {/* Uptime Card */}
              <Card className="postcard-card transform rotate-2">
                <div className="postcard-stamp">UPTIME</div>
                <CardHeader className="pb-3 border-b-2 border-foreground/10 mx-4">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Uptime</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="text-3xl font-bold tracking-tighter">{serverStatus.uptime}</div>
                  <p className="text-xs font-typewriter mt-4 text-muted-foreground italic">Continuous Log Service</p>
                </CardContent>
              </Card>

              {/* Active Sessions Card */}
              <Card className="postcard-card transform -rotate-1">
                <div className="postcard-stamp">CLIENTS</div>
                <CardHeader className="pb-3 border-b-2 border-foreground/10 mx-4">
                  <CardTitle className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Active Sessions</CardTitle>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="text-3xl font-bold tracking-tighter">{serverStatus.sessions}</div>
                  <p className="text-xs font-typewriter mt-4 text-muted-foreground italic">Authenticated Users</p>
                </CardContent>
              </Card>
            </div>

            {/* Quick Stats */}
            <Card className="postcard-card border-l-[12px] border-l-primary/30">
              <CardHeader>
                <CardTitle className="text-lg uppercase">System Metrics</CardTitle>
                <CardDescription className="font-handwriting text-primary text-lg">Real-time performance logs</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  {[
                    { label: "Memory Usage", value: "512 MB" },
                    { label: "CPU Usage", value: "15%" },
                    { label: "Requests/min", value: "240" },
                    { label: "Avg Response", value: "145ms" }
                  ].map((stat) => (
                    <div key={stat.label} className="p-4 border-2 border-foreground/10 bg-background/50 pointer-events-none">
                      <p className="text-[10px] uppercase font-bold text-muted-foreground">{stat.label}</p>
                      <p className="text-2xl font-bold tracking-tighter mt-1">{stat.value}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Features Overview */}
            <Card className="postcard-card border-r-[12px] border-r-secondary/30">
              <CardHeader>
                <CardTitle className="text-lg uppercase">Streamable HTTP Transport</CardTitle>
                <CardDescription className="font-handwriting text-secondary text-lg">MCP Protocol Implementation Features</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {[
                    { icon: Zap, color: "text-primary", bg: "bg-primary/5", title: "Unified HTTP Endpoint", desc: "Single /mcp endpoint for all operations" },
                    { icon: Shield, color: "text-green-700", bg: "bg-green-700/5", title: "Secure Sessions", desc: "Cryptographic session IDs" },
                    { icon: Database, color: "text-accent", bg: "bg-accent/5", title: "Server-Sent Events", desc: "Bidirectional communication" },
                    { icon: Code, color: "text-secondary", bg: "bg-secondary/5", title: "JSON-RPC 2.0", desc: "Standard message format" }
                  ].map((feat) => (
                    <div key={feat.title} className="flex gap-4 p-4 border-2 border-foreground/5 items-start">
                      <feat.icon className={`w-6 h-6 ${feat.color} flex-shrink-0`} />
                      <div>
                        <p className="font-bold uppercase text-xs tracking-widest">{feat.title}</p>
                        <p className="text-sm text-muted-foreground mt-1 leading-tight">{feat.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Services Tab */}
          <TabsContent value="services" className="space-y-10">
            <Card className="postcard-card border-t-[12px] border-t-secondary/30">
              <CardHeader>
                <CardTitle className="text-lg uppercase">Google Workspace Services</CardTitle>
                <CardDescription className="font-handwriting text-secondary text-lg">Integration status and activity logs</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {services.map((service) => (
                    <div key={service.name} className="flex items-center justify-between p-4 border-2 border-foreground/5 hover:bg-foreground/5 transition cursor-pointer group">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 border-2 ${service.status === "active" ? "border-green-600/50 bg-green-50" : "border-foreground/10 bg-background"}`}>
                          <img
                            src={getServiceIcon(service.name)}
                            alt={service.name}
                            className={`w-8 h-8 object-contain ${service.status === "active" ? "" : "grayscale"}`}
                          />
                        </div>
                        <div>
                          <p className="font-bold uppercase text-sm tracking-widest group-hover:text-primary transition-colors">{service.name}</p>
                          {service.lastActivity && (
                            <p className="text-[10px] font-typewriter text-muted-foreground mt-1 underline decoration-dotted">Last activity: {service.lastActivity}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge className={`${getStatusColor(service.status)} border-2 border-current px-3 py-1 font-typewriter uppercase text-[10px] bg-transparent`}>
                          <span className="flex items-center gap-2">
                            {getStatusIcon(service.status)}
                            {service.status}
                          </span>
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Tool Categories */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {[
                { title: "Drive Tools", icon: "/drive.png", items: ["search_drive_files", "get_drive_file_content", "create_drive_file", "update_drive_file", "list_drive_items"], color: "border-primary/20" },
                { title: "Gmail Tools", icon: "/gmail.webp", items: ["search_gmail_messages", "get_gmail_message_content", "send_gmail_message", "modify_gmail_labels", "get_thread_content_batch"], color: "border-secondary/20" },
                { title: "Calendar Tools", icon: "/calendar.png", items: ["list_calendars", "get_events", "create_event", "query_free_busy", "quick_add_event"], color: "border-accent/20" },
                {
                  title: "G-Suite Services", items: [
                    { n: "Google Docs", i: "/docs.png" },
                    { n: "Google Sheets", i: "/sheets.png" },
                    { n: "Google Slides", i: "/slides.png" }
                  ], color: "border-foreground/20"
                }
              ].map((cat) => (
                <Card key={cat.title} className={`postcard-card border-t-4 ${cat.color} transform ${Math.random() > 0.5 ? 'rotate-1' : '-rotate-1'}`}>
                  <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm uppercase tracking-widest font-bold">{cat.title}</CardTitle>
                    {cat.icon && <img src={cat.icon} alt={cat.title} className="w-6 h-6 object-contain" />}
                  </CardHeader>
                  <CardContent className="space-y-2 text-xs font-typewriter text-muted-foreground pt-2">
                    {cat.title === "G-Suite Services" ? (
                      <div className="grid grid-cols-1 gap-2">
                        {cat.items.map((item: any) => (
                          <div key={item.n} className="flex items-center gap-3 p-1 border-b border-foreground/5">
                            <img src={item.i} alt={item.n} className="w-4 h-4 object-contain" />
                            <span>{item.n}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      cat.items.map((item: any) => (
                        <p key={item} className="p-1 border-b border-foreground/5 hover:text-foreground transition-colors">{" >> "} {item}</p>
                      ))
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* Configuration Tab */}
          <TabsContent value="configuration" className="space-y-10">
            <Card className="postcard-card border-b-[12px] border-b-accent/30">
              <CardHeader>
                <CardTitle className="text-lg uppercase">Server Configuration</CardTitle>
                <CardDescription className="font-handwriting text-accent text-lg">Current environment logs</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {[
                    { label: "Host Address", value: "0.0.0.0" },
                    { label: "Server Port", value: "8080" },
                    { label: "Protocol Version", value: "2025-03" },
                    { label: "Session Lifecycle", value: "24 hours" }
                  ].map((cfg) => (
                    <div key={cfg.label} className="p-4 border-2 border-foreground/5 bg-background/30 font-typewriter">
                      <p className="text-[10px] uppercase font-bold text-muted-foreground mb-1">{cfg.label}</p>
                      <p className="text-sm font-bold tracking-widest">{cfg.value}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <Card className="postcard-card transform rotate-1">
                <CardHeader>
                  <CardTitle className="text-sm uppercase font-bold">OAuth 2.1 Protocol</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 font-typewriter text-xs">
                  <div className="p-3 border-l-4 border-primary bg-primary/5">
                    <p className="text-[10px] font-bold opacity-50 uppercase">Auth Endpoint</p>
                    <p className="break-all mt-1">https://accounts.google.com/o/oauth2/v2/auth</p>
                  </div>
                  <div className="p-3 border-l-4 border-primary bg-primary/5">
                    <p className="text-[10px] font-bold opacity-50 uppercase">Token exchange</p>
                    <p className="break-all mt-1">https://oauth2.googleapis.com/token</p>
                  </div>
                </CardContent>
              </Card>

              <Card className="postcard-card transform -rotate-1">
                <CardHeader>
                  <CardTitle className="text-sm uppercase font-bold">Security Shields</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 font-typewriter text-xs">
                  {[
                    "DNS Rebinding Protection",
                    "CORS Proxy Layer",
                    "Session Isolation"
                  ].map((shield) => (
                    <div key={shield} className="flex items-center justify-between p-2 border-b border-foreground/5">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-3 h-3 text-green-600" />
                        <span>{shield}</span>
                      </div>
                      <span className="text-[8px] bg-green-100 text-green-800 px-2 py-0.5 font-bold uppercase">ACTIVE</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Deployment Tab */}
          <TabsContent value="deployment" className="space-y-10">
            <Card className="postcard-card border-t-[12px] border-t-primary/20">
              <CardHeader>
                <CardTitle className="text-lg uppercase">Cloud Run Manifest</CardTitle>
                <CardDescription className="font-handwriting text-primary text-lg">Production deployment protocol</CardDescription>
              </CardHeader>
              <CardContent className="space-y-8">
                <div className="bg-foreground text-background p-6 font-typewriter text-[11px] leading-relaxed relative overflow-hidden group">
                  <div className="absolute top-2 right-2 opacity-10 group-hover:opacity-30 transition-opacity">
                    <Code className="w-24 h-24" />
                  </div>
                  <p className="mb-4 text-primary font-bold"># gcloud deployment script v1.0.4</p>
                  <pre className="whitespace-pre-wrap">
                    {`gcloud run deploy google-workspace-mcp-server \\
  --image gcr.io/PROJECT_ID/google-workspace-mcp:latest \\
  --platform managed \\
  --region us-central1 \\
  --memory 1Gi --cpu 1 \\
  --concurrency 80 \\
  --no-allow-unauthenticated`}
                  </pre>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pb-4">
                  {[
                    { l: "Memory", v: "1GB" },
                    { l: "CPU", v: "1 vCPU" },
                    { l: "Concurrent", v: "80" },
                    { l: "Timeout", v: "3600s" }
                  ].map(spec => (
                    <div key={spec.l} className="text-center border-2 border-foreground/5 py-3 font-typewriter">
                      <p className="text-[10px] uppercase opacity-50">{spec.l}</p>
                      <p className="text-sm font-bold">{spec.v}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <Card className="postcard-card transform -rotate-1">
                <CardHeader>
                  <CardTitle className="text-sm uppercase font-bold">Deployment Checklist</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 font-typewriter text-xs text-muted-foreground">
                  {[
                    "Docker image tagged and pushed",
                    "Service account with IAM roles",
                    "OAuth secrets in Manager",
                    "Cloud Logging verified",
                    "Monitoring alerts established"
                  ].map(step => (
                    <div key={step} className="flex items-center gap-3 p-1">
                      <div className="w-4 h-4 border-2 border-foreground/20 flex items-center justify-center">
                        <CheckCircle2 className="w-3 h-3 text-green-600" />
                      </div>
                      <span>{step}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card className="postcard-card transform rotate-2">
                <CardHeader>
                  <CardTitle className="text-sm uppercase font-bold">Quick Protocols</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {[
                    "Backend README",
                    "Cloud Run Guide",
                    "MCP Specification",
                    "Workspace APIs"
                  ].map(link => (
                    <Button key={link} variant="link" className="w-full justify-start font-typewriter text-xs text-muted-foreground hover:text-primary h-auto p-0">
                      {" >> "} VIEW {link.toUpperCase()}
                    </Button>
                  ))}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mt-24 mb-12 relative flex flex-col items-center">
        <div className="absolute top-0 w-full h-[1px] bg-foreground/20" />
        <div className="pt-12 text-center text-xs font-typewriter uppercase tracking-widest text-muted-foreground">
          <p>Google Workspace MCP Server • Model Context Protocol Implementation</p>
          <p className="mt-2 opacity-50 font-handwriting text-lg text-primary capitalize tracking-normal">Streamable HTTP Transport • Cloud Run Ready</p>
        </div>
        <div className="mt-12 opacity-10 grayscale hover:grayscale-0 transition-all cursor-crosshair">
          <img src="/mcp-logo.png" alt="MCP" className="w-20 h-20 object-contain" />
        </div>
      </footer>
    </div >
  );
}
