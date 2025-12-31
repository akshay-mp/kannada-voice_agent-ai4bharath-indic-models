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

export function createVoiceSession(): VoiceSession {
  let ws: WebSocket | null = null;
  let ttsFinishTimeout: ReturnType<typeof setTimeout> | null = null;
  let isMuted = false;
  let muteLingerTimeout: ReturnType<typeof setTimeout> | null = null;

  const audioPlayback = createAudioPlayback(() => {
    // Playback state change callback - no longer used for muting
    // Muting is now controlled by user_input (mute) and finishTurn (unmute)
  });
  const audioCapture = createAudioCapture();

  function handleEvent(event: ServerEvent) {
    const turn = get(currentTurn);

    switch (event.type) {
      case "user_input":
        // MUTE MIC IMMEDIATELY - server detected speech, pipeline is processing
        // This prevents echo/feedback during the entire processing phase
        isMuted = true;
        if (muteLingerTimeout) {
          clearTimeout(muteLingerTimeout);
          muteLingerTimeout = null;
        }

        // Always start new turn on VAD start (Audio Received)
        const prevTurn = get(currentTurn);
        if (prevTurn.active) {
          // Force finish previous turn if active?
          // If we overwrite, we lose stats for the interrupted turn.
          // Better to just save waterfall data.
          if (prevTurn.turnStartTs) {
            waterfallData.set({ ...prevTurn });
          }
        } else if (prevTurn.turnStartTs) {
          // Previous turn finished normally
          waterfallData.set({ ...prevTurn });
        }

        currentTurn.startTurn(event.ts);
        console.log("Turn Started (User Input):", event.ts);
        break;

      case "stt_chunk":
        // Ensure turn is active if stt_start missed?
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

        // Debounce finish turn
        if (ttsFinishTimeout) clearTimeout(ttsFinishTimeout);
        ttsFinishTimeout = setTimeout(() => {
          const t = get(currentTurn);
          // If audio finished playing (we can't know for sure here, but 1s is safe)
          // Actually handling finish logic:
          finishTurn();
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

    // NOTE: Unmuting is now handled by audio-duration-based logic in ws.onmessage
    // Do NOT unmute here as it would conflict with audio playback timing
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

        // Calculate audio duration and schedule unmute
        const audioDurationMs = getWavDurationMs(event.data);
        if (audioDurationMs > 0) {
          // Clear any pending unmute and schedule new one based on audio length
          if (muteLingerTimeout) {
            clearTimeout(muteLingerTimeout);
          }
          // Keep muted for audio duration + 1000ms buffer (extra safety for echo)
          const unmutedelay = audioDurationMs + 1000;
          console.log(`TTS audio: ${audioDurationMs}ms, unmute in ${unmutedelay}ms`);
          muteLingerTimeout = setTimeout(() => {
            isMuted = false;
            muteLingerTimeout = null;
            console.log("Mic unmuted - ready for next input");
          }, unmutedelay);
        }
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
