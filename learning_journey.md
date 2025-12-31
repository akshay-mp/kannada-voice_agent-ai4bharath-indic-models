# Learning Journey

## 2025-12-31: The Quest for Real-Time Performance

### The Challenge
Our initial deployment of the Kannada Voice Agent was functional but suffered from severe latency issues, making it impractical for real-time conversation.
- **Total Turn Latency**: ~75 seconds
- **User Experience**: excruciatingly slow response times.
- **Infrastructure Cost**: Prohibitively high (5 x A10G GPUs).

### Root Cause Analysis
We performed a deep dive into the pipeline's performance waterfall:
1.  **TTS Bottleneck**: The specific IndicF5 model implementation was taking ~62 seconds to generate audio. This accounted for >80% of the total latency.
2.  **Resource Inefficiency**: We deployed 1B parameter translation models on dedicated A10G (24GB) GPUs. These models are small enough to run efficiently on CPU or shared GPU resources, especially with quantization.
3.  **Serial Execution**: The pipeline was processing strictly sequentially: `Audio -> STT -> Translate -> Agent -> Translate -> TTS -> Audio`. No pipelining or streaming was implemented.

### Key Learnings & Decisions
1.  **Model Selection Matters**: While IndicF5 offers quality, its varying inference times (diffusion-based) and the specific lack of optimization in our setup made it unsuitable for real-time interaction compared to faster autoregressive models like Parler-TTS.
2.  **Optimization is Mandatory**: Running raw HuggingFace models in production is inefficient. Technologies like **CTranslate2** (for translation) and **INT8 quantization** are essential for reasonable cost/performance ratios.
3.  **Streaming is Key**: For voice agents, "Time to First Byte" (TTFB) is the metric that matters. We must move to a streaming architecture where the TTS starts playing as soon as the first few tokens are available.

### strategic Pivot
We are moving from a "deploy everything on big GPUs" strategy to a **Balanced Optimization** strategy:
- **Consolidation**: Group lighter services (STT, Translation) onto a single GPU.
- **Engine Switch**: Use **CTranslate2** for translation (4x speedup, 1/4 memory).
- **Streaming TTS**: Switch to **Parler-TTS** (or optimized F5) and implement token-level streaming from the Agent -> TTS.

This journey highlights the divide between "research code" (working models) and "production systems" (optimized pipelines).
