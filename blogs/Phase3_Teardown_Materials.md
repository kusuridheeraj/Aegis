# Phase 3 War Stories: Hardening the MCP Layer

This document tracks the technical "Gotchas" and invisible bugs discovered while building the AI Consumption layer for Aegis. Use these as primary hooks for the Phase 3 engineering blog.

---

### War Story 1: The "Handshake Timeout" Phantom
**Symptom:** AI clients (like Cherry Studio or Claude Desktop) connect to the MCP server but report "No tools discovered" or immediately disconnect.

**The Detective Work:** 
We checked the internal logs and discovered that the server was taking **13.5 seconds** to boot. Most MCP clients have a hard **10-second timeout** for the initial `stdio` handshake. 

**The Root Cause:** 
HuggingFace's `SentenceTransformer` library performs a "version check" over HTTPS every time it initializes. If the internet is slow, the server hangs on the network call. Since the handshake happens *during* the boot process, the client kills the process before it can ever register its tools.

**The Staff-Level Fix:** 
Forced **`local_files_only=True`** in the model loader. This tells the system: *"I don't care if there is a new version; use what is on the disk."* 
*   **Result:** Boot time dropped from 13.5s to **0.4s**. The handshake is now near-instant.

---

### War Story 2: The "Ghost Working Directory" Bug
**Symptom:** The MCP server works perfectly when run from the terminal, but throws "File Not Found" or "Connection Refused" when run from an external app.

**The Root Cause:** 
When an app like Cherry Studio launches an MCP server, it often starts the process from its own system directory, NOT your project folder. Any code using relative paths (like `open(".env")`) will fail because Python looks in the wrong folder.

**The Staff-Level Fix:** 
Implemented **Path Hardening**. We used `Path(__file__).parent.absolute()` to programmatically find the server's root folder at runtime. This ensures that the `.env` file and log files are found regardless of where the server is launched from.

---

### War Story 3: The Log Corruption Trap
**Symptom:** The MCP protocol throws "Invalid JSON" or "Parse Error" even though the code is correct.

**The Root Cause:** 
MCP over `stdio` uses `stdout` for its communication. If you have a `print("Starting server...")` or a standard `logging.info()` that goes to `stdout`, that text gets mixed in with the protocol's JSON messages. The AI client sees the text, tries to parse it as JSON, fails, and crashes.

The Staff-Level Fix:
Redirected all server logging to a **Dedicated File Handler** and forced all console output to **`stderr`**. This keeps the "Protocol Pipe" (`stdout`) purely for JSON messages, while developers can still watch the raw logs in real-time via `aegis-mcp.log`.

---

### War Story 4: The "Intelligence Gap" (Why Protocols Fail on Weak Models)
**Symptom:** The MCP server is 100% healthy, the tools are discovered, but the AI responds with: *"I don't have access to your local files or tools."*

**The Root Cause:** 
**MCP is only as smart as the model behind it.** Many free or lightweight models aren't fine-tuned for "Tool Use." Even if the protocol delivers the data to the model's front door, the model doesn't know how to "open the door" and read the results. It reverts to its safety training, claiming it has no external access.

**The Fix:** 
Distinguish between a **Protocol Failure** and a **Reasoning Failure**. If the model is too "dumb" to call the tool natively, we bypass its decision-making loop using a **Headless Agent Proxy**.

---

### War Story 5: The "Headless Agent" (Engineering Autonomy without Credits)
**The Problem:** We wanted to prove the RAG pipeline worked end-to-end, but we didn't want to spend money on expensive Claude 3.5 API credits for a basic test.

**The Innovation:** 
I built a **Headless Agent (`headless_agent.py`)**. 
Instead of relying on the model to "decide" to use a tool, the script forces a **Manual Reasoning Loop**:
1.  **Reasoning:** Use a cheap/free model to extract search keywords from the user question.
2.  **Execution:** Manually call the local Qdrant database using those keywords.
3.  **Synthesis:** Feed the retrieved text back to the free model for a final summary.

**The Result:** 
We proved that our vector retrieval was flawless (retrieving Jennifer Doudna's discovery from a 40MB PDF) using a **zero-cost model** that originally claimed it "didn't have access." 

*Lesson:* Don't let a weak model convince you your architecture is broken. If the protocol works, but the model is dumb, build a proxy.

---

### War Story 7: The Quantization Hack (Squeezing AI onto a CPU)
**The Problem:** Generating embeddings for massive PDF books was too slow on a standard CPU, creating a bottleneck in our real-time pipeline.

**The Solution:** 
We implemented **8-bit INT8 Quantization** via the `optimum` and `onnxruntime` libraries. We exported our PyTorch model to ONNX format and applied Level 3 optimizations.

**The Real-World Metrics:**
After stress-testing with a 100-chunk workload, we achieved:
*   **3.8x Inference Speedup:** The pipeline now vectorizes text nearly 4 times faster than standard precision.
*   **66% RAM Reduction:** Memory usage dropped from ~82MB to ~28MB, allowing the AI worker to run on extremely cheap, low-resource hardware.

*The Architectural Insight:* A Staff Engineer doesn't just build a model; they optimize the model for the hardware it actually runs on.


---

### War Story 6: The "Coworker" Transition (Scripted Proxy vs. Autonomous Brain)
**The Concept:** At the 72 LPA level, you don't build calculators; you build coworkers. We realized that our initial `headless_agent.py` was just a high-speed calculator. It followed a linear path and gave up if the math didn't match.

**The Comparison:**
We documented the fundamental shift from **Linear Logic** to **Stateful Autonomy**:

| Feature | Headless Proxy (The Script) | LangGraph (The Brain) |
| :--- | :--- | :--- |
| **Logic** | **Linear.** (Prompt -> Search -> Answer) | **Cyclic.** (Reason -> Search -> Evaluate -> Repeat) |
| **Error Handling** | None. It fails if results are null. | **Self-Correction.** It analyzes its own failures and retries. |
| **State** | Stateless. Forgets everything immediately. | **Stateful.** Remembers what it tried before to avoid loops. |

**The Hook:** LangGraph turns your AI from a "calculator" into a "coworker." It doesn't just search; it **thinks** about whether the search was successful before it talks back to you.

