{
    /**
     * Agent Tool for Space Invaders Demo
     * 
     * Target: Browser (EcmaScript Module / OmniLink UI)
     * 
     * Responsibilities:
     * 1. Establish direct WebSocket API to ws://localhost:6789/agent_invaders.
     * 2. Parse out fast-refreshing game state (ship bounds, nearest incoming aliens, active bullets).
     * 3. Decide optimal lateral movement (LEFT/RIGHT/STOP) and targeting trigger bounds.
     * 4. Dispatch `action` payload stream over the WebSocket.
     */

    // Interfaces mirroring the Game's JSON stream payload format
    interface Alien {
        x: number;
        y: number;
    }

    interface Bullet {
        x: number;
        y: number;
    }

    interface GameState {
        type: "state";
        shipX: number;
        shipWidth?: number;
        bullet: Bullet | null;
        aliens: Alien[];
        score: number;
        level: number;
    }

    interface AgentAction {
        type: "action";
        move: "left" | "right" | "stop";
        shoot?: boolean;
    }

    const WS_URL = "ws://localhost:6789/agent_invaders";

    function startAgentLoop() {
        console.log(`🚀 Space Invaders Browser Agent Started. Attempting connection to ${WS_URL}...`);

        // --- STEP 1: Connect WebSocket API Array ---
        // Note: Instead of polling via continuous HTTP fetch (as seen in the Pong demo), 
        // the Space Invaders engine specifically provides a bidirectional, lightning-fast WebSocket stream!
        const ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            console.log("✅ [AGENT ONLINE]: Successfully linked to the Space Invaders Game Server!");
        };

        ws.onmessage = (event: MessageEvent) => {
            try {
                // --- STEP 2: Parse the internal Game State ---
                const gameState: GameState = JSON.parse(event.data);

                if (gameState.type !== "state") {
                    return; // Suppress undefined command formats
                }

                // Derive internal alignment variables
                const shipWidth = gameState.shipWidth || 40;
                const shipCenter = gameState.shipX + (shipWidth / 2);
                const tolerance = 6; // Positional snap tolerance in Pixels

                // Find lowest imminent alien threat
                let targetAlien: Alien | null = null;
                if (gameState.aliens && gameState.aliens.length > 0) {
                    targetAlien = gameState.aliens.reduce((prev, curr) => {
                        // Heavily prioritize lowest Y coordinate, tie break with X distance 
                        if (curr.y > prev.y) return curr;
                        if (curr.y === prev.y) {
                            return Math.abs(curr.x - shipCenter) < Math.abs(prev.x - shipCenter) ? curr : prev;
                        }
                        return prev;
                    });
                }

                // --- STEP 3: Logic processing (Brain Pipeline) ---
                let moveCmd: "left" | "right" | "stop" = "stop";
                let shootCmd = false;

                if (targetAlien) {
                    if (shipCenter < targetAlien.x - tolerance) {
                        moveCmd = "right";
                    } else if (shipCenter > targetAlien.x + tolerance) {
                        moveCmd = "left";
                    } else {
                        moveCmd = "stop";
                        // Firing authorization: we hold off shooting if any bullet is already active vertically
                        if (!gameState.bullet) {
                            shootCmd = true;
                        }
                    }
                } else {
                    moveCmd = "stop"; // All aliens cleared or not loaded
                }

                // Intentional handicap for basic agent on Level > 1
                if (gameState.level > 1 && Math.random() < 0.5) {
                    const r = Math.random();
                    if (r < 0.33) moveCmd = "stop";
                    else if (r < 0.66) moveCmd = "left";
                    else moveCmd = "right";

                    // Prevent shooting 50% of time
                    if (Math.random() < 0.5) shootCmd = false;
                }

                // Inspection logging: Monitor the tight-loop AI routing behaviors
                if (moveCmd !== "stop" || shootCmd) {
                    console.log(`[AGENT] Ship @ ${Math.round(shipCenter)} | Target @ ${targetAlien ? Math.round(targetAlien.x) : 'N/A'} -> Action: ${moveCmd.toUpperCase()}${shootCmd ? ' | 💥 FIRE' : ''}`);
                }

                // --- STEP 4: Act (Dispatch output event via WebSocket POST) ---
                const actionPayload: AgentAction = {
                    type: "action",
                    move: moveCmd
                };

                // Only append the shoot instruction strictly if active to save bytes/state pollution
                if (shootCmd) {
                    actionPayload.shoot = true;
                }

                // Stream action resolution directly mapping backwards up the WebSocket
                ws.send(JSON.stringify(actionPayload));

            } catch (error) {
                // Log without failing out the engine natively 
                console.error("❌ Link parse error or pipeline fail:", error);
            }
        };

        // Auto-reconnect handling for seamless continuity 
        ws.onclose = () => {
            console.log("🔌 [DISCONNECTED]: Dropped socket back to host. Retrying loop in 2s...");
            setTimeout(startAgentLoop, 2000); // 2000ms poll restart to prevent infinite unblocked recursions
        };

        ws.onerror = (error: Event) => {
            console.error("⚠️ WebSocket Connectivity Event Warning Detected:");
        };
    }

    // Bootstrap loop trigger
    startAgentLoop();
}
