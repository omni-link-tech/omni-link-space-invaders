{
    /**
     * Advanced Master Agent for Space Invaders
     * Faster logic, better tracking, suitable for higher levels.
     */

    interface Alien { x: number; y: number; }
    interface Bullet { x: number; y: number; }
    interface GameState {
        type: "state";
        shipX: number;
        shipWidth?: number;
        bullet: Bullet | null;
        aliens: Alien[];
        score: number;
        lives: number;
        level: number;
        gameOver: boolean;
    }
    interface AgentAction {
        type: "action";
        move: "left" | "right" | "stop";
        shoot?: boolean;
    }

    const MASTER_WS_URL = "ws://localhost:6789/agent_invaders";
    let lastAlienX: number | null = null;
    let alienDirection = 1;

    function startMasterAgentLoop() {
        console.log(`🚀 Space Invaders Master Agent Started. Connecting to ${MASTER_WS_URL}...`);
        const ws = new WebSocket(MASTER_WS_URL);

        ws.onopen = () => {
            console.log("✅ [MASTER AGENT]: Linked to Game Server.");
        };

        ws.onmessage = (event: MessageEvent) => {
            try {
                const gameState: GameState = JSON.parse(event.data);
                if (gameState.type !== "state" || gameState.gameOver) return;

                const shipWidth = gameState.shipWidth || 40;
                const shipCenter = gameState.shipX + (shipWidth / 2);
                const shipCenterY = 480 - 30; // Game canvas height is 480, ship is 30px from bottom
                // Wider tolerance + predictive for higher speeds
                const tolerance = 8;

                let targetAlien: Alien | null = null;
                if (gameState.aliens && gameState.aliens.length > 0) {
                    targetAlien = gameState.aliens.reduce((prev, curr) => {
                        // Priority 1: Lowest Y (closest to ship)
                        if (curr.y > prev.y) return curr;
                        if (curr.y === prev.y) {
                            return Math.abs(curr.x - shipCenter) < Math.abs(prev.x - shipCenter) ? curr : prev;
                        }
                        return prev;
                    });
                    // Track alien direction implicitly via the target's movement
                    if (lastAlienX !== null) {
                        if (targetAlien.x > lastAlienX) alienDirection = 1;
                        else if (targetAlien.x < lastAlienX) alienDirection = -1;
                    }
                    lastAlienX = targetAlien.x;
                } else {
                    lastAlienX = null;
                }

                let moveCmd: "left" | "right" | "stop" = "stop";
                let shootCmd = false;

                if (targetAlien) {
                    // --- EXACT INTERSECTION MATH ---
                    // Bullet travels up at 6px per frame.
                    const bulletSpeed = 6;
                    // Alien travels horizontally depending on level
                    const alienSpeed = 0.8 + (gameState.level - 1) * 0.4;
                    // Distance the bullet needs to travel vertically:
                    const dy = shipCenterY - targetAlien.y;
                    // Time (in frames) for bullet to reach the alien's Y coordinate
                    const timeToHit = dy / bulletSpeed;

                    // Anticipate alien's X coordinate at time of impact
                    let predictedTargetX = targetAlien.x + (alienDirection * alienSpeed * timeToHit);

                    // Optional boundaries check: if it bounces off a wall while the bullet is mid-air
                    // (Game width is 640. Alien width is 30. Hit edges are 10 on left, 630 on right)
                    if (predictedTargetX > 630 - 30) {
                        predictedTargetX = 630 - 30 - Math.abs((predictedTargetX) - (630 - 30));
                    } else if (predictedTargetX < 10) {
                        predictedTargetX = 10 + Math.abs(10 - predictedTargetX);
                    }

                    // Tighter tolerance for the newly calculated perfect lead
                    const exactTolerance = 3;

                    if (shipCenter < predictedTargetX - exactTolerance) {
                        moveCmd = "right";
                    } else if (shipCenter > predictedTargetX + exactTolerance) {
                        moveCmd = "left";
                    } else {
                        moveCmd = "stop";
                        // Fire if perfectly aligned and bullet isn't active
                        if (!gameState.bullet) shootCmd = true;
                    }
                }

                const actionPayload: AgentAction = { type: "action", move: moveCmd };
                if (shootCmd) actionPayload.shoot = true;
                ws.send(JSON.stringify(actionPayload));

            } catch (error) {
                console.error("❌ Parse error:", error);
            }
        };

        ws.onclose = () => {
            console.log("🔌 [DISCONNECTED]: Retrying in 2s...");
            setTimeout(startMasterAgentLoop, 2000);
        };
        ws.onerror = (error: Event) => console.error("⚠️ WebSocket Error");
    }

    startMasterAgentLoop();
}
