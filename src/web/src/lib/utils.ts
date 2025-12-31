export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || ms === 0) return '—';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatTime(timestamp: Date): string {
  return timestamp.toLocaleTimeString();
}

/**
 * Parse WAV header and calculate audio duration in milliseconds.
 * WAV header structure: RIFF header (44 bytes typical) followed by audio data.
 */
export function getWavDurationMs(arrayBuffer: ArrayBuffer): number {
  try {
    const view = new DataView(arrayBuffer);

    // Check RIFF header
    const riff = String.fromCharCode(view.getUint8(0), view.getUint8(1), view.getUint8(2), view.getUint8(3));
    if (riff !== 'RIFF') return 0;

    // Get sample rate (bytes 24-27, little endian)
    const sampleRate = view.getUint32(24, true);

    // Get bits per sample (bytes 34-35, little endian)
    const bitsPerSample = view.getUint16(34, true);

    // Get number of channels (bytes 22-23, little endian)
    const numChannels = view.getUint16(22, true);

    // Data size is typically at byte 40-43 (subchunk2 size)
    // But it's safer to calculate from total size - header size
    const dataSize = arrayBuffer.byteLength - 44; // Assuming 44-byte header

    // Calculate duration: data_size / (sample_rate * channels * bits_per_sample / 8)
    const bytesPerSecond = sampleRate * numChannels * (bitsPerSample / 8);
    const durationSeconds = dataSize / bytesPerSecond;

    return Math.round(durationSeconds * 1000);
  } catch {
    return 0;
  }
}

