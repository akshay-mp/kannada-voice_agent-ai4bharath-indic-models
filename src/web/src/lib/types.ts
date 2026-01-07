// Server event types
export type ServerEvent =
  | { type: "user_input"; ts: number }
  | { type: "stt_chunk"; ts: number; transcript: string }
  | { type: "stt_output"; ts: number; transcript: string }
  | { type: "agent_chunk"; text: string; ts: number }
  | {
    type: "tool_call";
    id: string;
    name: string;
    args: Record<string, any>;
    ts: number;
  }
  | {
    type: "tool_result";
    tool_call_id: string;
    name: string;
    result: string;
    ts: number;
  }
  | { type: "agent_end"; full_response: string; ts: number }
  | {
    type: "translation";
    ts: number;
    text: string;
    direction: "indic_to_en" | "en_to_indic";
  }
  | { type: "tts_chunk"; audio_length: number; ts: number }
  | { type: "tts_complete"; ts: number }
  | { type: "processing_start" }
  | {
    type: "timings";
    data: {
      stt: number;
      trans_in: number;
      agent: number;
      trans_out: number;
      tts: number;
      total: number;
    }
  };

// Session state
export interface SessionState {
  connected: boolean;
  recording: boolean;
  status: "ready" | "connecting" | "listening" | "error" | "disconnected";
  startTime: number | null;
  elapsed: number;
}

// Pipeline turn state
export interface TurnState {
  active: boolean;
  turnStartTs: number | null;
  sttStartTs: number | null;
  sttEndTs: number | null;
  trans1StartTs: number | null; // Indic -> En
  trans1EndTs: number | null;
  agentStartTs: number | null;
  agentEndTs: number | null;
  trans2StartTs: number | null; // En -> Indic
  trans2EndTs: number | null;
  ttsStartTs: number | null;
  ttsEndTs: number | null;
  transcript: string;
  response: string;
}

// Latency statistics
export interface LatencyStats {
  turns: number;
  stt: number[];
  trans1: number[];
  agent: number[];
  trans2: number[];
  tts: number[];
  total: number[];
}

// Activity feed item
export interface ActivityItem {
  id: string;
  type: "stt" | "agent" | "tts" | "tool";
  label: string;
  text: string;
  args?: Record<string, unknown>;
  timestamp: Date;
}

// Console log entry
export interface LogEntry {
  id: string;
  message: string;
  timestamp: Date;
}
