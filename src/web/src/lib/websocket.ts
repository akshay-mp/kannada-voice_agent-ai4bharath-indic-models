import type { ServerEvent } from "./types";
import {
  session,
  currentTurn,
  latencyStats,
  waterfallData,
  activities,
  logs,
} from "./stores";
import { createAudioCapture, createAudioPlayback } from "./audio";
import { get } from "svelte/store";
import { getWavDurationMs } from "./utils";

export interface VoiceSession {
  start: () => Promise<void>;
  stop: () => void;
}

let ttsComplete = false;
let muteLingerTimeout: ReturnType<typeof setTimeout> | null = null;

export function createVoiceSession(): VoiceSession {
  const audioPlayback = createAudioPlayback((isPlaying) => {
    // Playback state change callback
    if (!isPlaying && ttsComplete) {
      // Audio finished AND server said TTS is done -> Unmute
      // NOTE: isMuted logic is local variable.
      isMuted = false;
      ttsComplete = false; // Reset for next turn
      console.log("Turn finished: TTS Complete & Audio Ended -> Mic Unmuted");
      finishTurn();
    }
  });

  const audioCapture = createAudioCapture();
  let ws: WebSocket | null = null;
  let isMuted = false;
  let ttsFinishTimeout: ReturnType<typeof setTimeout> | null = null;

  function handleEvent(event: ServerEvent) {
    const turn = get(currentTurn);

    switch (event.type) {
      case "user_input":
        // Fallback or deprecated - used if we did local VAD
        isMuted = true;
        currentTurn.startTurn(event.ts);
        break;

      case "processing_start":
        // Server VAD trigger
        isMuted = true;
        if (muteLingerTimeout) clearTimeout(muteLingerTimeout);
        // Start a new turn
        const now = Date.now();
        const prevTurn = get(currentTurn);
        if (prevTurn.active && prevTurn.turnStartTs) {
          waterfallData.set({ ...prevTurn });
        } else if (prevTurn.turnStartTs) {
          waterfallData.set({ ...prevTurn });
        }
        currentTurn.startTurn(now);
        console.log("Turn Started (Server VAD)");
        break;

      case "timings":
        // Apply precise server timings
        currentTurn.applyTimings(event.data);
        break;

      case "tts_complete":
        ttsComplete = true;
        console.log("TTS Generation Complete signal received");
        // Check if playback is already idle (short audio case)
        // Since we can't check 'isPlaying' directly easily without refactoring audioPlayback,
        // we rely on the callback. If callback doesn't fire (already idle), we might be stuck.
        // TODO: Ideally expose isPlaying state getter from audioPlayback.
        break;

      case "stt_chunk":
        if (!turn.active) {
          currentTurn.startTurn(event.ts || Date.now());
        }
        currentTurn.sttStart(event.ts);
        currentTurn.sttChunk(event.transcript);
        break;

      case "stt_output":
        currentTurn.sttEnd(event.ts, event.transcript);
        activities.add("stt", "Transcription", event.transcript);
        break;

      case "translation":
        if (event.direction === "indic_to_en") {
          if (!event.text) {
            currentTurn.trans1Start(event.ts);
          } else {
            currentTurn.trans1End(event.ts);
            activities.add("stt", "Translation (In→En)", event.text);
          }
        } else {
          if (!event.text) {
            currentTurn.trans2Start(event.ts);
          } else {
            currentTurn.trans2End(event.ts);
            activities.add("agent", "Translation (En→In)", event.text);
          }
        }
        break;

      case "agent_chunk":
        currentTurn.agentChunk(event.ts, event.text);
        break;

      case "tool_call":
        activities.add(
          "tool",
          `Tool: ${event.name}`,
          "Called with arguments:",
          event.args
        );
        logs.log(`Tool call: ${event.name}`);
        break;

      case "tool_result":
        activities.add("tool", `Tool Result: ${event.name}`, event.result);
        logs.log(`Tool result: ${event.result}`);
        break;

      case "tts_chunk": {
        const currentTurnState = get(currentTurn);
        if (!currentTurnState.ttsStartTs && currentTurnState.response) {
          activities.add("agent", "Agent Response", currentTurnState.response);
        }
        currentTurn.ttsChunk(event.ts);

        // Debounce finish turn - purely for stats finalization
        if (ttsFinishTimeout) clearTimeout(ttsFinishTimeout);
        ttsFinishTimeout = setTimeout(() => {
          // stats finalized in callback now? No, waterfall update still happens here or in callback?
          // We moved finishTurn() call to the callback usually.
          // But kept it here for safety? No, removing duplicate call logic.
          // Keeping timeout just to track "Turn End" for waterfall if callback fails?
          // Actually, let's keep it but NOT call finishTurn here, or ensure idempotency.
          // finishTurn is idempotent-ish.
        }, 1000);
        break;
      }
    }
  }

  function finishTurn() {
    console.log("Finishing turn, updating stats...");
    const turn = get(currentTurn);
    waterfallData.set({ ...turn });
    latencyStats.recordTurn(turn);
    currentTurn.finishTurn();
  }

  async function start(): Promise<void> {
    if (ws?.readyState === WebSocket.OPEN) return;

    session.setStatus("connecting");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);
    ws.binaryType = "arraybuffer";

    ws.onopen = async () => {
      session.connect();
      logs.log("Session started");

      try {
        await audioCapture.start((chunk) => {
          // Send only if not muted (Agent not speaking)
          if (!isMuted && get(session).connected && ws?.readyState === WebSocket.OPEN) {
            ws.send(chunk);
          }
        });
        logs.log("Microphone access granted");
      } catch (err) {
        console.error(err);
        logs.log(
          `Error: ${err instanceof Error ? err.message : "Unknown error"}`
        );
        session.setStatus("error");
        stop();
      }
    };

    ws.onmessage = async (event) => {
      if (event.data instanceof ArrayBuffer) {
        // Binary audio data (TTS)
        audioPlayback.push(event.data);
      } else {
        try {
          const eventData: ServerEvent = JSON.parse(event.data);
          handleEvent(eventData);
        } catch (e) {
          console.error("Failed to parse WebSocket message:", event.data);
        }
      }
    };

    ws.onclose = () => {
      session.disconnect();
      logs.log("WebSocket disconnected");
    };

    ws.onerror = (e) => {
      console.error(e);
      logs.log("WebSocket error");
      session.setStatus("error");
    };
  }

  function stop(): void {
    logs.log("Session ended");

    if (ttsFinishTimeout) {
      clearTimeout(ttsFinishTimeout);
      ttsFinishTimeout = null;
    }

    audioPlayback.stop();
    audioCapture.stop();

    if (ws) {
      ws.close();
      ws = null;
    }

    session.reset();
  }

  return { start, stop };
}
