import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { 
  Terminal, 
  TrendingUp, 
  Crosshair, 
  ShieldAlert, 
  CheckCircle2, 
  FileText, 
  Send,
  Activity,
  Bot,
  Lock,
  Search,
  Newspaper,
  ChevronRight,
  Code2,
  Zap
} from 'lucide-react';

const FadeIn = ({ children, delay = 0, className = "" }: { children: React.ReactNode, delay?: number, className?: string }) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
      transition={{ duration: 0.7, delay, ease: [0.21, 0.47, 0.32, 0.98] }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

export default function App() {
  return (
    <div className="relative min-h-screen bg-background overflow-x-hidden selection:bg-primary/20 selection:text-primary">
      {/* Background Texture & Glows */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-grid-pattern [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)] opacity-30 mix-blend-screen"></div>
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary/10 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-primary/5 blur-[100px] rounded-full"></div>
      </div>

      <div className="relative z-10">
        {/* Navigation / Header */}
        <header className="container mx-auto px-6 py-8 flex items-center justify-between">
          <div className="flex items-center gap-2 text-primary font-mono font-bold text-xl tracking-tight">
            <Activity className="w-6 h-6" />
            <span>QuantBot.ai</span>
          </div>
          <div className="flex items-center gap-3 bg-secondary/50 border border-border px-4 py-1.5 rounded-full backdrop-blur-sm">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.6)]"></div>
            <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">API Online</span>
          </div>
        </header>

        {/* Hero Section */}
        <section className="container mx-auto px-6 pt-20 pb-32 flex flex-col items-center text-center">
          <FadeIn delay={0.1}>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-sm font-medium mb-8">
              <Zap className="w-4 h-4" />
              <span>Version 2.0 Live</span>
            </div>
          </FadeIn>
          
          <FadeIn delay={0.2} className="max-w-4xl">
            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 text-transparent bg-clip-text bg-gradient-to-br from-white to-white/60">
              Institutional-Grade <br className="hidden md:block" />
              <span className="text-primary">Quant Analysis</span> in Telegram
            </h1>
          </FadeIn>
          
          <FadeIn delay={0.3} className="max-w-2xl">
            <p className="text-lg md:text-xl text-muted-foreground mb-12 leading-relaxed">
              An AI-powered investment assistant that breaks down complex financial data, technicals, and macro context into actionable insights instantly.
            </p>
          </FadeIn>
          
          <FadeIn delay={0.4}>
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <a 
                href="https://t.me" 
                target="_blank" 
                rel="noreferrer"
                className="group relative inline-flex items-center gap-2 bg-primary text-primary-foreground font-semibold px-8 py-4 rounded-lg overflow-hidden transition-all hover:scale-105 active:scale-95"
              >
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></div>
                <Send className="w-5 h-5 relative z-10" />
                <span className="relative z-10">Add to Telegram</span>
              </a>
              <a 
                href="#commands"
                className="inline-flex items-center gap-2 px-8 py-4 rounded-lg font-medium border border-border bg-card/30 hover:bg-card/80 transition-colors"
              >
                <Code2 className="w-5 h-5 text-muted-foreground" />
                <span>View Commands</span>
              </a>
            </div>
          </FadeIn>
        </section>

        {/* How It Works Section */}
        <section className="border-t border-border bg-card/20 backdrop-blur-md py-24">
          <div className="container mx-auto px-6">
            <FadeIn>
              <div className="text-center mb-16">
                <h2 className="text-3xl font-bold mb-4">Frictionless Workflow</h2>
                <p className="text-muted-foreground">Get deep analytical models without leaving your chat.</p>
              </div>
            </FadeIn>
            
            <div className="grid md:grid-cols-3 gap-8 relative">
              <div className="hidden md:block absolute top-1/2 left-[10%] right-[10%] h-px bg-gradient-to-r from-transparent via-border to-transparent -translate-y-1/2"></div>
              
              {[
                { step: "01", title: "Open Telegram", desc: "Start a chat with our bot directly on your phone or desktop.", icon: Bot },
                { step: "02", title: "Request Ticker", desc: "Type /analyze followed by any US stock ticker (e.g., AAPL).", icon: Search },
                { step: "03", title: "Receive Insights", desc: "Get a comprehensive, multi-section quant report in seconds.", icon: FileText }
              ].map((item, i) => (
                <FadeIn key={i} delay={0.2 + (i * 0.1)} className="relative bg-card border border-border p-8 rounded-2xl flex flex-col items-center text-center hover:border-primary/50 transition-colors group">
                  <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-colors">
                    <item.icon className="w-6 h-6 text-primary" />
                  </div>
                  <div className="text-4xl font-mono font-black text-white/5 absolute top-4 right-4">{item.step}</div>
                  <h3 className="text-xl font-bold mb-3">{item.title}</h3>
                  <p className="text-muted-foreground">{item.desc}</p>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* Commands & Terminal Section */}
        <section id="commands" className="py-24 container mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <FadeIn>
                <h2 className="text-3xl font-bold mb-6">Powerful Commands</h2>
                <p className="text-muted-foreground mb-8 text-lg">
                  Designed for speed. Access robust financial models using simple slash commands. No login required.
                </p>
              </FadeIn>
              
              <div className="space-y-4">
                <FadeIn delay={0.1}>
                  <div className="bg-card border border-border p-5 rounded-xl group hover:border-primary/50 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <code className="text-primary font-mono bg-primary/10 px-2 py-1 rounded text-sm">/analyze [TICKER]</code>
                      <span className="text-xs text-muted-foreground uppercase tracking-wide">Core Command</span>
                    </div>
                    <p className="text-sm text-muted-foreground">Runs a full comprehensive quantitative and qualitative analysis on the specified ticker.</p>
                  </div>
                </FadeIn>

                <FadeIn delay={0.2}>
                  <div className="bg-card border border-border p-5 rounded-xl group hover:border-primary/50 transition-colors">
                    <div className="flex items-center justify-between mb-2">
                      <code className="text-primary font-mono bg-primary/10 px-2 py-1 rounded text-sm">/help</code>
                      <span className="text-xs text-muted-foreground uppercase tracking-wide">Utility</span>
                    </div>
                    <p className="text-sm text-muted-foreground">Displays all available commands, usage examples, and tips for reading the output.</p>
                  </div>
                </FadeIn>
              </div>
            </div>

            <FadeIn delay={0.3} className="relative">
              <div className="absolute -inset-1 bg-gradient-to-b from-primary/20 to-transparent rounded-2xl blur-lg opacity-50"></div>
              <div className="relative bg-[#0d1117] border border-border rounded-xl overflow-hidden shadow-2xl flex flex-col">
                <div className="h-10 bg-[#161b22] border-b border-border flex items-center px-4 gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
                  <span className="ml-2 text-xs font-mono text-muted-foreground">telegram-bot-session</span>
                </div>
                <div className="p-6 font-mono text-sm overflow-hidden h-[400px] relative">
                  <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#0d1117] z-10"></div>
                  <div className="text-muted-foreground mb-4 flex items-center gap-2">
                    <span className="text-primary">User</span> <ChevronRight className="w-3 h-3" /> /analyze NVDA
                  </div>
                  <div className="text-muted-foreground mb-4 flex items-center gap-2 opacity-70">
                    <span className="text-blue-400">Bot</span> <ChevronRight className="w-3 h-3" /> Fetching real-time market data...
                  </div>
                  <div className="space-y-4 text-gray-300">
                    <div className="text-white font-bold pb-2 border-b border-border/50">📊 NVDA ANALYSIS REPORT</div>
                    <div>
                      <span className="text-yellow-400">⚠️ Risk Score:</span> 3.5/10 (Moderate)
                    </div>
                    <div>
                      <span className="text-green-400">✅ Confidence:</span> 85%
                    </div>
                    <div>
                      <span className="text-blue-400">📈 Tech Analysis:</span> RSI is currently at 68, approaching overbought territory. MACD shows strong bullish divergence. Moving averages (50d/200d) indicate sustained upward momentum...
                    </div>
                    <div>
                      <span className="text-purple-400">🎯 Entry/Target/Stop:</span>
                      <br />• Entry Range: $118 - $122
                      <br />• PT: $140 (+15%)
                      <br />• SL: $108 (-9%)
                    </div>
                  </div>
                </div>
              </div>
            </FadeIn>
          </div>
        </section>

        {/* Output Sections */}
        <section className="py-24 bg-card/30 border-y border-border">
          <div className="container mx-auto px-6">
            <FadeIn>
              <div className="text-center max-w-2xl mx-auto mb-16">
                <h2 className="text-3xl font-bold mb-4">Comprehensive Output</h2>
                <p className="text-muted-foreground">Every analysis provides a 360-degree view of the asset, structured for rapid consumption.</p>
              </div>
            </FadeIn>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {[
                { icon: Newspaper, title: "News & Macro", desc: "Recent catalysts and broader economic context affecting the ticker." },
                { icon: TrendingUp, title: "Technical Analysis", desc: "Momentum indicators, moving averages, and volume profile." },
                { icon: Crosshair, title: "Entry/Target/Stop", desc: "Calculated levels based on volatility and support/resistance zones." },
                { icon: Search, title: "Thesis Validation", desc: "Core fundamental arguments supporting the directional bias." },
                { icon: ShieldAlert, title: "Risk Score", desc: "Proprietary 1-10 metric evaluating downside exposure." },
                { icon: CheckCircle2, title: "Confidence Score", desc: "AI certainty percentage based on signal confluence." },
                { icon: Terminal, title: "Executive Summary", desc: "The bottom line, condensed into a single actionable paragraph.", colSpan: true }
              ].map((card, i) => (
                <FadeIn key={i} delay={0.1 * i} className={card.colSpan ? "md:col-span-2 lg:col-span-3 xl:col-span-2" : ""}>
                  <div className="bg-card border border-border p-6 rounded-xl h-full hover:bg-secondary/50 transition-colors">
                    <card.icon className="w-6 h-6 text-primary mb-4" />
                    <h3 className="font-bold mb-2">{card.title}</h3>
                    <p className="text-sm text-muted-foreground">{card.desc}</p>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* Privacy Section */}
        <section className="py-32 container mx-auto px-6 text-center">
          <FadeIn>
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-secondary text-primary mb-8 border border-border shadow-[0_0_30px_rgba(0,212,255,0.15)]">
              <Lock className="w-8 h-8" />
            </div>
            <h2 className="text-3xl font-bold mb-6">Built on Privacy</h2>
            <div className="max-w-2xl mx-auto p-6 rounded-2xl bg-gradient-to-b from-card to-background border border-border">
              <p className="text-lg text-muted-foreground leading-relaxed">
                <strong className="text-foreground">Zero PII.</strong> No absolute prices reach the AI models. 
                Our architecture normalizes data locally — only <span className="text-primary font-mono text-sm">relative metrics</span>, <span className="text-primary font-mono text-sm">ratios</span>, and <span className="text-primary font-mono text-sm">% changes</span> are transmitted for analysis. Your portfolio remains yours.
              </p>
            </div>
          </FadeIn>
        </section>

        {/* Footer */}
        <footer className="border-t border-border bg-card/50 py-12">
          <div className="container mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-muted-foreground font-mono text-sm">
              <Activity className="w-4 h-4 text-primary" />
              <span>QuantBot.ai © {new Date().getFullYear()}</span>
            </div>
            <div className="text-sm text-muted-foreground text-center md:text-right">
              Built with <span className="text-foreground">FastAPI</span> + <span className="text-foreground">OpenRouter</span> + <span className="text-foreground">yfinance</span>
              <div className="text-xs mt-1 text-primary/70">Free tier API limit applies.</div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
