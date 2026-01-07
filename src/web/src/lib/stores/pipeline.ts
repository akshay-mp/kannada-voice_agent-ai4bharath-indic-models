import { writable, derived } from "svelte/store";
import type { TurnState, LatencyStats } from "../types";

const initialTurnState: TurnState = {
  active: false,
  turnStartTs: null,
  sttStartTs: null,
  sttEndTs: null,
  trans1StartTs: null,
  trans1EndTs: null,
  agentStartTs: null,
  agentEndTs: null,
  trans2StartTs: null,
  trans2EndTs: null,
  ttsStartTs: null,
  ttsEndTs: null,
  transcript: "",
  response: "",
};

function createTurnStore() {
  const { subscribe, set, update } = writable<TurnState>(initialTurnState);

  return {
    subscribe,

    startTurn(ts: number) {
      set({
        ...initialTurnState,
        active: true,
        turnStartTs: ts,
      });
    },

    sttStart(ts: number) {
      update((t) => ({ ...t, sttStartTs: t.sttStartTs ?? ts }));
    },

    sttEnd(ts: number, transcript: string) {
      update((t) => ({ ...t, sttEndTs: ts, transcript }));
    },

    sttChunk(transcript: string) {
      update((t) => ({ ...t, transcript }));
    },

    trans1Start(ts: number) {
      update((t) => ({ ...t, trans1StartTs: t.trans1StartTs ?? ts }));
    },

    trans1End(ts: number) {
      update((t) => ({ ...t, trans1EndTs: ts }));
    },

    agentStart(ts: number) {
      update((t) => ({ ...t, agentStartTs: t.agentStartTs ?? ts }));
    },

    agentChunk(ts: number, text: string) {
      update((t) => ({
        ...t,
        agentStartTs: t.agentStartTs ?? ts,
        agentEndTs: ts,
        response: t.response + text,
      }));
    },

    trans2Start(ts: number) {
      update((t) => ({ ...t, trans2StartTs: t.trans2StartTs ?? ts }));
    },

    trans2End(ts: number) {
      update((t) => ({ ...t, trans2EndTs: ts }));
    },

    ttsStart(ts: number) {
      update((t) => ({ ...t, ttsStartTs: t.ttsStartTs ?? ts }));
    },

    ttsChunk(ts: number) {
      update((t) => ({
        ...t,
        ttsStartTs: t.ttsStartTs ?? ts,
        ttsEndTs: ts,
      }));
    },

    finishTurn() {
      update((t) => ({ ...t, active: false }));
    },

    applyTimings(timings: { stt: number; trans_in: number; agent: number; trans_out: number; tts: number; total: number }) {
      update((t) => {
        if (!t.turnStartTs) return t;
        const start = t.turnStartTs;
        // Convert seconds to ms
        const sttEnd = start + timings.stt * 1000;
        const trans1End = sttEnd + timings.trans_in * 1000;
        const agentEnd = trans1End + timings.agent * 1000;
        const trans2End = agentEnd + timings.trans_out * 1000;
        const ttsEnd = trans2End + timings.tts * 1000;

        return {
          ...t,
          sttStartTs: start,
          sttEndTs: sttEnd,
          trans1StartTs: sttEnd,
          trans1EndTs: trans1End,
          agentStartTs: trans1End,
          agentEndTs: agentEnd,
          trans2StartTs: agentEnd,
          trans2EndTs: trans2End,
          ttsStartTs: trans2End,
          ttsEndTs: ttsEnd,
        };
      });
    },

    reset() {
      set(initialTurnState);
    },
  };
}

function createLatencyStore() {
  const { subscribe, set, update } = writable<LatencyStats>({
    turns: 0,
    stt: [],
    trans1: [],
    agent: [],
    trans2: [],
    tts: [],
    total: [],
  });

  return {
    subscribe,

    recordTurn(turn: TurnState) {
      const sttLatency =
        turn.sttEndTs && turn.sttStartTs
          ? turn.sttEndTs - turn.sttStartTs
          : null;
      const trans1Latency =
        turn.trans1EndTs && turn.trans1StartTs
          ? turn.trans1EndTs - turn.trans1StartTs
          : null;
      const agentLatency =
        turn.agentEndTs && turn.agentStartTs
          ? turn.agentEndTs - turn.agentStartTs
          : null;
      const trans2Latency =
        turn.trans2EndTs && turn.trans2StartTs
          ? turn.trans2EndTs - turn.trans2StartTs
          : null;
      const ttsLatency =
        turn.ttsEndTs && turn.ttsStartTs
          ? turn.ttsEndTs - turn.ttsStartTs
          : null;

      if (
        sttLatency !== null &&
        trans1Latency !== null &&
        agentLatency !== null &&
        trans2Latency !== null &&
        ttsLatency !== null
      ) {
        update((s) => ({
          turns: s.turns + 1,
          stt: [...s.stt, sttLatency],
          trans1: [...s.trans1, trans1Latency],
          agent: [...s.agent, agentLatency],
          trans2: [...s.trans2, trans2Latency],
          tts: [...s.tts, ttsLatency],
          total: [
            ...s.total,
            sttLatency + trans1Latency + agentLatency + trans2Latency + ttsLatency,
          ],
        }));
      }
    },

    reset() {
      set({ turns: 0, stt: [], trans1: [], agent: [], trans2: [], tts: [], total: [] });
    },
  };
}

export const currentTurn = createTurnStore();
export const latencyStats = createLatencyStore();

// Preserved waterfall data (kept until next turn starts)
export const waterfallData = writable<TurnState | null>(null);

// Derived stats
export const computedStats = derived(latencyStats, ($stats) => {
  if ($stats.total.length === 0) {
    return { avg: null, min: null, max: null };
  }
  const avg = $stats.total.reduce((a, b) => a + b, 0) / $stats.total.length;
  const min = Math.min(...$stats.total);
  const max = Math.max(...$stats.total);
  return { avg, min, max };
});
