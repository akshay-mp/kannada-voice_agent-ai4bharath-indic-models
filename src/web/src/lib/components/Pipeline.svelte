<script lang="ts">
  import { currentTurn } from '../stores';
  import { formatDuration } from '../utils';

  interface StageState {
    active: boolean;
    complete: boolean;
    time: string;
  }

  let stt = $derived<StageState>({
    active: !!$currentTurn.sttStartTs && !$currentTurn.sttEndTs,
    complete: !!$currentTurn.sttEndTs,
    time: $currentTurn.sttEndTs && $currentTurn.sttStartTs
      ? formatDuration($currentTurn.sttEndTs - $currentTurn.sttStartTs)
      : $currentTurn.sttStartTs ? '...' : '—',
  });

  let trans1 = $derived<StageState>({
    active: !!$currentTurn.trans1StartTs && !$currentTurn.trans1EndTs,
    complete: !!$currentTurn.trans1EndTs,
    time: $currentTurn.trans1EndTs && $currentTurn.trans1StartTs
      ? formatDuration($currentTurn.trans1EndTs - $currentTurn.trans1StartTs)
      : $currentTurn.trans1StartTs ? '...' : '—',
  });

  let agent = $derived<StageState>({
    active: !!$currentTurn.agentStartTs && !$currentTurn.agentEndTs,
    complete: !!$currentTurn.agentEndTs,
    time: $currentTurn.agentEndTs && $currentTurn.agentStartTs
      ? formatDuration($currentTurn.agentEndTs - $currentTurn.agentStartTs)
      : $currentTurn.agentStartTs ? '...' : '—',
  });

  let trans2 = $derived<StageState>({
    active: !!$currentTurn.trans2StartTs && !$currentTurn.trans2EndTs,
    complete: !!$currentTurn.trans2EndTs,
    time: $currentTurn.trans2EndTs && $currentTurn.trans2StartTs
      ? formatDuration($currentTurn.trans2EndTs - $currentTurn.trans2StartTs)
      : $currentTurn.trans2StartTs ? '...' : '—',
  });

  let tts = $derived<StageState>({
    active: !!$currentTurn.ttsStartTs && !$currentTurn.ttsEndTs,
    complete: !!$currentTurn.ttsEndTs,
    time: $currentTurn.ttsEndTs && $currentTurn.ttsStartTs
      ? formatDuration($currentTurn.ttsEndTs - $currentTurn.ttsStartTs)
      : $currentTurn.ttsStartTs ? '...' : '—',
  });

  function stageClasses(state: StageState, color: 'cyan' | 'purple' | 'orange' | 'indigo' | 'emerald'): string {
    const colorMap = {
      cyan: {
        border: 'border-cyan-400',
        active: 'bg-cyan-400/15 shadow-[0_0_16px_theme(colors.cyan.400/30)]',
      },
      purple: {
        border: 'border-purple-500',
        active: 'bg-purple-500/15 shadow-[0_0_16px_theme(colors.purple.500/30)]',
      },
      orange: {
        border: 'border-orange-500',
        active: 'bg-orange-500/15 shadow-[0_0_16px_theme(colors.orange.500/30)]',
      },
      indigo: {
        border: 'border-indigo-500',
        active: 'bg-indigo-500/15 shadow-[0_0_16px_theme(colors.indigo.500/30)]',
      },
      emerald: {
        border: 'border-emerald-500',
        active: 'bg-emerald-500/15 shadow-[0_0_16px_theme(colors.emerald.500/30)]',
      },
    };

    const c = colorMap[color];
    let classes = `w-13 h-13 rounded-xl flex items-center justify-center text-2xl
                   bg-[#252530] border-2 ${c.border} transition-all duration-300`;

    if (state.active) {
      classes += ` ${c.active} scale-105 animate-pulse`;
    } else if (state.complete) {
      classes += ' opacity-70';
    }

    return classes;
  }
</script>

<div class="flex items-center justify-center gap-2 py-4 px-2 overflow-x-auto">
  <!-- STT Stage -->
  <div class="flex flex-col items-center gap-2.5 min-w-[60px]">
    <div class={stageClasses(stt, 'cyan')}>🎤</div>
    <div class="text-[10px] font-medium uppercase tracking-wider text-gray-500">STT</div>
    <div class="font-mono text-[10px] text-gray-600">{stt.time}</div>
  </div>

  <div class="text-gray-600 text-sm -mt-6">→</div>

  <!-- Trans1 Stage (Indic->En) -->
  <div class="flex flex-col items-center gap-2.5 min-w-[60px]">
    <div class={stageClasses(trans1, 'indigo')}>🔄</div>
    <div class="text-[10px] font-medium uppercase tracking-wider text-gray-500">In→En</div>
    <div class="font-mono text-[10px] text-gray-600">{trans1.time}</div>
  </div>

  <div class="text-gray-600 text-sm -mt-6">→</div>

  <!-- Agent Stage -->
  <div class="flex flex-col items-center gap-2.5 min-w-[60px]">
    <div class={stageClasses(agent, 'purple')}>🤖</div>
    <div class="text-[10px] font-medium uppercase tracking-wider text-gray-500">Agent</div>
    <div class="font-mono text-[10px] text-gray-600">{agent.time}</div>
  </div>

  <div class="text-gray-600 text-sm -mt-6">→</div>

  <!-- Trans2 Stage (En->Indic) -->
  <div class="flex flex-col items-center gap-2.5 min-w-[60px]">
    <div class={stageClasses(trans2, 'emerald')}>🔄</div>
    <div class="text-[10px] font-medium uppercase tracking-wider text-gray-500">En→In</div>
    <div class="font-mono text-[10px] text-gray-600">{trans2.time}</div>
  </div>

  <div class="text-gray-600 text-sm -mt-6">→</div>

  <!-- TTS Stage -->
  <div class="flex flex-col items-center gap-2.5 min-w-[60px]">
    <div class={stageClasses(tts, 'orange')}>🔊</div>
    <div class="text-[10px] font-medium uppercase tracking-wider text-gray-500">TTS</div>
    <div class="font-mono text-[10px] text-gray-600">{tts.time}</div>
  </div>
</div>

