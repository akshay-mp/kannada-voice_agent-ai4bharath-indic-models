// Sample rate of audio from ElevenLabs (pcm_24000 format)
const SAMPLE_RATE = 24000;

export interface AudioPlayback {
  push: (chunk: string | ArrayBuffer) => void;
  stop: () => void;
  resetScheduling: () => void;
}

export interface AudioPlayback {
  push: (chunk: string | ArrayBuffer) => void;
  stop: () => void;
  resetScheduling: () => void;
}

export function createAudioPlayback(
  onPlaybackStateChange?: (isPlaying: boolean) => void
): AudioPlayback {
  let audioContext: AudioContext | null = null;
  let nextPlayTime = 0;
  let sourceQueue: AudioBufferSourceNode[] = [];
  let base64Queue: (string | ArrayBuffer)[] = [];
  let isProcessing = false;
  let activeSources = 0;

  function updateState(mod: number) {
    const wasPlaying = activeSources > 0;
    activeSources += mod;
    const isPlaying = activeSources > 0;
    if (wasPlaying !== isPlaying) {
      onPlaybackStateChange?.(isPlaying);
    }
  }

  function ensureContext(): AudioContext {
    if (!audioContext) {
      audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
    }
    if (audioContext.state === "suspended") {
      audioContext.resume();
    }
    return audioContext;
  }

  function pcmBase64ToArrayBuffer(pcmBase64: string): {
    arrayBuffer: ArrayBuffer;
    length: number;
  } {
    const binaryData = atob(pcmBase64);
    const arrayBuffer = new ArrayBuffer(binaryData.length);
    const uint8Array = new Uint8Array(arrayBuffer);

    for (let i = 0; i < binaryData.length; i++) {
      uint8Array[i] = binaryData.charCodeAt(i);
    }

    return { arrayBuffer, length: uint8Array.length };
  }

  function createAudioBuffer(
    arrayBuffer: ArrayBuffer,
    length: number
  ): AudioBuffer {
    const ctx = ensureContext();
    const data = new DataView(arrayBuffer);
    const audioBuffer = ctx.createBuffer(1, length / 2, SAMPLE_RATE);
    const channelData = audioBuffer.getChannelData(0);

    for (let i = 0; i < length; i += 2) {
      const sample = data.getInt16(i, true);
      channelData[i / 2] = sample / 32768;
    }

    return audioBuffer;
  }

  function schedulePlaySource(source: AudioBufferSourceNode): void {
    source.start(nextPlayTime);
    source.addEventListener("ended", () => sourceEnded(source));
  }

  function sourceEnded(source: AudioBufferSourceNode): void {
    const index = sourceQueue.indexOf(source);
    if (index > -1) {
      sourceQueue.splice(index, 1);
    }
  }

  function processQueue(): void {
    if (isProcessing) return;
    isProcessing = true;

    // Async processing function
    const playNext = async () => {
      if (base64Queue.length === 0) {
        isProcessing = false;
        return;
      }

      const item = base64Queue.shift();
      if (!item) {
        processQueue(); // Loop
        return;
      }

      try {
        const ctx = ensureContext();
        let arrayBuffer: ArrayBuffer;

        if (typeof item === "string") {
          // Base64 string (legacy/fallback)
          const result = pcmBase64ToArrayBuffer(item);
          // If it's raw PCM Base64, decodeAudioData might fail (no header).
          // But if we moved to WAV, it works.
          // If legacy PCM is used, we might need manual method.
          // For now, assuming new flow sends WAV as ArrayBuffer.
          // If string is strict PCM, we use manual creation.
          // Let's keep manual creation for string to be safe for legacy, 
          // but for ArrayBuffer (WAV) use decodeAudioData.
          const audioBuffer = createAudioBuffer(result.arrayBuffer, result.length);
          playBuffer(audioBuffer, ctx);
          return;
        } else {
          // ArrayBuffer (WAV/Binary)
          arrayBuffer = item;
          // Decode WAV/Audio file
          const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
          playBuffer(audioBuffer, ctx);
        }
      } catch (err) {
        console.error("Error processing audio chunk:", err);
        // Continue to next
        playNext();
      }
    };

    // Helper to play the buffer
    const playBuffer = (audioBuffer: AudioBuffer, ctx: AudioContext) => {
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      sourceQueue.push(source);

      // Track active sources
      updateState(1);
      source.onended = () => {
        updateState(-1);
      };

      // If we've fallen behind, catch up to current time
      if (nextPlayTime < ctx.currentTime) {
        nextPlayTime = ctx.currentTime;
      }

      schedulePlaySource(source);
      nextPlayTime += audioBuffer.duration;

      // Loop
      playNext();
    };

    playNext();
  }

  function push(chunk: string | ArrayBuffer): void {
    base64Queue.push(chunk);
    processQueue();
  }

  function stop(): void {
    base64Queue = [];

    for (const source of sourceQueue) {
      try {
        source.stop();
      } catch {
        // Ignore if already stopped
      }
    }
    sourceQueue = [];
    nextPlayTime = 0;
  }

  function resetScheduling(): void {
    nextPlayTime = 0;
  }

  return {
    push,
    stop,
    resetScheduling,
  };
}
